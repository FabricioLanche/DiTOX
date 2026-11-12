import numpy as np

from src.metric_comparison.comparators.classification import ClassificationComparator
from src.metric_comparison.comparators.body import BodyComparator
from src.metric_comparison.comparators.ssd import SSDComparator
from src.metric_comparison.comparators.speech import SpeechComparator
from src.metric_comparison.comparators.text import TextComparator
from src.metric_comparison.comparators.yolov3 import YOLOV3Comparator
from src.metric_comparison.evaluators.object_detection import ObjectDetectionEvaluator
from src.metric_comparison.extractors.ssd_extractor import SSDExtractor
from src.metric_comparison.extractors.yolov2_extractor import YOLOV2Extractor
from src.metric_comparison.evaluators.comparator import (
    character_err_rate,
    percentage_corr_kekpoints,
    word_err_rate,
)


class ModelComparisonDispatcher:
    """Select and run metric comparison logic for each model family."""

    def dispatch(
        self,
        *,
        evaluation_runner,
        onnx_runner,
        tags,
        model_name_opset,
        current_pass,
        include_certainties,
        enable_kt_on_one_dim_tensor,
        model_comparisons,
        base_model_out,
        opt_model_out,
        model,
        text_runner=None,
    ):
        if "speech_recognition" in tags or "speech" in tags:
            paired_ids = [key for key in base_model_out if key in opt_model_out]
            if not paired_ids:
                raise ValueError("Speech outputs have no matching sample IDs.")
            base_wer_values, base_cer_values = [], []
            opt_wer_values, opt_cer_values = [], []
            for sample_id in paired_ids:
                base_text = base_model_out[sample_id]
                opt_text = opt_model_out[sample_id]
                if not isinstance(base_text, dict) or not isinstance(opt_text, dict):
                    raise TypeError("Speech task runners must return prediction/reference per sample.")
                reference = base_text.get("reference")
                if not isinstance(reference, str) or reference != opt_text.get("reference"):
                    raise ValueError(f"Speech reference is missing or inconsistent for {sample_id}.")
                base_wer_values.append(word_err_rate(reference, base_text["prediction"]))
                base_cer_values.append(character_err_rate(reference, base_text["prediction"]))
                opt_wer_values.append(word_err_rate(reference, opt_text["prediction"]))
                opt_cer_values.append(character_err_rate(reference, opt_text["prediction"]))
            evaluation = {
                "base_wer": float(np.mean(base_wer_values)),
                "base_cer": float(np.mean(base_cer_values)),
                "wer": float(np.mean(opt_wer_values)),
                "cer": float(np.mean(opt_cer_values)),
            }
            SpeechComparator(evaluation, model_comparisons).update(
                model_name_opset, current_pass
            )

        elif "body_recognition" in tags or "body" in tags:
            paired_ids = [key for key in base_model_out if key in opt_model_out]
            if not paired_ids:
                raise ValueError("Pose outputs have no matching sample IDs.")
            pck_values = []
            for sample_id in paired_ids:
                base_pose = base_model_out[sample_id]
                opt_pose = opt_model_out[sample_id]
                if not isinstance(base_pose, dict) or not isinstance(opt_pose, dict):
                    raise TypeError("Pose task runners must return predicted and reference keypoints per sample.")
                scale = float(base_pose.get("scale", 0))
                if not np.isclose(scale, float(opt_pose.get("scale", scale))):
                    raise ValueError(f"Pose scale differs for sample {sample_id}.")
                reference = np.asarray(base_pose["reference_keypoints"])
                if not np.array_equal(reference, np.asarray(opt_pose["reference_keypoints"])):
                    raise ValueError(f"Pose reference differs for sample {sample_id}.")
                base_pck = percentage_corr_kekpoints(
                    reference, base_pose["keypoints"], scale
                )
                opt_pck = percentage_corr_kekpoints(
                    reference, opt_pose["keypoints"], scale
                )
                pck_values.append(
                    {"base": base_pck, "optimized": opt_pck}
                )
            BodyComparator({
                "base_pck": float(np.mean([value["base"] for value in pck_values])),
                "pck": float(np.mean([value["optimized"] for value in pck_values])),
            }, model_comparisons).update(
                model_name_opset, current_pass
            )

        elif "text" in tags and text_runner is not None:
            evaluation = text_runner.evaluate(base_model_out, opt_model_out)
            comparator = TextComparator(evaluation, model_comparisons)
            comparator.update(model_name_opset, current_pass)

        elif ("classification" in tags):
            evaluation = evaluation_runner.evaluate(base_model_out, opt_model_out, type=tags, include_certainties=include_certainties)
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


