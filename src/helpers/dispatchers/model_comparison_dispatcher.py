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
            different_samples = 0
            different_words = 0
            total_words = 0
            substitutions = insertions = deletions = 0
            cer_values = []
            for sample_id in paired_ids:
                base_text = base_model_out[sample_id]
                opt_text = opt_model_out[sample_id]
                if not isinstance(base_text, dict) or not isinstance(opt_text, dict):
                    raise TypeError("Speech task runners must return prediction/reference per sample.")
                reference = base_text.get("reference")
                if not isinstance(reference, str) or reference != opt_text.get("reference"):
                    raise ValueError(f"Speech reference is missing or inconsistent for {sample_id}.")
                base_prediction = base_text["prediction"]
                optimized_prediction = opt_text["prediction"]
                cer_values.append(character_err_rate(base_prediction, optimized_prediction))
                different_samples += int(base_prediction != optimized_prediction)
                different_words += word_err_rate(base_prediction, optimized_prediction) * max(
                    len(base_prediction.split()), 1
                )
                total_words += len(base_prediction.split())
                left, right = base_prediction.split(), optimized_prediction.split()
                costs = [[(0, 0, 0, 0) for _ in range(len(right) + 1)] for _ in range(len(left) + 1)]
                for i in range(1, len(left) + 1): costs[i][0] = (i, 0, 0, i)
                for j in range(1, len(right) + 1): costs[0][j] = (j, 0, j, 0)
                for i in range(1, len(left) + 1):
                    for j in range(1, len(right) + 1):
                        if left[i-1] == right[j-1]: costs[i][j] = costs[i-1][j-1]
                        else:
                            candidates = [
                                (costs[i-1][j-1][0]+1, costs[i-1][j-1][1]+1, costs[i-1][j-1][2], costs[i-1][j-1][3]),
                                (costs[i][j-1][0]+1, costs[i][j-1][1], costs[i][j-1][2]+1, costs[i][j-1][3]),
                                (costs[i-1][j][0]+1, costs[i-1][j][1], costs[i-1][j][2], costs[i-1][j][3]+1),
                            ]
                            costs[i][j] = min(candidates, key=lambda item: item[0])
                _, sub, ins, dele = costs[-1][-1]
                substitutions += sub; insertions += ins; deletions += dele
            evaluation = {
                "different_samples": different_samples,
                "different_words": int(round(different_words)),
                "total_words": total_words,
                "total_samples": len(paired_ids),
                "change_rate": 100.0 * different_samples / len(paired_ids),
                "wer": float(different_words / total_words) if total_words else 0.0,
                "cer": float(np.mean(cer_values)) if cer_values else 0.0,
                "substitutions": substitutions, "insertions": insertions, "deletions": deletions,
            }
            SpeechComparator(evaluation, model_comparisons).update(
                model_name_opset, current_pass
            )

        elif "body_recognition" in tags or "body" in tags:
            paired_ids = [key for key in base_model_out if key in opt_model_out]
            if not paired_ids:
                raise ValueError("Pose outputs have no matching sample IDs.")
            different_samples = 0
            different_keypoints = 0
            total_keypoints = 0
            oks_values = []; pck_values = []; displacements = []
            coco_sigmas = np.array([.26,.25,.25,.35,.35,.79,.79,.72,.72,.62,.62,1.07,1.07,.87,.87,.89,.89]) / 10
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
                base_keypoints = np.asarray(base_pose["keypoints"], dtype=np.float64)
                opt_keypoints = np.asarray(opt_pose["keypoints"], dtype=np.float64)
                if base_keypoints.shape != opt_keypoints.shape:
                    raise ValueError(
                        f"Pose keypoint shapes differ for sample {sample_id}: "
                        f"{base_keypoints.shape} vs {opt_keypoints.shape}."
                    )
                point_equal = np.isclose(
                    base_keypoints, opt_keypoints, rtol=1e-5, atol=1e-5,
                    equal_nan=True,
                )
                changed_points = ~np.all(point_equal, axis=1)
                different_samples += int(np.any(changed_points))
                different_keypoints += int(np.count_nonzero(changed_points))
                total_keypoints += int(base_keypoints.shape[0])
                valid = np.isfinite(base_keypoints[:,:2]).all(axis=1) & np.isfinite(opt_keypoints[:,:2]).all(axis=1)
                d = np.linalg.norm(base_keypoints[:,:2]-opt_keypoints[:,:2],axis=1)
                scale=max(scale,1e-6); sigmas=coco_sigmas[:len(d)]
                oks_values.append(float(np.mean(np.exp(-(d[valid]**2)/(2*(scale*sigmas[valid])**2)))) if np.any(valid) else 1.0)
                pck_values.extend((d[valid] <= .2*scale).tolist())
                displacements.extend((d[valid]/scale).tolist())
            BodyComparator({
                "different_samples": different_samples,
                "different_keypoints": different_keypoints,
                "total_keypoints": total_keypoints,
                "total_samples": len(paired_ids),
                "change_rate": 100.0*different_samples/len(paired_ids),
                "oks": float(np.mean(oks_values)),
                "pck": 100.0*float(np.mean(pck_values)) if pck_values else 100.0,
                "mean_normalized_displacement": float(np.mean(displacements)) if displacements else 0.0,
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
            total = len(base_model_out)
            changed = len(evaluation.get("dissimilar", []))
            model_comparisons[model_name_opset][current_pass]["output_change"] = {
                "changed_samples": changed, "total_samples": total,
                "change_rate": 100.0 * changed / total if total else 0.0,
            }

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

            # Keep tensor-ranking differences separate from decoded box metrics.
            raw_family_metrics = model_comparisons[model_name_opset][current_pass]
            tensor_rank = {}
            boxes = {}
            for output_name, metrics in raw_family_metrics.items():
                if not isinstance(metrics, dict):
                    continue
                if any(key in metrics for key in ("first", "top5", "topK")):
                    tensor_rank[output_name] = metrics
                elif any(key.startswith("metrics_") for key in metrics):
                    boxes[output_name] = metrics
            dissimilar = evaluation.get("dissimilar", [])
            changed_ids = set()
            for values in dissimilar:
                if isinstance(values, (list, tuple, set)):
                    changed_ids.update(values)
            total = len(base_model_out)
            model_comparisons[model_name_opset][current_pass] = {
                "output_change": {
                    "changed_samples": len(changed_ids),
                    "total_samples": total,
                    "change_rate": 100.0 * len(changed_ids) / total if total else 0.0,
                },
                "family_metrics": {"detection": {
                    "tensor_rank": tensor_rank,
                    "boxes": boxes,
                }},
            }
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


