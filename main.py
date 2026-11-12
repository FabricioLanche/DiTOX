import logging
import sys
from os import listdir
from pathlib import Path
from os.path import isfile, join

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from configs.config import load_pipeline_config
from src.model_orchestrator.model_orchestrator import ModelOrchestrator
from src.model_orchestrator.tvm_builder import TVMBuilder
from src.dispatchers import BackendDispatcher, ModelComparisonDispatcher
from src.reports.logger import configure_pipeline_logger
from src.reports import ReportManager
from src.runner.preprocessing.prepared_image_inputs import PreparedImageInputs
from src.runner.preprocessing.text_inputs import TextInputProvider


def _process_model_batch(
    model_data,
    batch_state,
    *,
    report_manager,
    backend_dispatcher,
    comparison_dispatcher,
    onnx_runner,
    general_config,
    images_config,
    optimizer_config,
    include_certainties,
    enable_kt_on_one_dim_tensor,
    pipeline_trace,
    text_input_provider,
):
    model_comparisons_file = batch_state["report_path"]
    with pipeline_trace.stage(
        "report.load_or_initialize", report=str(model_comparisons_file)
    ):
        if batch_state["report_started"]:
            model_comparisons = report_manager.load(model_comparisons_file)
        else:
            model_comparisons = report_manager.new_report(
                batch_state["manifest_categories"],
                batch_state["manifest_missing_models"],
                batch_state["manifest_excluded_by_config"],
            )
            report_manager.save(model_comparisons_file, model_comparisons)
            batch_state["report_started"] = True

    model_name = model_data["model_name"]
    model_name_opset = model_data["model_name_opset"]
    tags = model_data["tags"]
    model_config = model_data["model_config"]
    model_path = model_data["model_path"]
    model = model_data["model"]
    relax_model = model_data["relax_model"]
    relax_input_names = model_data["relax_input_names"]
    base_executable = model_data["base_executable"]
    tvm_build_error = model_data["tvm_build_error"]
    original_hash = model_data["original_hash"]
    opt_model_path = model_data["opt_model_path"]
    images_paths = batch_state["images_paths"]
    text_prompts = None
    if "text" in tags:
        if batch_state.get("text_prompts") is None:
            with pipeline_trace.stage("text_inputs.load"):
                batch_state["text_prompts"] = text_input_provider.load()
        text_prompts = batch_state["text_prompts"][
            batch_state["starts_from"] : batch_state["ends_at"]
        ]

    if not optimizer_config.get("enabled", True):
        passes = []
    else:
        active_optimizer = (
            backend_dispatcher.onnx_optimizer
            if "text" in tags
            else backend_dispatcher.optimizer
        )
        passes = (
            optimizer_config["passes"]
            if optimizer_config["passes"]
            else active_optimizer.get_optimizer_passes()
        )

    print("Running original model...")
    print(model_path)
    base_relax_mod = relax_model if backend_dispatcher.is_tvm else None
    prepared_image_inputs = None
    trace_context = {
        "batch": model_comparisons_file.stem,
        "model": model_name_opset,
    }

    try:
        if (
            backend_dispatcher.is_tvm
            and "text" not in tags
            and tvm_build_error is None
        ):
            with pipeline_trace.stage("images.preprocess", **trace_context):
                prepared_image_inputs = PreparedImageInputs(
                    images_paths,
                    model_config,
                    subbatch_size=images_config.get(
                        "preprocessing_subbatch_size", 32
                    ),
                )

        with pipeline_trace.stage("baseline.run", **trace_context):
            base_model_out = backend_dispatcher.run_baseline(
                model,
                tags,
                images_paths,
                model_config,
                include_certainties,
                base_executable=base_executable,
                relax_input_names=relax_input_names,
                tvm_build_error=tvm_build_error,
                prepared_image_inputs=prepared_image_inputs,
                text_prompts=text_prompts,
            )
    except Exception as error:
        if prepared_image_inputs is not None:
            prepared_image_inputs.close()
        pipeline_trace.event(
            "baseline.failed",
            level=logging.ERROR,
            error=repr(error),
            **trace_context,
        )
        print(error)
        print(model_name + " - a base model error occured!")
        model_comparisons["failed_models"].append(model_name_opset)
        model_comparisons["conversion_errors"][model_name_opset] = {
            "baseline": repr(error)
        }
        with pipeline_trace.stage("report.save", **trace_context):
            report_manager.save(model_comparisons_file, model_comparisons)
        return

    model_comparisons["base_models_run"] += 1
    model_comparisons[model_name_opset] = {
        "skipped": [],
        "failed": [],
        "blocked": [],
        "dependency_checks": {},
        "dependency_failures": {},
        "different": 0,
        "run": 0,
    }

    if not passes:
        model_comparisons[model_name_opset]["baseline_only"] = True
        with pipeline_trace.stage("report.save", **trace_context):
            report_manager.save(model_comparisons_file, model_comparisons)

    run_individual_passes = general_config["run_individual_passes"]
    passes_to_run = backend_dispatcher.passes_to_run(
        passes, run_individual_passes
    )

    try:
        for current_pass in passes_to_run:
            pass_context = {**trace_context, "pass": current_pass}
            with pipeline_trace.stage("optimization.pass", **pass_context):
                opt_model_out, conversion_failed, current_pass = (
                    backend_dispatcher.run_optimization_pass(
                        current_pass,
                        base_relax_mod=base_relax_mod,
                        base_model_out=base_model_out,
                        tags=tags,
                        images_paths=images_paths,
                        model_config=model_config,
                        include_certainties=include_certainties,
                        model_path=model_path,
                        opt_model_path=opt_model_path,
                        original_hash=original_hash,
                        model_name=model_name,
                        model_name_opset=model_name_opset,
                        model_comparisons=model_comparisons,
                        enable_kt_on_one_dim_tensor=enable_kt_on_one_dim_tensor,
                        relax_input_names=relax_input_names,
                        prepared_image_inputs=prepared_image_inputs,
                        text_prompts=text_prompts,
                    )
                )

            if not conversion_failed and opt_model_out is not None:
                with pipeline_trace.stage("metrics.compare", **pass_context):
                    comparison_dispatcher.dispatch(
                        evaluation_runner=backend_dispatcher.evaluation_runner,
                        onnx_runner=onnx_runner,
                        tags=tags,
                        model_name_opset=model_name_opset,
                        current_pass=current_pass,
                        include_certainties=include_certainties,
                        enable_kt_on_one_dim_tensor=enable_kt_on_one_dim_tensor,
                        model_comparisons=model_comparisons,
                        base_model_out=base_model_out,
                        opt_model_out=opt_model_out,
                        model=model,
                        text_runner=backend_dispatcher.text_runner,
                    )

            with pipeline_trace.stage("report.save", **pass_context):
                report_manager.save(model_comparisons_file, model_comparisons)
            if not run_individual_passes:
                break

        with pipeline_trace.stage("report.save", **trace_context):
            report_manager.save(model_comparisons_file, model_comparisons)
    finally:
        if prepared_image_inputs is not None:
            prepared_image_inputs.close()


