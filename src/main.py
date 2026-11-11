import sys
from os import listdir
from pathlib import Path
from os.path import isfile, join

project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.configs.config import load_pipeline_config
from src.model_orchestrator.model_orchestrator import ModelOrchestrator
from src.dispatchers import BackendDispatcher, ModelComparisonDispatcher
from src.reports import ReportManager


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
    images_folder = script_dir + "/" + images_config["images_folder_rel_path"]

    report_manager = ReportManager(
        script_dir, general_config["report_file_base_rel_path"]
    )
    
    backend_dispatcher = BackendDispatcher(run_config)
    comparison_dispatcher = ModelComparisonDispatcher()
    onnx_runner = backend_dispatcher.onnx_runner

    check_prob_models = general_config["check_reports_for_problematic_models"]
    model_orchestrator = ModelOrchestrator(
        general_config,
        hub_config,
        script_dir,
        check_prob_models=check_prob_models,
    )
    manifest_categories = model_orchestrator.manifest_categories
    manifest_missing_models = model_orchestrator.manifest_missing_models
    manifest_excluded_by_config = model_orchestrator.manifest_excluded_by_config
 
    all_images_paths = [join(images_folder, f) for f in listdir(images_folder) \
        if isfile(join(images_folder, f))]

    all_images_paths.sort()

    images_chunk = images_config["images_chunk"]
    starts_from = images_config["starts_from"]
    limit = images_config["limit"]
    ends_at = starts_from + images_chunk

    while ends_at < limit + images_chunk:

        model_comparisons = report_manager.new_report(
            manifest_categories,
            manifest_missing_models,
            manifest_excluded_by_config,
        )

        images_paths = None
        inputs = None

        images_paths = [x for x in all_images_paths[starts_from:ends_at]]
        print(" ---- Input Batch: " + str(starts_from) + " to " + str(ends_at))
        model_comparisons_file = report_manager.chunk_path(starts_from, ends_at)

        problematic_models = None
        if check_prob_models:
            problematic_models = report_manager.problematic_models(
                model_comparisons_file
            )
            print(
                f"Isolating passes for {len(problematic_models)} problematic models "
                f"from {model_comparisons_file.name}"
            )

        # Ensure even empty isolation chunks get a completion report.
        report_manager.save(model_comparisons_file, model_comparisons)

        for model_data in model_orchestrator.get_models(problematic_models):
            model_name = model_data["model_name"]
            model_name_opset = model_data["model_name_opset"]
            tags = model_data["tags"]
            first_input = model_data["first_input"]
            model_shape = model_data["model_shape"]
            model_config = model_data["model_config"]
            model_path = model_data["model_path"]
            model = model_data["model"]
            original_hash = model_data["original_hash"]
            opt_model_path = model_data["opt_model_path"]

            # Load passes.
            if not optimizer_config.get("enabled", True):
                passes = []
            else:
                passes = (
                    optimizer_config["passes"]
                    if optimizer_config["passes"]
                    else backend_dispatcher.optimizer_helper.get_optimizer_passes()
                )

            print("Running original model...")
            print(model_path)
            base_model_out = None
            base_relax_mod = None

            try:
                base_model_out, base_relax_mod = backend_dispatcher.run_baseline(
                    model,
                    tags,
                    first_input,
                    model_shape,
                    images_paths,
                    model_config,
                    include_certainties,
                )
            except Exception as e:
                print(e)
                print(model_name + " - a base model error occured!")
                model_comparisons["failed_models"].append(model_name_opset)
                model_comparisons["conversion_errors"][model_name_opset] = {
                    "baseline": repr(e)
                }
                report_manager.save(model_comparisons_file, model_comparisons)
                continue

            model_comparisons["base_models_run"] += 1

            model_comparisons[model_name_opset] = {
                "skipped": [],
                "failed": [],
                "blocked": [],
                "dependency_checks": {},
                "dependency_failures": {},
                "different": 0,
                "run": 0
            }

            if not passes:
                model_comparisons[model_name_opset]["baseline_only"] = True
                report_manager.save(model_comparisons_file, model_comparisons)

            run_individual_passes = general_config["run_individual_passes"]
            passes_to_run = backend_dispatcher.passes_to_run(
                passes, run_individual_passes
            )

            for current_pass in passes_to_run:
                opt_model_out, conversion_failed, current_pass = (
                    backend_dispatcher.run_optimization_pass(
                        current_pass,
                        base_relax_mod=base_relax_mod,
                        base_model_out=base_model_out,
                        model=model,
                        tags=tags,
                        first_input=first_input,
                        model_shape=model_shape,
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
                        run_individual_passes=run_individual_passes,
                    )
                )

                if not conversion_failed and opt_model_out is not None:
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
                    )

                report_manager.save(model_comparisons_file, model_comparisons)
                
                if not run_individual_passes:
                    break

            report_manager.save(model_comparisons_file, model_comparisons)
        
        starts_from += images_chunk
        ends_at += images_chunk

if __name__ == "__main__":
    main()
