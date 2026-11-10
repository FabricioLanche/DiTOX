import os
import sys
import json
import hashlib
import subprocess
import numpy as np
from os import listdir
from pathlib import Path
from os.path import isfile, join
from helpers.model_helper import load_config
import onnx
from onnx import hub

from helpers.optimizer_helper import OptimizerHelper
from helpers.model_helper import get_size, get_model_path, load_config, \
    prepare_model_input_dimension, prepare_model_shape

from helpers.yolov2_extractor import YOLOV2Extractor
from helpers.ssd_extractor import SSDExtractor

from evaluators.object_detection import ObjectDetectionEvaluator

from comparators.classification import ClassificationComparator
from comparators.ssd import SSDComparator
from comparators.yolov3 import YOLOV3Comparator

from runners.onnx_runner import ONNXRunner
from runners.tvm_runner import TVMRunner
from builders.tvm_builder import TVMBuilder


def _has_dissimilarity(evaluation):
    values = np.asarray(evaluation.get("percentage_dissimilar", []), dtype=float)
    return bool(np.any(values[np.isfinite(values)] > 0))


def _report_chunk_path(script_dir, report_rel_path, starts_from, ends_at):
    report_path = Path(script_dir) / report_rel_path.lstrip("/\\")
    report_stem = report_path.stem.split("_chunk", 1)[0]
    return report_path.with_name(
        f"{report_stem}_chunk_{starts_from}_{ends_at}{report_path.suffix}"
    )


def _problematic_models_from_report(report_path):
    with open(report_path, "r", encoding="utf-8") as report_file:
        report = json.load(report_file)

    return (
        set(report.get("failed_models", []))
        | {
            model
            for model, error in report.get("conversion_errors", {}).items()
            if error
        }
        | {
            model
            for model, result in report.items()
            if isinstance(result, dict)
            and any(result.get(key) for key in ("different", "failed", "blocked"))
        }
    )


