import logging
import json
import multiprocessing
import os
import sys
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, wait
from pathlib import Path

project_root = Path(__file__).resolve().parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from configs.config import load_pipeline_config
from src.model_orchestrator.model_orchestrator import ModelOrchestrator
from src.model_orchestrator.tvm_builder import TVMBuilder
from src.helpers.dispatchers import BackendDispatcher, ModelComparisonDispatcher
from src.helpers.reports.logger import configure_pipeline_logger
from src.helpers.reports import ReportManager
from src.helpers.reports.checkpoint_manager import CheckpointManager
from src.runner.preprocessing.prepared_image_inputs import PreparedImageInputs
from src.runner.preprocessing.text_inputs import DatasetInputProvider, TextInputProvider
from src.runner.preprocessing.model_preprocessor import ModelPreprocessor


def _available_cpu_count():
    try:
        return max(1, len(os.sched_getaffinity(0)))
    except (AttributeError, OSError):
        return max(1, os.cpu_count() or 1)


def _discover_image_paths(images_folder, pipeline_trace):
    from PIL import Image

    images_folder = Path(images_folder)
    supported_extensions = {
        extension.lower() for extension in Image.registered_extensions()
    }
    image_paths = []
    ignored_files = []

    for path in sorted(images_folder.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in supported_extensions:
            ignored_files.append(path.name)
            continue
        image_paths.append(str(path))

    pipeline_trace.event(
        "images.discovered",
        directory=str(images_folder),
        image_count=len(image_paths),
        ignored_file_count=len(ignored_files),
    )
    if ignored_files:
        print(
            f"Ignored {len(ignored_files)} non-image or invalid file(s) "
            f"in {images_folder}."
        )
    return image_paths


def _run_parallel_models(
    model_specs,
    batch_states,
    *,
    run_config,
    report_manager,
    pipeline_trace,
    model_workers,
    threads_per_worker,
    manifest_categories,
    manifest_missing_models,
    manifest_excluded_by_config,
    reports,
    completed_models,
    checkpoint_manager,
):
    from src.helpers.dispatchers.model_worker import run_model_task

    model_workers = min(model_workers, len(model_specs))
    reports = reports or [
        report_manager.new_report(
            manifest_categories,
            manifest_missing_models,
            manifest_excluded_by_config,
        )
        for _ in batch_states
    ]
    completed_models = set(completed_models or [])
    if model_workers == 0:
        for batch_index, batch_state in enumerate(batch_states):
            report_manager.save(batch_state["report_path"], reports[batch_index])
        return
    cpu_count = _available_cpu_count()
    if threads_per_worker == 0:
        threads_per_worker = max(1, cpu_count // model_workers)
    task_items = iter(
        (
            model_spec,
            [
                batch_index
                for batch_index, batch_state in enumerate(batch_states)
                if (
                    model_spec["model_name_opset"]
                    not in batch_state["existing_models"]
                    and (
                        not batch_state["problematic_models"]
                        or model_spec["model_name_opset"]
                        in batch_state["problematic_models"]
                    )
                )
            ],
        )
        for model_spec in model_specs
        if any(
            model_spec["model_name_opset"]
            not in batch_state["existing_models"]
            and (
                not batch_state["problematic_models"]
                or model_spec["model_name_opset"]
                in batch_state["problematic_models"]
            )
            for batch_state in batch_states
        )
    )

    def make_task(model_spec, batch_indexes):
        return {
            "config_path": str(run_config.path),
            "project_root": str(Path(__file__).resolve().parent),
            "model_spec": model_spec,
            "threads_per_worker": threads_per_worker,
            "batch_indexes": batch_indexes,
            "batch_states": [
                {
                    **batch_states[batch_index],
                    "images_paths": [
                        str(path)
                        for path in batch_states[batch_index]["images_paths"]
                    ],
                    "manifest_categories": manifest_categories,
                    "manifest_missing_models": manifest_missing_models,
                    "manifest_excluded_by_config": manifest_excluded_by_config,
                }
                for batch_index in batch_indexes
            ],
        }

    def merge_task_result(model_spec, batch_indexes, result):
        model_results = result["reports"]
        if checkpoint_manager is not None:
            checkpoint_manager.record_model(
                model_spec["model_name_opset"],
                {
                    batch_states[batch_index]["report_path"]: model_result
                    for batch_index, model_result in zip(
                        batch_indexes, model_results
                    )
                },
            )
        completed_models.add(model_spec["model_name_opset"])
        for batch_index, model_result in zip(batch_indexes, model_results):
            ReportManager.clear_model_failures(
                reports[batch_index], model_spec["model_name_opset"]
            )
            ReportManager.merge_model_result(reports[batch_index], model_result)
            pipeline_trace.event(
                "model.worker.completed",
                model=model_spec["model_name_opset"],
                batch=batch_states[batch_index]["report_path"].stem,
            )
            report_manager.save(
                batch_states[batch_index]["report_path"], reports[batch_index]
            )

    with pipeline_trace.stage(
        "models.parallel_run",
        model_count=len(model_specs),
        max_workers=model_workers,
        threads_per_worker=threads_per_worker,
    ):
        with ProcessPoolExecutor(
            max_workers=model_workers,
            mp_context=multiprocessing.get_context("spawn"),
        ) as executor:
            pending = {}

            def submit_next():
                try:
                    model_spec, batch_indexes = next(task_items)
                except StopIteration:
                    return False
                task = make_task(model_spec, batch_indexes)
                pipeline_trace.event(
                    "model.worker.submitted",
                    model=model_spec["model_name_opset"],
                    batches=[
                        batch_states[index]["report_path"].stem
                        for index in batch_indexes
                    ],
                )
                future = executor.submit(run_model_task, task)
                pending[future] = (model_spec, batch_indexes)
                return True

            for _ in range(min(model_workers * 2, len(model_specs))):
                if not submit_next():
                    break

            while pending:
                completed, _ = wait(pending, return_when=FIRST_COMPLETED)
                for future in completed:
                    model_spec, batch_indexes = pending.pop(future)
                    try:
                        result = future.result()
                    except Exception as error:
                        model_name_opset = model_spec["model_name_opset"]
                        worker_results = {}
                        for batch_index in batch_indexes:
                            worker_result = report_manager.new_report()
                            worker_result["failed_models"].append(model_name_opset)
                            worker_result["conversion_errors"][model_name_opset] = {
                                "worker": repr(error)
                            }
                            ReportManager.clear_model_failures(
                                reports[batch_index], model_name_opset
                            )
                            worker_results[
                                batch_states[batch_index]["report_path"]
                            ] = worker_result
                            reports[batch_index]["failed_models"].append(
                                model_name_opset
                            )
                            reports[batch_index]["conversion_errors"][
                                model_name_opset
                            ] = {"worker": repr(error)}
                            report_manager.save(
                                batch_states[batch_index]["report_path"],
                                reports[batch_index],
                            )
                            pipeline_trace.event(
                                "model.worker.failed",
                                level=logging.ERROR,
                                model=model_name_opset,
                                batch=batch_states[batch_index]["report_path"].stem,
                                error=repr(error),
                            )
                        if checkpoint_manager is not None:
                            checkpoint_manager.record_model(
                                model_name_opset, worker_results
                            )
                        completed_models.add(model_name_opset)
                    else:
                        merge_task_result(model_spec, batch_indexes, result)
                    submit_next()

    for batch_index, batch_state in enumerate(batch_states):
        report_manager.save(batch_state["report_path"], reports[batch_index])


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
    task_samples = batch_state.get("task_samples")
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
    prepared_task_inputs = None
    trace_context = {
        "batch": model_comparisons_file.stem,
        "model": model_name_opset,
    }

    try:
        if (
            backend_dispatcher.is_tvm
            and task_samples is None
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

        if task_samples is not None and model_data.get("external"):
            prepared_task_inputs = {}
            input_specs = model_config["input_specs"]
            for sample in task_samples:
                sample_id = str(sample["id"])
                if "body_recognition" in tags:
                    input_value, _, transform = ModelPreprocessor.preprocess_pose(
                        sample["image_path"],
                        model_name,
                        input_specs[0]["shape"],
                        input_specs[0]["dtype"],
                        bbox=sample.get("bbox"),
                    )
                    sample["pose_transform"] = transform
                    prepared_task_inputs[sample_id] = {
                        input_specs[0]["name"]: input_value
                    }
                else:
                    prepared_task_inputs[sample_id] = ModelPreprocessor.preprocess_speech(
                        sample["audio"],
                        sample["sample_rate"],
                        model_name,
                        input_specs,
                        model_config["model_dir"],
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
                prepared_task_inputs=prepared_task_inputs,
                task_samples=task_samples,
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
                        prepared_task_inputs=prepared_task_inputs,
                        task_samples=task_samples,
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

    script_dir = str(project_root)
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

    task_config = run_config.task
    task_type = task_config.get("type")
    all_task_samples = None
    if task_type:
        dataset_path = Path(task_config["dataset_path"])
        if not dataset_path.is_absolute():
            dataset_path = Path(script_dir) / dataset_path
        task_limit = task_config.get("limit", images_config.get("limit"))
        if task_type == "body_recognition":
            images_dir = Path(task_config["images_dir"])
            if not images_dir.is_absolute():
                images_dir = Path(script_dir) / images_dir
            all_task_samples = DatasetInputProvider.load_pose_samples(
                dataset_path, images_dir, task_limit
            )
            all_images_paths = [sample["image_path"] for sample in all_task_samples]
            all_images_paths.append(str(dataset_path))
        elif task_type == "speech_recognition":
            all_task_samples = DatasetInputProvider.load_speech_samples(
                dataset_path, task_limit
            )
            # Include the source dataset in checkpoint identity.
            all_images_paths = [str(dataset_path)]
        else:
            raise ValueError(f"Unsupported task.type: {task_type}")
        pipeline_trace.event(
            "task.samples_loaded", task=task_type, sample_count=len(all_task_samples)
        )
    else:
        all_images_paths = _discover_image_paths(images_folder, pipeline_trace)

    images_chunk = images_config["images_chunk"]
    starts_from = images_config["starts_from"]
    limit = (
        task_config.get("limit", len(all_task_samples))
        if all_task_samples is not None
        else images_config["limit"]
    )
    ends_at = starts_from + images_chunk
    batch_states = []

    while ends_at < limit + images_chunk:
        if all_task_samples is not None:
            task_samples = all_task_samples[starts_from:ends_at]
            images_paths = [
                sample["image_path"]
                for sample in task_samples
                if "image_path" in sample
            ]
        else:
            task_samples = None
            images_paths = all_images_paths[starts_from:ends_at]
        report_path = report_manager.chunk_path(starts_from, ends_at)
        print(" ---- Input Batch: " + str(starts_from) + " to " + str(ends_at))

        batch_states.append(
            {
                "images_paths": images_paths,
                "task_samples": task_samples,
                "starts_from": starts_from,
                "ends_at": ends_at,
                "text_prompts": None,
                "report_path": report_path,
                "problematic_models": None,
                "existing_models": set(),
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

    model_ids = [
        f"{model.model}-{int(model.opset)}"
        for model in model_orchestrator.all_models
    ]
    checkpoint_manager = None
    completed_models = set()
    checkpoint_settings = run_config.checkpoint
    if checkpoint_settings.get("enabled", True):
        with run_config.path.open("r", encoding="utf-8") as config_file:
            config_data = json.load(config_file)
        checkpoint_manager = CheckpointManager(
            script_dir,
            run_config.path,
            config_data,
            all_images_paths,
            model_ids,
            checkpoint_settings,
        )

    report_templates = {}
    if checkpoint_manager is not None and checkpoint_manager.resumed:
        completed_models = checkpoint_manager.completed_models
        stored_reports = checkpoint_manager.reports_for(
            [state["report_path"] for state in batch_states]
        )
        for batch_state in batch_states:
            report_path = batch_state["report_path"]
            report = stored_reports.get(
                str(report_path),
                report_manager.new_report(
                    manifest_categories,
                    manifest_missing_models,
                    manifest_excluded_by_config,
                ),
            )
            report_templates[str(report_path)] = report
            batch_state["existing_models"] = ReportManager.model_ids(
                report, model_ids
            )
            batch_state["problematic_models"] = (
                checkpoint_manager.problematic_models_for(report_path)
            )
            report_manager.save(report_path, report)
            batch_state["report_started"] = True
        pipeline_trace.event(
            "checkpoint.resumed",
            completed_models=len(completed_models),
            checkpoint=str(checkpoint_manager.state_path),
        )
    else:
        problematic_models_by_report = {}
        for batch_state in batch_states:
            report_path = batch_state["report_path"]
            report_template = report_manager.new_report(
                manifest_categories,
                manifest_missing_models,
                manifest_excluded_by_config,
            )
            if check_prob_models:
                if report_path.is_file():
                    existing_report = report_manager.load(report_path)
                    if not ReportManager.is_compatible(
                        existing_report, report_template
                    ):
                        raise ValueError(
                            f"Existing report is incompatible with this model "
                            f"selection: {report_path}. Use a different report "
                            "directory instead of overwriting it."
                        )
                    report_template = existing_report
                    batch_state["report_started"] = True
                problematic_models = (
                    report_manager.problematic_models(report_path)
                    if report_path.is_file()
                    else set()
                )
                batch_state["problematic_models"] = problematic_models
                print(
                    f"Isolating passes for {len(problematic_models)} problematic models "
                    f"from {report_path.name}"
                )
                problematic_models_by_report[str(report_path)] = sorted(
                    problematic_models
                )
            else:
                problematic_models_by_report[str(report_path)] = None

            if not check_prob_models and report_path.is_file():
                existing_report = report_manager.load(report_path)
                if not ReportManager.is_compatible(
                    existing_report, report_template
                ):
                    raise ValueError(
                        f"Existing report is incompatible with this model "
                        f"selection: {report_path}. Use a different report "
                        "directory instead of overwriting it."
                    )
                report_template = existing_report
                batch_state["existing_models"] = ReportManager.model_ids(
                    existing_report, model_ids
                )
                batch_state["report_started"] = True

            report_templates[str(report_path)] = report_template
            if checkpoint_manager is not None:
                batch_state["report_started"] = True

        if batch_states and not check_prob_models:
            completed_models = set.intersection(
                *(batch_state["existing_models"] for batch_state in batch_states)
            )

        if checkpoint_manager is not None:
            checkpoint_manager.initialize(
                report_templates,
                problematic_models_by_report,
                completed_model_ids=completed_models,
            )
            for batch_state in batch_states:
                report_manager.save(
                    batch_state["report_path"],
                    report_templates[str(batch_state["report_path"])],
                )
            pipeline_trace.event(
                "checkpoint.started",
                checkpoint=str(checkpoint_manager.state_path),
            )

    model_workers = run_config.runtime.get("tvm", {}).get("model_workers", 1)
    threads_per_worker = run_config.runtime.get("tvm", {}).get(
        "threads_per_worker", 0
    )
    parallel_models = model_workers > 1
    checkpoint_reports = (
        checkpoint_manager.reports_for(
            [state["report_path"] for state in batch_states]
        )
        if checkpoint_manager is not None
        else report_templates
    )

    if batch_states and parallel_models:
        problematic_union = None
        if check_prob_models:
            problematic_union = set().union(
                *(state["problematic_models"] for state in batch_states)
            )
        model_specs = list(
            model_orchestrator.get_models(
                problematic_union,
                metadata_only=True,
                exclude_models=completed_models,
            )
        )
        _run_parallel_models(
            model_specs,
            batch_states,
            run_config=run_config,
            report_manager=report_manager,
            pipeline_trace=pipeline_trace,
            model_workers=model_workers,
            threads_per_worker=threads_per_worker,
            manifest_categories=manifest_categories,
            manifest_missing_models=manifest_missing_models,
            manifest_excluded_by_config=manifest_excluded_by_config,
            reports=[
                checkpoint_reports.get(
                    str(state["report_path"]),
                    report_manager.new_report(
                        manifest_categories,
                        manifest_missing_models,
                        manifest_excluded_by_config,
                    ),
                )
                for state in batch_states
            ]
            if checkpoint_manager is not None
            else [
                report_templates[str(state["report_path"])]
                for state in batch_states
            ],
            completed_models=completed_models,
            checkpoint_manager=checkpoint_manager,
        )
    elif batch_states:
        problematic_union = None
        if check_prob_models:
            problematic_union = set().union(
                *(state["problematic_models"] for state in batch_states)
            )

        for model_data in model_orchestrator.get_models(
            problematic_union,
            exclude_models=completed_models,
        ):
            eligible_batches = [
                batch_state
                for batch_state in batch_states
                if (
                    not check_prob_models
                    or model_data["model_name_opset"]
                    in batch_state["problematic_models"]
                )
                and model_data["model_name_opset"]
                not in batch_state["existing_models"]
            ]
            if not eligible_batches:
                continue

            model_results = {}
            for batch_state in eligible_batches:
                current_report = report_manager.load(batch_state["report_path"])
                ReportManager.clear_model_failures(
                    current_report, model_data["model_name_opset"]
                )
                report_manager.save(batch_state["report_path"], current_report)
                before_report = (
                    current_report if checkpoint_manager is not None else None
                )
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
                if checkpoint_manager is not None:
                    after_report = report_manager.load(batch_state["report_path"])
                    model_results[batch_state["report_path"]] = (
                        ReportManager.extract_model_result(
                            before_report,
                            after_report,
                            model_data["model_name_opset"],
                        )
                    )

            if checkpoint_manager is not None and model_results:
                checkpoint_manager.record_model(
                    model_data["model_name_opset"], model_results
                )
                completed_models.add(model_data["model_name_opset"])
                pipeline_trace.event(
                    "checkpoint.model_saved",
                    model=model_data["model_name_opset"],
                )

        for batch_state in batch_states:
            if not batch_state["report_started"]:
                empty_report = report_manager.new_report(
                    manifest_categories,
                    manifest_missing_models,
                    manifest_excluded_by_config,
                )
                report_manager.save(batch_state["report_path"], empty_report)

    if checkpoint_manager is not None:
        checkpoint_manager.mark_run_completed()
        pipeline_trace.event(
            "checkpoint.completed",
            completed_models=len(checkpoint_manager.completed_models),
        )
    pipeline_trace.event("pipeline.completed", batch_count=len(batch_states))

if __name__ == "__main__":
    main()
