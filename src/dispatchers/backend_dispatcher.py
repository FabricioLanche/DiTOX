import hashlib
import onnx
import numpy as np

from src.optimizer import ONNXOptimizer, TVMOptimizer
from src.runner.onnx_runner import ONNXRunner
from src.runner.tvm_runner import TVMRunner


def _has_dissimilarity(evaluation):
    values = np.asarray(evaluation.get("percentage_dissimilar", []), dtype=float)
    return bool(np.any(values[np.isfinite(values)] > 0))


class BackendDispatcher:
    """Select backend-specific components and execute baseline models."""

    def __init__(self, run_config):
        self.backend = run_config.backend
        self.onnx_runner = ONNXRunner({})
        self.tvm_optimizer = TVMOptimizer() if self.is_tvm else None
        self.onnx_optimizer = ONNXOptimizer()
        self.optimizer = self.tvm_optimizer if self.is_tvm else self.onnx_optimizer
        self.tvm_runner = TVMRunner(run_config.tvm) if self.is_tvm else None

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
    ):
        if "text" in tags:
            print("Text models not supported on this version.")
            return None

        if self.is_tvm:
            if tvm_build_error is not None:
                raise tvm_build_error
            output = self.tvm_runner.execute_tvm_executable(
                base_executable,
                images_paths,
                model_config,
                input_names=relax_input_names,
                include_certainties=include_certainties,
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
    ):
        conversion_failed = False
        opt_model_out = None
        if self.is_tvm:
            try:
                if current_pass == "all":
                    print("Running optimized TVM model. Pass: all")
                    optimized_pipeline = self.tvm_optimizer.get_optimized_pipeline()
                    optimized_executable = self.tvm_optimizer.generate_executable(
                        base_relax_mod,
                        optimized_pipeline,
                    )
                    opt_model_out = self.tvm_runner.execute_tvm_executable(
                        optimized_executable,
                        images_paths,
                        model_config,
                        input_names=relax_input_names,
                        include_certainties=include_certainties,
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
                            dependency_executable = self.tvm_optimizer.generate_executable(
                                base_relax_mod,
                                dependency_pipeline,
                            )
                            dependency_out = self.tvm_runner.execute_tvm_executable(
                                dependency_executable,
                                images_paths,
                                model_config,
                                input_names=relax_input_names,
                                include_certainties=include_certainties,
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
                        candidate_executable = self.tvm_optimizer.generate_executable(
                            base_relax_mod,
                            candidate_pipeline,
                        )
                        opt_model_out = self.tvm_runner.execute_tvm_executable(
                            candidate_executable,
                            images_paths,
                            model_config,
                            input_names=relax_input_names,
                            include_certainties=include_certainties,
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

                    if "text" not in tags:
                        opt_model_out = self.onnx_runner.execute_onnx_model(onnx_model, images_paths, config=model_config, include_certainties=include_certainties)

                except Exception as e:
                    if model_name_opset not in model_comparisons["conversion_errors"]:
                        model_comparisons["conversion_errors"][model_name_opset] = {}
                    model_comparisons["conversion_errors"][model_name_opset][current_pass] = repr(e)
                    model_comparisons[model_name_opset]["failed"].append(current_pass)
                    conversion_failed = True


        return opt_model_out, conversion_failed, current_pass