def main():

    config_path = sys.argv[1] if len(sys.argv) > 1 else './config.json'
    with open(config_path, "r") as f:
        config = json.load(f)
    images_config = config["images"]
    general_config = config["general"]
    hub_config = config["hub"]
    optimizer_config = config["optimizer"]

    include_certainties = general_config["include_certainties"]
    enable_kt_on_one_dim_tensor = general_config["enable_kt_on_one_dim_tensor"]

    script_dir = os.path.dirname(os.path.realpath(__file__))
    images_folder = script_dir + "/" + images_config["images_folder_rel_path"]

    manifest_path = hub_config.get("model_manifest_rel_path")
    manifest_categories = None
    manifest_missing_models = []
    manifest_excluded_by_config = []
    if manifest_path:
        manifest_file = Path(script_dir) / manifest_path.lstrip("/\\")
        with open(manifest_file, "r", encoding="utf-8") as manifest_stream:
            manifest = json.load(manifest_stream)
        manifest_categories = {
            (item["model"], int(item["opset"])): item["category"]
            for item in manifest["models"]
        }
        included_categories = set(hub_config["tags_of_models_to_consider"])
        excluded_names = set(general_config.get("exclude_name_filters", []))
        manifest_excluded_by_config = [
            f"{model_name}-{opset}"
            for (model_name, opset), category in manifest_categories.items()
            if category not in included_categories
            or f"{model_name}-{opset}" in excluded_names
            or opset < hub_config["opset_bottom_threshold"]
        ]
        catalog = hub.list_models()
        catalog_by_id = {
            (item.model, int(item.opset)): item
            for item in catalog
        }
        all_models = [
            catalog_by_id[model_id]
            for model_id in manifest_categories
            if model_id in catalog_by_id
        ]
        manifest_missing_models = [
            f"{model_name}-{opset}"
            for model_name, opset in manifest_categories
            if (model_name, opset) not in catalog_by_id
        ]
        if manifest_missing_models:
            print(
                "Manifest models absent from current ONNX Hub catalog: "
                + ", ".join(manifest_missing_models)
            )
    else:
        all_models = hub.list_models(tags=hub_config["tags"])

    hub.set_dir(script_dir + "/" + hub_config["cache_folder_rel_path"])
    
    report_file_base_rel_path = general_config["report_file_base_rel_path"]
    
    backend = general_config.get("backend", "ort")
    onnx_runner = ONNXRunner({})
    tvm_runner = TVMRunner(config.get("tvm", {})) if backend == "tvmr" else None
    tvm_builder = TVMBuilder() if backend == "tvmr" else None
    optimization_target = "tvm" if backend == "tvmr" else "onnx"
    opt_helper = OptimizerHelper(target=optimization_target)

    check_prob_models = general_config["check_reports_for_problematic_models"]
 
    skip_until = general_config["skip_until_model_id"]
    run_up_to = general_config["run_up_to_model_id"]

    all_images_paths = [join(images_folder, f) for f in listdir(images_folder) \
        if isfile(join(images_folder, f))]

    all_images_paths.sort()

    images_chunk = images_config["images_chunk"]
    starts_from = images_config["starts_from"]
    limit = images_config["limit"]
    ends_at = starts_from + images_chunk

    while ends_at < limit + images_chunk:

        json_object = None
        model_comparisons = {}
        model_comparisons["no_dissimilar"] = 0
        model_comparisons["base_models_run"] = 0
        model_comparisons["model_instances_run"] = 0
        model_comparisons["failed_conversions_no"] = 0
        model_comparisons["skipped_models"] = []
        model_comparisons["failed_models"] = []
        model_comparisons["conversion_errors"] = {}
        if manifest_categories is not None:
            model_comparisons["manifest_models_expected"] = len(manifest_categories)
            model_comparisons["manifest_models_not_found"] = manifest_missing_models
            model_comparisons["manifest_models_excluded_by_config"] = (
                manifest_excluded_by_config
            )
            model_comparisons["manifest_models_selected_by_config"] = (
                len(manifest_categories)
                - len(manifest_missing_models)
                - len(manifest_excluded_by_config)
            )

        images_paths = None
        inputs = None

        images_paths = [x for x in all_images_paths[starts_from:ends_at]]
        print(" ---- Input Batch: " + str(starts_from) + " to " + str(ends_at))
        model_comparisons_file = _report_chunk_path(
            script_dir, report_file_base_rel_path, starts_from, ends_at
        )

        problematic_models = None
        if check_prob_models:
            problematic_models = _problematic_models_from_report(model_comparisons_file)
            print(
                f"Isolating passes for {len(problematic_models)} problematic models "
                f"from {model_comparisons_file.name}"
            )

        # Ensure even empty isolation chunks get a completion report.
        json_object = json.dumps(model_comparisons, indent=2)

        model_no = 0
        for model_obj in all_models:

            model_no += 1
            if (model_no < skip_until or model_no > run_up_to):
                continue

            model_name = model_obj.model
            model_opset = model_obj.opset
            model_name_opset = model_name + "-" + str(model_opset)

            if check_prob_models and model_name_opset not in problematic_models:
                continue

            excluded_models = general_config.get("exclude_name_filters", [])
            if model_name_opset in excluded_models:
                continue

            # Note: Enable to print models with opset.
            # print(model_name_opset)
            manifest_category = None
            if manifest_categories is not None:
                manifest_category = manifest_categories[(model_name, int(model_opset))]
                tags = [manifest_category]
                if manifest_category != "text":
                    tags.append("vision")
            else:
                tags = model_obj.tags

            name_filters = general_config["name_filters"]
            is_exact_match = general_config["match_filter_exact"]
            
            if len(name_filters) != 0:
                filter_in_name = False
                for filter in name_filters:
                    if filter in model_name_opset:
                        print(model_name_opset)
                    if is_exact_match and filter == model_name_opset:
                        filter_in_name = True
                        break
                    elif not is_exact_match and filter in model_name_opset:
                        filter_in_name = True
                        break

                if not filter_in_name:
                    continue

            tag_found = False
            if len(hub_config["tags_of_models_to_consider"]) != 0:
                for tag_to_consider in hub_config["tags_of_models_to_consider"]:
                    if tag_to_consider in tags:
                        tag_found = True
                        break

                if not tag_found:
                    continue

            if model_opset < hub_config["opset_bottom_threshold"]:
                continue

            print("Model Number: " + str(model_no))
            print("Model Name: " + model_name)
            print(model_obj)

            img_dimension = prepare_model_input_dimension(model_obj)

            keywords = ["tf", "keras", "torch", "tflite", "densenet", \
                "resnet", "mobilenet", "inception", "shufflenet", "googlenet", "version-rfb"]

            # Check if any known library is in name.
            # If not, PyTorch preprocessing configuration will be used.
            contains_keyword = False
            for keyword in keywords:
                if keyword in model_name.lower():
                    contains_keyword = True
                    break

            first_input = model_obj.metadata["io_ports"]["inputs"][0]

            print(first_input["shape"])

            model_shape = prepare_model_shape(model_obj)

            model_config = {
                "model_name": model_name + "_torch" if not contains_keyword else "",
                "input_name": first_input["name"],
                "input_shape": model_shape,
                "input_dimension": img_dimension
            }

            model_path = get_model_path(script_dir, model_obj)

            model = hub.load(model_name, opset=model_opset)

            original_hash = hashlib.md5(open(model_path,'rb').read()).hexdigest()
            opt_model_path = model_path.replace(".onnx", "_opt.onnx")

            # Load passes.
            if not optimizer_config.get("enabled", True):
                passes = []
            else:
                passes = optimizer_config["passes"] if len(optimizer_config["passes"]) != 0 else \
                    opt_helper.get_optimizer_passes()

            print("Running original model...")
            print(model_path)
            base_model_out = None
            base_relax_mod = None

            try:
                if "text" not in tags:
                    if backend == "tvmr":
                        base_relax_mod = tvm_builder.build_relax(model, {first_input["name"]: model_shape})
                        base_model_out = tvm_runner.execute_relax_model(base_relax_mod, images_paths, config=model_config, include_certainties=include_certainties)
                    else:
                        base_model_out = onnx_runner.execute_onnx_model(model, images_paths, config=model_config, include_certainties=include_certainties)
                else:
                    print("Text models not supported on this version.")
            except Exception as e:
                print(e)
                print(model_name + " - a base model error occured!")
                model_comparisons["failed_models"].append(model_name_opset)
                model_comparisons["conversion_errors"][model_name_opset] = {
                    "baseline": repr(e)
                }
                json_object = json.dumps(model_comparisons, indent=2)
                with open(model_comparisons_file, "w") as outfile:
                    outfile.write(json_object)
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
                json_object = json.dumps(model_comparisons, indent=2)
                with open(model_comparisons_file, "w") as outfile:
                    outfile.write(json_object)

            run_individual_passes = general_config["run_individual_passes"]
            if backend == "tvmr":
                passes_to_run = (
                    passes if run_individual_passes else (["all"] if passes else [])
                )
            else:
                passes_to_run = passes if run_individual_passes else ["all"]

            for current_pass in passes_to_run:
                conversion_failed = False
                opt_model_out = None

                if backend == "tvmr":
                    try:
                        if current_pass == "all":
                            print("Running optimized TVM model. Pass: all")
                            opt_model_out = tvm_runner.execute_relax_model(
                                base_relax_mod,
                                images_paths,
                                config=model_config,
                                include_certainties=include_certainties,
                                optimized=True,
                            )
                        else:
                            required_dependencies = opt_helper.get_tvm_isolation_dependencies(
                                current_pass
                            )
                            included_dependencies = []
                            dependency_failure = None
                            dependency_checks = []

                            for dependency in required_dependencies:
                                included_dependencies.append(dependency)
                                dependency_mod = tvm_builder.build_relax(
                                    model,
                                    {first_input["name"]: model_shape},
                                )
                                dependency_pipeline = opt_helper.get_tvm_isolation_pipeline(
                                    current_pass,
                                    dependencies=included_dependencies,
                                    include_optimization=False,
                                )
                                try:
                                    dependency_out = tvm_runner.execute_relax_model(
                                        dependency_mod,
                                        images_paths,
                                        config=model_config,
                                        include_certainties=include_certainties,
                                        relax_pipeline=dependency_pipeline,
                                    )
                                except Exception as error:
                                    dependency_failure = {
                                        "pass": dependency,
                                        "error": repr(error),
                                    }
                                    dependency_checks.append(
                                        {
                                            "pass": dependency,
                                            "status": "failed",
                                            "error": repr(error),
                                        }
                                    )
                                    break

                                dependency_evaluation = tvm_runner.evaluate(
                                    base_model_out,
                                    dependency_out,
                                    type=tags,
                                    include_certainties=include_certainties,
                                    enable_kt_on_one_dim_tensor=enable_kt_on_one_dim_tensor,
                                )
                                dependency_different = _has_dissimilarity(
                                    dependency_evaluation
                                )
                                dependency_checks.append(
                                    {
                                        "pass": dependency,
                                        "status": (
                                            "different"
                                            if dependency_different
                                            else "passed"
                                        ),
                                        "percentage_dissimilar": dependency_evaluation.get(
                                            "percentage_dissimilar"
                                        ),
                                    }
                                )
                                if dependency_different:
                                    dependency_failure = {
                                        "pass": dependency,
                                        "reason": "dependency output differs from default TVM output",
                                    }
                                    break

                            model_comparisons[model_name_opset]["dependency_checks"][
                                current_pass
                            ] = dependency_checks

                            if dependency_failure is not None:
                                model_comparisons[model_name_opset]["dependency_failures"][
                                    current_pass
                                ] = dependency_failure
                                model_comparisons[model_name_opset]["blocked"].append(
                                    current_pass
                                )
                                conversion_failed = True
                            else:
                                print(
                                    f"Running isolated TVM optimization: {current_pass}"
                                )
                                candidate_mod = tvm_builder.build_relax(
                                    model,
                                    {first_input["name"]: model_shape},
                                )
                                candidate_pipeline = opt_helper.get_tvm_isolation_pipeline(
                                    current_pass,
                                    dependencies=required_dependencies,
                                    include_optimization=True,
                                )
                                opt_model_out = tvm_runner.execute_relax_model(
                                    candidate_mod,
                                    images_paths,
                                    config=model_config,
                                    include_certainties=include_certainties,
                                    relax_pipeline=candidate_pipeline,
                                )
                    except Exception as e:
                        print(f"TVM Relax pass {current_pass} error: {e}")
                        if current_pass not in model_comparisons[model_name_opset]["blocked"]:
                            if model_name_opset not in model_comparisons["conversion_errors"]:
                                model_comparisons["conversion_errors"][model_name_opset] = {}
                            model_comparisons["conversion_errors"][model_name_opset][current_pass] = repr(e)
                            model_comparisons[model_name_opset]["failed"].append(current_pass)
                            model_comparisons["failed_conversions_no"] += 1
                        conversion_failed = True
                else:
                    # --- ORT branch ---
                    try:
                        if not run_individual_passes:
                            p = subprocess.Popen(['python3 -m onnxoptimizer ' + model_path + " " + opt_model_path], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                            current_pass = "all"
                        else:
                            p = subprocess.Popen(['python3 -m onnxoptimizer ' + model_path + " " + opt_model_path + " -p " + current_pass], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True)
                        
                        (output, err) = p.communicate()  
                        p.wait()
                        if p.returncode != 0:
                            print(output)
                            if model_name_opset not in model_comparisons["conversion_errors"]:
                                model_comparisons["conversion_errors"][model_name_opset] = {}
                            model_comparisons["conversion_errors"][model_name_opset][current_pass] = repr(output)
                            model_comparisons["failed_conversions_no"] += 1
                            conversion_failed = True

                    except subprocess.CalledProcessError as e:
                        print('Fatal error: code={}, out="{}"'.format(e.returncode, e.output))

                    opt_hash = None
                    try:
                        opt_hash = hashlib.md5(open(opt_model_path,'rb').read()).hexdigest()
                    except:
                        conversion_failed = True
                    if (opt_hash is not None and original_hash == opt_hash):
                        print(current_pass + " has no effect on model " + model_name)
                        model_comparisons[model_name_opset]["skipped"].append(current_pass)
                    elif (not conversion_failed):
                        print("Running optimized model. Pass: " + current_pass)
                        print(opt_model_path)
                        try:
                            onnx_model = onnx.load(opt_model_path)
                            
                            if "text" not in tags:
                                opt_model_out = onnx_runner.execute_onnx_model(onnx_model, images_paths, config=model_config, include_certainties=include_certainties)

                        except Exception as e:
                            if model_name_opset not in model_comparisons["conversion_errors"]:
                                model_comparisons["conversion_errors"][model_name_opset] = {}
                            model_comparisons["conversion_errors"][model_name_opset][current_pass] = repr(e)
                            model_comparisons[model_name_opset]["failed"].append(current_pass)
                            conversion_failed = True

                if not conversion_failed and opt_model_out is not None:
                    runner_eval = tvm_runner if backend == "tvmr" else onnx_runner

                    if ("classification" in tags):
                        evaluation = runner_eval.evaluate(base_model_out, opt_model_out, type=tags, include_certainties=include_certainties)
                        print(evaluation)
                        comparator = ClassificationComparator(evaluation, model_comparisons)
                        comparator.update(model_name_opset, current_pass, include_certainties=include_certainties)

                    elif ("object detection segmentation" in tags and "RetinaNet" not in model_name_opset):
                        model_comparisons[model_name_opset][current_pass] = {}
                        evaluation = onnx_runner.evaluate(base_model_out, opt_model_out, type=tags, include_certainties=include_certainties, enable_kt_on_one_dim_tensor=enable_kt_on_one_dim_tensor)
                        print(evaluation)
                        if "YOLOv3" in model_name_opset:
                            comparator = YOLOV3Comparator(evaluation, model_comparisons)
                            comparator.update(model_name_opset, model, base_model_out, opt_model_out, current_pass)

                        elif "YOLOv2-9" in model_name_opset:
                            extractor = YOLOV2Extractor()

                            metrics_5 = []
                            metrics_7 = []
                            metrics_9 = []
                            evaluator_5 = ObjectDetectionEvaluator(iou_threshold=0.5)
                            evaluator_7 = ObjectDetectionEvaluator(iou_threshold=0.75)
                            evaluator_9 = ObjectDetectionEvaluator(iou_threshold=0.9)

                            output = [node.name for node in model.graph.output]

                            for img_key in base_model_out.keys():
                                base_image = base_model_out[img_key]
                                opt_image = opt_model_out[img_key]
                                base_data = extractor.extract_yolo_outputs(base_image)
                                base_bboxes = base_data[0]
                                base_labels = base_data[1]
                                base_scores = base_data[2]

                                opt_data = extractor.extract_yolo_outputs(opt_image)
                                opt_bboxes = opt_data[0]
                                opt_labels = opt_data[1]
                                opt_scores = opt_data[2]

                                # Skip undetected classes.
                                if (base_labels == [] and opt_labels == []) or (base_bboxes == [] and opt_bboxes == []):
                                    continue

                                metric_5 = evaluator_5.compute_metrics(base_bboxes, base_labels, base_scores, opt_bboxes, opt_labels, opt_scores)
                                metrics_5.append(metric_5)

                                metric_7 = evaluator_7.compute_metrics(base_bboxes, base_labels, base_scores, opt_bboxes, opt_labels, opt_scores)
                                metrics_7.append(metric_7)

                                metric_9 = evaluator_9.compute_metrics(base_bboxes, base_labels, base_scores, opt_bboxes, opt_labels, opt_scores)
                                metrics_9.append(metric_9)

                            model_comparisons[model_name_opset][current_pass][output[0]] = {
                                "metrics_0_5": {
                                    "avg_f1": np.mean([o["F1"] for o in metrics_5]) * 100,
                                    "avg_prec": np.mean([o["precision"] for o in metrics_5]) * 100,
                                    "avg_recall": np.mean([o["recall"] for o in metrics_5]) * 100,
                                    "avg_mAP": np.mean([o["mAP"] for o in metrics_5]) * 100,
                                    "avg_IoU": np.mean([o["IoU"] for o in metrics_5]) * 100,
                                },
                                "metrics_0_7": {
                                    "avg_f1": np.mean([o["F1"] for o in metrics_7]) * 100,
                                    "avg_prec": np.mean([o["precision"] for o in metrics_7]) * 100,
                                    "avg_recall": np.mean([o["recall"] for o in metrics_7]) * 100,
                                    "avg_mAP": np.mean([o["mAP"] for o in metrics_7]) * 100,
                                    "avg_IoU": np.mean([o["IoU"] for o in metrics_7]) * 100,
                                },
                                "metrics_0_9": {
                                    "avg_f1": np.mean([o["F1"] for o in metrics_9]) * 100,
                                    "avg_prec": np.mean([o["precision"] for o in metrics_9]) * 100,
                                    "avg_recall": np.mean([o["recall"] for o in metrics_9]) * 100,
                                    "avg_mAP": np.mean([o["mAP"] for o in metrics_9]) * 100,
                                    "avg_IoU": np.mean([o["IoU"] for o in metrics_9]) * 100,
                                }
                            }

                        elif "SSD" in model_name_opset:
                            extractor = SSDExtractor()

                            metrics_5 = []
                            metrics_7 = []
                            metrics_9 = []
                            evaluator_5 = ObjectDetectionEvaluator(iou_threshold=0.5)
                            evaluator_7 = ObjectDetectionEvaluator(iou_threshold=0.75)
                            evaluator_9 = ObjectDetectionEvaluator(iou_threshold=0.9)

                            output = [node.name for node in model.graph.output]

                            for img_key in base_model_out.keys():
                                base_image = base_model_out[img_key]
                                opt_image = opt_model_out[img_key]

                                (base_bboxes, base_labels, base_scores) = extractor.extract_ssd_outputs(base_image)
                                (opt_bboxes, opt_labels, opt_scores) = extractor.extract_ssd_outputs(opt_image)

                                if (base_labels == [] and opt_labels == []) or (base_bboxes == [] and opt_bboxes == []):
                                    continue

                                metric_5 = evaluator_5.compute_metrics(base_bboxes, base_labels, base_scores, opt_bboxes, opt_labels, opt_scores)
                                metrics_5.append(metric_5)

                                metric_7 = evaluator_7.compute_metrics(base_bboxes, base_labels, base_scores, opt_bboxes, opt_labels, opt_scores)
                                metrics_7.append(metric_7)

                                metric_9 = evaluator_9.compute_metrics(base_bboxes, base_labels, base_scores, opt_bboxes, opt_labels, opt_scores)
                                metrics_9.append(metric_9)

                            
                            model_comparisons[model_name_opset][current_pass][output[0]] = {
                                "metrics_0_5": {
                                    "avg_f1": np.mean([o["F1"] for o in metrics_5]) * 100,
                                    "avg_prec": np.mean([o["precision"] for o in metrics_5]) * 100,
                                    "avg_recall": np.mean([o["recall"] for o in metrics_5]) * 100,
                                    "avg_mAP": np.mean([o["mAP"] for o in metrics_5]) * 100,
                                    "avg_IoU": np.mean([o["IoU"] for o in metrics_5]) * 100,
                                },
                                "metrics_0_7": {
                                    "avg_f1": np.mean([o["F1"] for o in metrics_7]) * 100,
                                    "avg_prec": np.mean([o["precision"] for o in metrics_7]) * 100,
                                    "avg_recall": np.mean([o["recall"] for o in metrics_7]) * 100,
                                    "avg_mAP": np.mean([o["mAP"] for o in metrics_7]) * 100,
                                    "avg_IoU": np.mean([o["IoU"] for o in metrics_7]) * 100,
                                },
                                "metrics_0_9": {
                                    "avg_f1": np.mean([o["F1"] for o in metrics_9]) * 100,
                                    "avg_prec": np.mean([o["precision"] for o in metrics_9]) * 100,
                                    "avg_recall": np.mean([o["recall"] for o in metrics_9]) * 100,
                                    "avg_mAP": np.mean([o["mAP"] for o in metrics_9]) * 100,
                                    "avg_IoU": np.mean([o["IoU"] for o in metrics_9]) * 100,
                                }
                            }

                            cmp_object = {}
                            if (evaluation["percentage_dissimilar1"][1] != -1):
                                cmp_object["first"] = evaluation["percentage_dissimilar1"][1]
                            if (evaluation["percentage_dissimilar5"][1] != -1):
                                cmp_object["top5"] = evaluation["percentage_dissimilar5"][1]

                            comparator = SSDComparator(evaluation, model_comparisons)
                            comparator.update(model_name_opset, current_pass, include_certainties=include_certainties, array_index=1)
                    else:
                        evaluation = onnx_runner.evaluate(base_model_out, opt_model_out, type=tags, include_certainties=include_certainties)
                        output =[node.name for node in model.graph.output]
                        model_comparisons[model_name_opset][current_pass] = {}

                        for i, output_node in enumerate(output):
                            cmp_object = {}
                            if (evaluation["percentage_dissimilar1"][i] != -1):
                                cmp_object["first"] = evaluation["percentage_dissimilar1"][i]
                            if (evaluation["percentage_dissimilar5"][i] != -1):
                                cmp_object["top5"] = evaluation["percentage_dissimilar5"][i]
                            cmp_object["topK"] = evaluation["percentage_dissimilar"][i]

                            model_comparisons[model_name_opset][current_pass][output[i]] = cmp_object

                        # This assumes the new model has the same output structure
                        # with SSD (boxes, classes, scores).
                        # TODO: Extend to work for every model.
                        comparator = SSDComparator(evaluation, model_comparisons)
                        comparator.update(model_name_opset, current_pass, include_certainties=include_certainties, array_index=1)
                        
                    model_comparisons["model_instances_run"] += 1
                    model_comparisons[model_name_opset]["run"] += 1
                
                    json_object = json.dumps(model_comparisons, indent=2)

                json_object = json.dumps(model_comparisons, indent=2)
                with open(model_comparisons_file, "w") as outfile:
                    outfile.write(json_object)
                
                if not run_individual_passes:
                    break

            if json_object is not None:
                with open(model_comparisons_file, "w") as outfile:
                    outfile.write(json_object)
        
        starts_from += images_chunk
        ends_at += images_chunk

if __name__ == "__main__":
    main()
