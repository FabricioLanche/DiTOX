import hashlib

from onnx import hub

from builders.tvm_builder import TVMBuilder
from helpers.model_helper import (
    get_model_path,
    prepare_model_input_dimension,
    prepare_model_shape,
)


class ModelOrchestrator:

    def __init__(
        self,
        general_config,
        hub_config,
        script_dir,
        different_models=None,
        check_prob_models=False,
        model_comparisons_file_exists=False,
        backend="onnx",
    ):
        self.general_config = general_config
        self.hub_config = hub_config
        self.script_dir = script_dir
        self.backend = backend
        self.builder = TVMBuilder() if backend == "tvm" else None
        self.different_models = different_models or []
        self.check_prob_models = check_prob_models
        self.model_comparisons_file_exists = model_comparisons_file_exists

        self.all_models = hub.list_models(tags=hub_config["tags"])
        cache_folder = hub_config["cache_folder_rel_path"]
        hub.set_dir(script_dir + "/" + cache_folder)

    def get_models(self):
        for model_no, model_obj in enumerate(self.all_models, start=1):
            if (
                model_no < self.general_config["skip_until_model_id"]
                or model_no > self.general_config["run_up_to_model_id"]
            ):
                continue

            model_name = model_obj.model
            model_opset = model_obj.opset
            model_name_opset = model_name + "-" + str(model_opset)
            tags = model_obj.tags

            name_filters = self.general_config["name_filters"]
            is_exact_match = self.general_config["match_filter_exact"]
            if len(name_filters) != 0:
                filter_in_name = False
                for name_filter in name_filters:
                    if name_filter in model_name_opset:
                        print(model_name_opset)
                    if is_exact_match and name_filter == model_name_opset:
                        filter_in_name = True
                        break
                    elif not is_exact_match and name_filter in model_name_opset:
                        filter_in_name = True
                        break

                if not filter_in_name:
                    continue

            if (
                self.check_prob_models
                and self.model_comparisons_file_exists
                and model_name_opset not in self.different_models
            ):
                continue

            if len(self.hub_config["tags_of_models_to_consider"]) != 0:
                tag_found = False
                for tag_to_consider in self.hub_config["tags_of_models_to_consider"]:
                    if tag_to_consider in tags:
                        tag_found = True
                        break

                if not tag_found:
                    continue

            if model_opset < self.hub_config["opset_bottom_threshold"]:
                continue

            print("Model Number: " + str(model_no))
            print("Model Name: " + model_name)
            print(model_obj)

            img_dimension = prepare_model_input_dimension(model_obj)
            keywords = [
                "tf", "keras", "torch", "tflite", "densenet", "resnet",
                "mobilenet", "inception", "shufflenet", "googlenet",
                "version-rfb",
            ]
            contains_keyword = any(
                keyword in model_name.lower() for keyword in keywords
            )

            first_input = model_obj.metadata["io_ports"]["inputs"][0]
            print(first_input["shape"])

            model_config = {
                "model_name": model_name + "_torch" if not contains_keyword else "",
                "input_name": first_input["name"],
                "input_shape": prepare_model_shape(model_obj),
                "input_dimension": img_dimension,
            }

            model_path = get_model_path(
                self.script_dir, model_obj, self.hub_config["cache_folder_rel_path"]
            )
            model = hub.load(model_name, opset=model_opset)
            with open(model_path, "rb") as model_file:
                original_hash = hashlib.md5(model_file.read()).hexdigest()

            model_data = {
                "model_no": model_no,
                "model_obj": model_obj,
                "model_name": model_name,
                "model_opset": model_opset,
                "model_name_opset": model_name_opset,
                "tags": tags,
                "model_config": model_config,
                "model_path": model_path,
                "model": model,
                "original_hash": original_hash,
                "opt_model_path": model_path.replace(".onnx", "_opt.onnx"),
            }

            if self.builder is not None:
                input_shape = model_config["input_shape"]
                shape_dict = None
                if input_shape and all(
                    isinstance(dimension, int) and dimension > 0
                    for dimension in input_shape
                ):
                    shape_dict = {model_config["input_name"]: tuple(input_shape)}

                try:
                    model_data["relax_model"] = self.builder.build_relax(
                        model, shape_dict=shape_dict
                    )
                except Exception as exc:
                    model_data["relax_conversion_error"] = repr(exc)
                    print(
                        f"ONNX-to-Relax conversion failed for {model_name_opset}: "
                        f"{exc}"
                    )

            yield model_data