def main():

    config_path = sys.argv[1] if len(sys.argv) > 1 else None
    run_config = load_pipeline_config(config_path)
    images_config = run_config.images
    general_config = run_config.general
    hub_config = run_config.hub
    optimizer_config = run_config.optimizer

    include_certainties = general_config["include_certainties"]
    enable_kt_on_one_dim_tensor = general_config["enable_kt_on_one_dim_tensor"]

    script_dir = str(Path(__file__).resolve().parent.parent)
    pipeline_trace = configure_pipeline_logger(
        script_dir, run_config.logging
    )
    pipeline_trace.event(
        "pipeline.started",
        config=str(run_config.path),
        backend=run_config.backend,
        run_id=pipeline_trace.run_id,
    )
    images_folder = script_dir + "/" + images_config["images_folder_rel_path"]

    report_manager = ReportManager(
        script_dir, general_config["report_file_base_rel_path"]
    )

    tvm_builder = None
    if run_config.backend == "tvmr":
        runtime_tvm_config = run_config.runtime.get("tvm", {})
        compiled_cache_dir = (
            runtime_tvm_config.get("compiled_cache_dir")
            or run_config.tvm.get("compiled_cache_dir")
        )
        if compiled_cache_dir is None:
            compiled_cache_dir = (
                Path(script_dir)
                / hub_config["cache_folder_rel_path"].lstrip("/\\")
                / "tvm_compiled"
            )
        else:
            compiled_cache_dir = Path(compiled_cache_dir).expanduser()
            if not compiled_cache_dir.is_absolute():
                compiled_cache_dir = Path(script_dir) / compiled_cache_dir
        tvm_builder = TVMBuilder(
            compiled_cache_dir,
            pipeline_trace=pipeline_trace,
        )

    backend_dispatcher = BackendDispatcher(
        run_config,
        pipeline_trace=pipeline_trace,
    )
    comparison_dispatcher = ModelComparisonDispatcher()
    onnx_runner = backend_dispatcher.onnx_runner
    text_input_provider = TextInputProvider(run_config.text)

    check_prob_models = general_config["check_reports_for_problematic_models"]
    with pipeline_trace.stage("models.catalog_discovery"):
        model_orchestrator = ModelOrchestrator(
            general_config,
            hub_config,
            script_dir,
            check_prob_models=check_prob_models,
            tvm_builder=tvm_builder,
            pipeline_trace=pipeline_trace,
        )
    manifest_categories = model_orchestrator.manifest_categories
    manifest_missing_models = model_orchestrator.manifest_missing_models
    manifest_excluded_by_config = model_orchestrator.manifest_excluded_by_config
 
    all_images_paths = [
        join(images_folder, filename)
        for filename in listdir(images_folder)
        if isfile(join(images_folder, filename))
    ]
    all_images_paths.sort()

    images_chunk = images_config["images_chunk"]
    starts_from = images_config["starts_from"]
    limit = images_config["limit"]
    ends_at = starts_from + images_chunk
    batch_states = []

    while ends_at < limit + images_chunk:
        images_paths = all_images_paths[starts_from:ends_at]
        report_path = report_manager.chunk_path(starts_from, ends_at)
        print(" ---- Input Batch: " + str(starts_from) + " to " + str(ends_at))

        problematic_models = None
        if check_prob_models:
            problematic_models = report_manager.problematic_models(report_path)
            print(
                f"Isolating passes for {len(problematic_models)} problematic models "
                f"from {report_path.name}"
            )

        batch_states.append(
            {
                "images_paths": images_paths,
                "starts_from": starts_from,
                "ends_at": ends_at,
                "text_prompts": None,
                "report_path": report_path,
                "problematic_models": problematic_models,
                "report_started": False,
                "manifest_categories": manifest_categories,
                "manifest_missing_models": manifest_missing_models,
                "manifest_excluded_by_config": manifest_excluded_by_config,
            }
        )
        pipeline_trace.event(
            "batch.scheduled",
            start=starts_from,
            end=ends_at,
            image_count=len(images_paths),
            report=str(report_path),
        )
        starts_from += images_chunk
        ends_at += images_chunk

    if batch_states:
        problematic_union = None
        if check_prob_models:
            problematic_union = set().union(
                *(state["problematic_models"] for state in batch_states)
            )

        for model_data in model_orchestrator.get_models(problematic_union):
            for batch_state in batch_states:
                if (
                    check_prob_models
                    and model_data["model_name_opset"]
                    not in batch_state["problematic_models"]
                ):
                    continue

                pipeline_trace.event(
                    "model.selected",
                    model=model_data["model_name_opset"],
                    batch=batch_state["report_path"].stem,
                )
                _process_model_batch(
                    model_data,
                    batch_state,
                    report_manager=report_manager,
                    backend_dispatcher=backend_dispatcher,
                    comparison_dispatcher=comparison_dispatcher,
                    onnx_runner=onnx_runner,
                    general_config=general_config,
                    images_config=images_config,
                    optimizer_config=optimizer_config,
                    include_certainties=include_certainties,
                    enable_kt_on_one_dim_tensor=enable_kt_on_one_dim_tensor,
                    pipeline_trace=pipeline_trace,
                    text_input_provider=text_input_provider,
                )

        for batch_state in batch_states:
            if not batch_state["report_started"]:
                empty_report = report_manager.new_report(
                    manifest_categories,
                    manifest_missing_models,
                    manifest_excluded_by_config,
                )
                report_manager.save(batch_state["report_path"], empty_report)

    pipeline_trace.event("pipeline.completed", batch_count=len(batch_states))

if __name__ == "__main__":
    main()
