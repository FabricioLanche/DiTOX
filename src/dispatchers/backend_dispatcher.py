import hashlib
from contextlib import nullcontext
from pathlib import Path

import onnx
import numpy as np

from src.optimizer import ONNXOptimizer, TVMOptimizer
from src.runner.onnx_runner import ONNXRunner
from src.runner.text_runner import TextRunner
from src.runner.tvm_runner import TVMRunner


def _has_dissimilarity(evaluation):
    values = np.asarray(evaluation.get("percentage_dissimilar", []), dtype=float)
    return bool(np.any(values[np.isfinite(values)] > 0))


class BackendDispatcher:
    """Select backend-specific components and execute baseline models."""

    def __init__(self, run_config, pipeline_trace=None):
        self.backend = run_config.backend
        self.pipeline_trace = pipeline_trace
        self.onnx_runner = ONNXRunner({})
        self.text_runner = TextRunner(run_config.text)
        self.tvm_optimizer = TVMOptimizer() if self.is_tvm else None
        self.onnx_optimizer = ONNXOptimizer()
        self.optimizer = self.tvm_optimizer if self.is_tvm else self.onnx_optimizer
        self.tvm_runner = TVMRunner(run_config.tvm) if self.is_tvm else None

    def _stage(self, name, **context):
        if self.pipeline_trace is None:
            return nullcontext()
        return self.pipeline_trace.stage(name, **context)

    @property
    def is_tvm(self):
        return self.backend == "tvmr"

    @property
    def evaluation_runner(self):
        return self.tvm_runner if self.is_tvm else self.onnx_runner

    def passes_to_run(self, passes, run_individual_passes):
        if self.is_tvm:
            return passes if run_individual_passes else (["all"] if passes else [])
        return passes if run_individual_passes else ["all"]

    def run_baseline(
        self,
        model,
        tags,
        images_paths,
        model_config,
        include_certainties,
        base_executable=None,
        relax_input_names=None,
        tvm_build_error=None,
        prepared_image_inputs=None,
        text_prompts=None,
        prepared_task_inputs=None,
        task_samples=None,
    ):
        if prepared_task_inputs is not None:
            if "speech_recognition" in tags and "whisper" in model_config["model_name"].lower():
                if self.is_tvm:
                    raise RuntimeError(
                        "Whisper encoder-decoder models currently require the ORT backend; "
                        "the TVM path in this project compiles a single ONNX graph."
                    )
                return self._run_whisper(
                    model_config, prepared_task_inputs, task_samples
                )
            raw_outputs = self._execute_task_inputs(
                model,
                prepared_task_inputs,
                tags,
                model_config,
                base_executable=base_executable,
                relax_input_names=relax_input_names,
                tvm_build_error=tvm_build_error,
            )
            return self._decode_task_outputs(
                raw_outputs, tags, model_config, task_samples
            )

        if "text" in tags:
            return self.text_runner.execute_text_model(model, text_prompts or [])

        if self.is_tvm:
            if tvm_build_error is not None:
                raise tvm_build_error
            output = self.tvm_runner.execute_tvm_executable(
                base_executable,
                images_paths,
                model_config,
                input_names=relax_input_names,
                include_certainties=include_certainties,
                prepared_image_inputs=prepared_image_inputs,
            )
            return output

        output = self.onnx_runner.execute_onnx_model(
            model,
            images_paths,
            config=model_config,
            include_certainties=include_certainties,
        )
        return output
    def run_optimization_pass(
        self,
        current_pass,
        *,
        base_relax_mod,
        base_model_out,
        tags,
        images_paths,
        model_config,
        include_certainties,
        model_path,
        opt_model_path,
        original_hash,
        model_name,
        model_name_opset,
        model_comparisons,
        enable_kt_on_one_dim_tensor,
        relax_input_names=None,
        prepared_image_inputs=None,
        text_prompts=None,
        prepared_task_inputs=None,
        task_samples=None,
    ):
        conversion_failed = False
        opt_model_out = None
        if self.is_tvm and prepared_task_inputs is not None:
            try:
                if current_pass == "all":
                    pipeline = self.tvm_optimizer.get_optimized_pipeline()
                else:
                    dependencies = self.tvm_optimizer.get_isolation_dependencies(
                        current_pass
                    )
                    pipeline = self.tvm_optimizer.get_isolation_pipeline(
                        current_pass,
                        dependencies=dependencies,
                        include_optimization=True,
                    )
                executable = self.tvm_optimizer.generate_executable(
                    base_relax_mod, pipeline
                )
                raw_outputs = self.tvm_runner.execute_tvm_inputs(
                    executable, relax_input_names, prepared_task_inputs
                )
                opt_model_out = self._decode_task_outputs(
                    raw_outputs, tags, model_config, task_samples
                )
            except Exception as error:
                conversion_failed = True
                model_comparisons.setdefault("conversion_errors", {}).setdefault(
                    model_name_opset, {}
                )[current_pass] = repr(error)
                model_comparisons[model_name_opset].setdefault("failed", []).append(
                    current_pass
                )
                model_comparisons["failed_conversions_no"] += 1
        elif self.is_tvm and "text" not in tags:
            try:
                if current_pass == "all":
                    print("Running optimized TVM model. Pass: all")
                    optimized_pipeline = self.tvm_optimizer.get_optimized_pipeline()
                    with self._stage(
                        "tvm.optimized_compile",
                        model=model_name_opset,
                        pass_name=current_pass,
                    ):
                        optimized_executable = self.tvm_optimizer.generate_executable(
                            base_relax_mod,
                            optimized_pipeline,
                        )
                    with self._stage(
                        "tvm.optimized_run",
                        model=model_name_opset,
                        pass_name=current_pass,
                    ):
                        opt_model_out = self.tvm_runner.execute_tvm_executable(
                            optimized_executable,
                            images_paths,
                            model_config,
                            input_names=relax_input_names,
                            include_certainties=include_certainties,
                            prepared_image_inputs=prepared_image_inputs,
                        )
                else:
                    required_dependencies = self.tvm_optimizer.get_isolation_dependencies(
                        current_pass
                    )
                    included_dependencies = []
                    dependency_failure = None
                    dependency_checks = []

                    for dependency in required_dependencies:
                        included_dependencies.append(dependency)
                        dependency_pipeline = self.tvm_optimizer.get_isolation_pipeline(
                            current_pass,
                            dependencies=included_dependencies,
                            include_optimization=False,
                        )
                        try:
                            dependency_context = {
                                "model": model_name_opset,
                                "pass_name": current_pass,
                                "dependency": dependency,
                            }
                            with self._stage(
                                "tvm.dependency_compile", **dependency_context
                            ):
                                dependency_executable = self.tvm_optimizer.generate_executable(
                                    base_relax_mod,
                                    dependency_pipeline,
                                )
                            with self._stage(
                                "tvm.dependency_run", **dependency_context
                            ):
                                dependency_out = self.tvm_runner.execute_tvm_executable(
                                    dependency_executable,
                                    images_paths,
                                    model_config,
                                    input_names=relax_input_names,
                                    include_certainties=include_certainties,
                                    prepared_image_inputs=prepared_image_inputs,
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

                        with self._stage(
                            "tvm.dependency_compare", **dependency_context
                        ):
                            dependency_evaluation = self.tvm_runner.evaluate(
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
                        candidate_pipeline = self.tvm_optimizer.get_isolation_pipeline(
                            current_pass,
                            dependencies=required_dependencies,
                            include_optimization=True,
                        )
                        candidate_context = {
                            "model": model_name_opset,
                            "pass_name": current_pass,
                        }
                        with self._stage(
                            "tvm.candidate_compile", **candidate_context
                        ):
                            candidate_executable = self.tvm_optimizer.generate_executable(
                                base_relax_mod,
                                candidate_pipeline,
                            )
                        with self._stage(
                            "tvm.candidate_run", **candidate_context
                        ):
                            opt_model_out = self.tvm_runner.execute_tvm_executable(
                                candidate_executable,
                                images_paths,
                                model_config,
                                input_names=relax_input_names,
                                include_certainties=include_certainties,
                                prepared_image_inputs=prepared_image_inputs,
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
            with self._stage(
                "onnx.optimization",
                model=model_name_opset,
                pass_name=current_pass,
            ):
                result = self.onnx_optimizer.optimize_model(
                    model_path,
                    opt_model_path,
                    optimization=current_pass,
                )
            if result.returncode != 0:
                print(result.stdout)
                if model_name_opset not in model_comparisons["conversion_errors"]:
                    model_comparisons["conversion_errors"][model_name_opset] = {}
                model_comparisons["conversion_errors"][model_name_opset][current_pass] = repr(result.stdout)
                model_comparisons["failed_conversions_no"] += 1
                conversion_failed = True

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

                    with self._stage(
                        "onnx.optimized_run",
                        model=model_name_opset,
                        pass_name=current_pass,
                    ):
                        if prepared_task_inputs is not None:
                            if "speech_recognition" in tags and "whisper" in model_config["model_name"].lower():
                                opt_model_out = self._run_whisper(
                                    model_config,
                                    prepared_task_inputs,
                                    task_samples,
                                    encoder_override=opt_model_path,
                                )
                            else:
                                raw_outputs = self.onnx_runner.execute_onnx_inputs(
                                    onnx_model, prepared_task_inputs
                                )
                                opt_model_out = self._decode_task_outputs(
                                    raw_outputs, tags, model_config, task_samples
                                )
                        elif "text" in tags:
                            opt_model_out = self.text_runner.execute_text_model(
                                onnx_model, text_prompts or []
                            )
                        else:
                            opt_model_out = self.onnx_runner.execute_onnx_model(onnx_model, images_paths, config=model_config, include_certainties=include_certainties)

                except Exception as e:
                    if model_name_opset not in model_comparisons["conversion_errors"]:
                        model_comparisons["conversion_errors"][model_name_opset] = {}
                    model_comparisons["conversion_errors"][model_name_opset][current_pass] = repr(e)
                    model_comparisons[model_name_opset]["failed"].append(current_pass)
                    conversion_failed = True


        return opt_model_out, conversion_failed, current_pass

    def _execute_task_inputs(
        self,
        model,
        prepared_inputs,
        tags,
        model_config,
        *,
        base_executable=None,
        relax_input_names=None,
        tvm_build_error=None,
    ):
        if self.is_tvm:
            if tvm_build_error is not None:
                raise tvm_build_error
            raw_outputs = self.tvm_runner.execute_tvm_inputs(
                base_executable, relax_input_names, prepared_inputs
            )
        else:
            raw_outputs = self.onnx_runner.execute_onnx_inputs(model, prepared_inputs)
        return raw_outputs

    @staticmethod
    def _decode_task_outputs(raw_outputs, tags, model_config, task_samples):
        samples_by_id = {str(sample["id"]): sample for sample in task_samples}
        decoded = {}
        model_name = model_config["model_name"]
        if "body_recognition" in tags:
            for sample_id, values in raw_outputs.items():
                sample = samples_by_id[str(sample_id)]
                points = BackendDispatcher._decode_pose(values, model_name)
                transform = sample["pose_transform"]
                if np.nanmax(np.abs(points[:, :2])) <= 1.5:
                    points[:, 0] *= transform["input_width"]
                    points[:, 1] *= transform["input_height"]
                points[:, 0] = (
                    points[:, 0] * transform["width"] / transform["input_width"]
                    + transform["left"]
                )
                points[:, 1] = (
                    points[:, 1] * transform["height"] / transform["input_height"]
                    + transform["top"]
                )
                decoded[str(sample_id)] = {
                    "keypoints": points,
                    "reference_keypoints": sample["reference_keypoints"],
                    "scale": sample["scale"],
                }
            return decoded

        for sample_id, values in raw_outputs.items():
            sample = samples_by_id[str(sample_id)]
            prediction = BackendDispatcher._decode_transcription(
                values, model_name, model_config["model_dir"]
            )
            decoded[str(sample_id)] = {
                "prediction": prediction,
                "reference": sample["reference"],
            }
        return decoded

    @staticmethod
    def _decode_pose(outputs, model_name):
        arrays = [np.asarray(value) for value in outputs]
        lower_name = model_name.lower()
        if "movenet" in lower_name:
            points = next(array for array in arrays if array.size >= 17 * 3).reshape(-1, 3)[-17:]
            return points[:, [1, 0, 2]].astype(np.float32)
        if "yolov8" in lower_name:
            output = max(arrays, key=lambda array: array.size)
            output = np.squeeze(output)
            if output.ndim == 2 and output.shape[0] < output.shape[1]:
                output = output.T
            candidates = output
            if candidates.ndim != 2 or candidates.shape[1] < 56:
                raise ValueError(f"Unexpected YOLOv8-Pose output shape: {output.shape}.")
            best = candidates[int(np.argmax(candidates[:, 4]))]
            return best[5:56].reshape(17, 3).astype(np.float32)
        if "rtmpose" in lower_name:
            heads = [np.squeeze(array) for array in arrays]
            heads = [head for head in heads if head.ndim == 2 and head.shape[0] == 17]
            if len(heads) >= 2:
                x_head, y_head = sorted(heads, key=lambda value: value.shape[1])[:2]
                x_indices = np.argmax(x_head, axis=1)
                y_indices = np.argmax(y_head, axis=1)
                scores = np.minimum(
                    np.max(x_head, axis=1), np.max(y_head, axis=1)
                )
                return np.column_stack((x_indices / 2, y_indices / 2, scores)).astype(np.float32)
        if "mediapipe" in lower_name:
            indices = [0, 2, 5, 7, 8, 11, 12, 13, 14, 15, 16, 23, 24, 25, 26, 27, 28]
            candidates = []
            for array in arrays:
                squeezed = np.squeeze(array)
                if squeezed.size == 39 * 5:
                    candidates.append(squeezed.reshape(39, 5))
                elif squeezed.ndim >= 2 and squeezed.shape[-1] == 5:
                    candidates.append(squeezed.reshape(-1, 5))
            if candidates:
                landmarks = max(candidates, key=lambda array: array.size)
                if landmarks.shape[0] > max(indices):
                    return landmarks[indices, :3].astype(np.float32)
        raise ValueError(f"No pose output adapter matches {model_name}.")

    @staticmethod
    def _decode_transcription(outputs, model_name, model_dir):
        lower_name = model_name.lower()
        if "whisper" in lower_name:
            raise RuntimeError(
                "Whisper requires encoder-decoder generation. Configure the ONNX Runtime "
                "speech-seq2seq backend; a single encoder graph cannot produce WER/CER."
            )
        logits = np.asarray(outputs[0])
        token_ids = np.argmax(logits, axis=-1).reshape(-1).tolist()
        if "citrinet" in lower_name:
            token_file = Path(model_dir) / "tokens.txt"
            if not token_file.is_file():
                raise FileNotFoundError(token_file)
            vocabulary = {}
            with token_file.open("r", encoding="utf-8") as stream:
                for line in stream:
                    parts = line.strip().split(maxsplit=1)
                    if len(parts) == 2:
                        vocabulary[int(parts[0])] = parts[1]
            vocabulary_size = max(vocabulary, default=-1) + 1
            if logits.ndim == 3 and logits.shape[1] == vocabulary_size:
                token_ids = np.argmax(logits, axis=1).reshape(-1).tolist()
            blank = next((index for index, token in vocabulary.items() if token in ("<blk>", "<blank>")), 0)
            collapsed, previous = [], None
            for index in token_ids:
                if index != previous and index != blank:
                    collapsed.append(vocabulary.get(index, ""))
                previous = index
            return "".join(collapsed).replace("▁", " ").strip()
        from transformers import AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(model_dir)
        return tokenizer.batch_decode([token_ids], skip_special_tokens=True)[0].strip()

    @staticmethod
    def _run_whisper(model_config, prepared_inputs, samples, encoder_override=None):
        import os
        import shutil
        import tempfile

        import torch
        from optimum.onnxruntime import ORTModelForSpeechSeq2Seq
        from transformers import AutoProcessor

        model_dir = Path(model_config["model_dir"])
        model_root = model_dir
        temporary_root = None
        if encoder_override is not None:
            temporary_root = tempfile.TemporaryDirectory(prefix="ditox-whisper-")
            model_root = Path(temporary_root.name) / "model"

            def link_or_copy(source, destination):
                try:
                    os.link(source, destination)
                except OSError:
                    shutil.copy2(source, destination)

            shutil.copytree(model_dir, model_root, copy_function=link_or_copy)
            relative_encoder = Path(model_config["primary_model_path"]).relative_to(model_dir)
            target_encoder = model_root / relative_encoder
            target_encoder.unlink(missing_ok=True)
            shutil.copy2(encoder_override, target_encoder)

        try:
            processor = AutoProcessor.from_pretrained(str(model_dir))
            model = ORTModelForSpeechSeq2Seq.from_pretrained(
                str(model_root), subfolder="onnx"
            )
            decoded = {}
            for sample in samples:
                sample_id = str(sample["id"])
                features = next(iter(prepared_inputs[sample_id].values()))
                generated = model.generate(
                    input_features=torch.from_numpy(np.asarray(features))
                )
                prediction = processor.tokenizer.batch_decode(
                    generated, skip_special_tokens=True
                )[0].strip()
                decoded[sample_id] = {
                    "prediction": prediction,
                    "reference": sample["reference"],
                }
            return decoded
        finally:
            if temporary_root is not None:
                temporary_root.cleanup()

