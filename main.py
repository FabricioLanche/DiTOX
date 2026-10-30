import os
import json
import hashlib
import subprocess
import numpy as np
from os import listdir
from os.path import isfile, join
from helpers.model_helper import load_config
import onnx

from helpers.optimizer_helper import OptimizerHelper
from helpers.model_orchestator import ModelOrchestrator

from helpers.yolov2_extractor import YOLOV2Extractor
from helpers.ssd_extractor import SSDExtractor

from evaluators.object_detection import ObjectDetectionEvaluator

from comparators.classification import ClassificationComparator
from comparators.ssd import SSDComparator
from comparators.yolov3 import YOLOV3Comparator

from runners.onnx_runner import ONNXRunner
from runners.tvm_runner import TVMRunner

def main():

    config = load_config('./config.json')
    images_config = config["images"]
    general_config = config["general"]
    hub_config = config["hub"]
    optimizer_config = config["optimizer"]
    runtime_config = config.get("runtime", {})
    backend = runtime_config.get("backend", "onnx").lower()
    if backend not in ("onnx", "tvm"):
        raise ValueError(f"Unsupported runtime backend: {backend}")

    include_certainties = general_config["include_certainties"]
    enable_kt_on_one_dim_tensor = general_config["enable_kt_on_one_dim_tensor"]

    script_dir = os.path.dirname(os.path.realpath(__file__))
    images_folder = script_dir + "/" + images_config["images_folder_rel_path"]

    model_comparisons_file = script_dir + "/" + general_config["report_file_base_rel_path"]
    
    onnx_runner = ONNXRunner({})
    tvm_runner = TVMRunner(runtime_config) if backend == "tvm" else None
    opt_helper = OptimizerHelper("tvmr" if backend == "tvm" else "ort")

    check_prob_models = general_config["check_reports_for_problematic_models"]
    model_comparisons_file_exists = os.path.exists(model_comparisons_file)
    if check_prob_models:
        if model_comparisons_file_exists:
            # Use model comparisons file to compare problematic models.
            f = open(model_comparisons_file, "r")
            base_object = json.load(f)

            different_models = []
                
            for key in base_object:
                elem = base_object[key]
                if isinstance(elem, dict) and "different" in elem and elem["different"] != 0:
                    different_models.append(key)
            print(different_models)
        else:
            print("Warning: check for problematic models is enabled but comparisons file does not exist. Skipping...")
 
    model_orchestrator = ModelOrchestrator(
        general_config,
        hub_config,
        script_dir,
        different_models if check_prob_models and model_comparisons_file_exists else [],
        check_prob_models,
        model_comparisons_file_exists,
        backend,
    )

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

        images_paths = None

        images_paths = [x for x in all_images_paths[starts_from:ends_at]]
        print(" ---- Input Batch: " + str(starts_from) + " to " + str(ends_at))
        model_comparisons_file = model_comparisons_file.split("_chunk")[0] + "_chunk_" + str(starts_from) + "_" + str(ends_at) + ".json"

        for model_data in model_orchestrator.get_models():
            model_name = model_data["model_name"]
            model_name_opset = model_data["model_name_opset"]
            tags = model_data["tags"]
            model_config = model_data["model_config"]
            model_path = model_data["model_path"]
            model = model_data["model"]
            original_hash = model_data["original_hash"]
            opt_model_path = model_data["opt_model_path"]

            # Load passes.
            passes = optimizer_config["passes"] if len(optimizer_config["passes"]) != 0 else \
                opt_helper.get_optimizer_passes()

            print("Running original model...")
            print(model_path)
            base_model_out = None
            prepared_inputs = None

            try:
                if "text" not in tags:
                    if backend == "tvm":
                        prepared_inputs = onnx_runner.prepare_onnx_inputs(
                            model, images_paths, model_config
                        )
                        base_model_out = onnx_runner.execute_onnx_model(
                            model,
                            images_paths,
                            config=model_config,
                            include_certainties=include_certainties,
                            prepared_inputs=prepared_inputs,
                        )
                    else:
                        base_model_out = onnx_runner.execute_onnx_model(model, images_paths, config=model_config, include_certainties=include_certainties)
                else:
                    print("Text models not supported on this version.")
            except Exception as e:
                print(e)
                print(model_name + " - a base model error occured!")
                model_comparisons["failed_models"].append(model_name)
                continue

            model_comparisons["base_models_run"] += 1

            model_comparisons[model_name_opset] = {
                "skipped": [],
                "failed": [],
                "different": 0,
                "run": 0
            }

            run_individual_passes = general_config["run_individual_passes"]

            if backend == "tvm":
                if run_individual_passes:
                    pass_runs = [("C0", [])] + [
                        (f"C{index + 1}_{pass_name}", passes[:index + 1])
                        for index, pass_name in enumerate(passes)
                    ]
                else:
                    pass_runs = [("all", passes)]
            else:
                pass_runs = [(pass_name, []) for pass_name in passes]

            for current_pass, tvm_passes in pass_runs:
                conversion_failed = False
                should_compare = True
                if backend == "onnx":
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
                    if not conversion_failed:
                        try:
                            opt_hash = hashlib.md5(open(opt_model_path, 'rb').read()).hexdigest()
                        except:
                            conversion_failed = True

                    if opt_hash is not None and original_hash == opt_hash:
                        print(current_pass + " has no effect on model " + model_name)
                        model_comparisons[model_name_opset]["skipped"].append(current_pass)
                        should_compare = False
                    elif not conversion_failed:
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
                else:
                    try:
                        if "relax_conversion_error" in model_data:
                            raise RuntimeError(model_data["relax_conversion_error"])
                        optimized_relax_model = opt_helper.apply_tvm_passes(
                            model_data["relax_model"],
                            tvm_passes,
                            target=runtime_config.get("target", "llvm"),
                        )
                        print("Running Relax model configuration: " + current_pass)
                        tvm_runner.compile_tvm_model(
                            optimized_relax_model,
                            target=runtime_config.get("target", "llvm"),
                        )
                        opt_model_out = {}
                        for image_path in images_paths:
                            image_name = os.path.basename(image_path)
                            outputs = tvm_runner.execute_tvm_model(
                                prepared_inputs[image_name]
                            )
                            opt_model_out[image_name] = onnx_runner.format_outputs(
                                outputs, include_certainties
                            )
                    except Exception as e:
                        if model_name_opset not in model_comparisons["conversion_errors"]:
                            model_comparisons["conversion_errors"][model_name_opset] = {}
                        model_comparisons["conversion_errors"][model_name_opset][current_pass] = repr(e)
                        model_comparisons[model_name_opset]["failed"].append(current_pass)
                        conversion_failed = True
                        if "relax_conversion_error" in model_data:
                            model_comparisons["failed_models"].append(model_name)

                if not conversion_failed and (should_compare or backend == "onnx"):
                        if ("classification" in tags):
                            evaluation = onnx_runner.evaluate(base_model_out, opt_model_out, type=tags, include_certainties=include_certainties)
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
                        if backend == "tvm":
                            model_comparisons[model_name_opset][current_pass][
                                "relax_passes"
                            ] = tvm_passes

                if backend == "tvm" or not conversion_failed:
                    json_object = json.dumps(model_comparisons, indent=2)

                    # TODO: Remove after debugging.
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
