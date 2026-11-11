import hashlib
import json
from pathlib import Path

from onnx import hub


class ModelOrchestrator:
    """Discovers, filters, loads, and describes models for a run."""

    PREPROCESSING_KEYWORDS = (
        "tf",
        "keras",
        "torch",
        "tflite",
        "densenet",
        "resnet",
        "mobilenet",
        "inception",
        "shufflenet",
        "googlenet",
        "version-rfb",
    )

    def __init__(
        self,
        general_config,
        hub_config,
        script_dir,
        check_prob_models=False,
    ):
        self.general_config = general_config
        self.hub_config = hub_config
        self.script_dir = Path(script_dir)
        self.check_prob_models = check_prob_models

        self.manifest_categories = None
        self.manifest_missing_models = []
        self.manifest_excluded_by_config = []

        cache_dir = self.script_dir / hub_config["cache_folder_rel_path"]
        hub.set_dir(str(cache_dir))
        self.all_models = self._discover_models()

    def _discover_models(self):
        manifest_rel_path = self.hub_config.get("model_manifest_rel_path")
        if not manifest_rel_path:
            return hub.list_models(tags=self.hub_config["tags"])

        manifest_path = self.script_dir / manifest_rel_path.lstrip("/\\")
        with manifest_path.open("r", encoding="utf-8") as manifest_stream:
            manifest = json.load(manifest_stream)

        self.manifest_categories = {
            (item["model"], int(item["opset"])): item["category"]
            for item in manifest["models"]
        }
        included_categories = set(
            self.hub_config.get("tags_of_models_to_consider", [])
        )
        excluded_names = set(self.general_config.get("exclude_name_filters", []))
        self.manifest_excluded_by_config = [
            f"{model_name}-{opset}"
            for (model_name, opset), category in self.manifest_categories.items()
            if category not in included_categories
            or f"{model_name}-{opset}" in excluded_names
            or opset < self.hub_config["opset_bottom_threshold"]
        ]

        catalog = hub.list_models()
        catalog_by_id = {
            (item.model, int(item.opset)): item
            for item in catalog
        }
        self.manifest_missing_models = [
            f"{model_name}-{opset}"
            for model_name, opset in self.manifest_categories
            if (model_name, opset) not in catalog_by_id
        ]
        if self.manifest_missing_models:
            print(
                "Manifest models absent from current ONNX Hub catalog: "
                + ", ".join(self.manifest_missing_models)
            )

        return [
            catalog_by_id[model_id]
            for model_id in self.manifest_categories
            if model_id in catalog_by_id
        ]

    def get_models(self, problematic_models=None):
        """Yield selected models with their loaded model and runtime metadata."""
        problematic_models = set(problematic_models or [])
        name_filters = self.general_config["name_filters"]
        exact_match = self.general_config["match_filter_exact"]
        selected_tags = self.hub_config["tags_of_models_to_consider"]
        excluded_names = set(self.general_config.get("exclude_name_filters", []))

        for model_no, model_obj in enumerate(self.all_models, start=1):
            if (
                model_no < self.general_config["skip_until_model_id"]
                or model_no > self.general_config["run_up_to_model_id"]
            ):
                continue

            model_name = model_obj.model
            model_opset = int(model_obj.opset)
            model_name_opset = f"{model_name}-{model_opset}"

            if self.check_prob_models and model_name_opset not in problematic_models:
                continue
            if model_name_opset in excluded_names:
                continue
            if self.manifest_categories is not None:
                category = self.manifest_categories[(model_name, model_opset)]
                tags = [category]
                if category != "text":
                    tags.append("vision")
            else:
                tags = model_obj.tags

            if name_filters:
                matches_name = any(
                    model_name_opset == name_filter
                    if exact_match
                    else name_filter in model_name_opset
                    for name_filter in name_filters
                )
                if not matches_name:
                    continue

            if selected_tags and not any(tag in tags for tag in selected_tags):
                continue
            if model_opset < self.hub_config["opset_bottom_threshold"]:
                continue

            first_input = model_obj.metadata["io_ports"]["inputs"][0]
            model_shape = self.prepare_model_shape(model_obj)
            img_dimension = self.prepare_model_input_dimension(model_obj)
            model_name_lower = model_name.lower()
            has_known_preprocessor = any(
                keyword in model_name_lower
                for keyword in self.PREPROCESSING_KEYWORDS
            )
            model_config = {
                "model_name": model_name + "_torch" if not has_known_preprocessor else "",
                "input_name": first_input["name"],
                "input_shape": model_shape,
                "input_dimension": img_dimension,
            }

            model_path = self.get_model_path(
                model_obj,
                self.hub_config["cache_folder_rel_path"],
            )
            model = hub.load(model_name, opset=model_opset)
            with open(model_path, "rb") as model_file:
                original_hash = hashlib.md5(model_file.read()).hexdigest()

            print("Model Number: " + str(model_no))
            print("Model Name: " + model_name)
            print(model_obj)
            print(first_input["shape"])

            yield {
                "model_no": model_no,
                "model_obj": model_obj,
                "model_name": model_name,
                "model_opset": model_opset,
                "model_name_opset": model_name_opset,
                "tags": tags,
                "first_input": first_input,
                "model_shape": model_shape,
                "model_config": model_config,
                "model_path": model_path,
                "model": model,
                "original_hash": original_hash,
                "opt_model_path": model_path.replace(".onnx", "_opt.onnx"),
            }

    def get_model_path(self, model_obj, cache_folder_rel_path):
        model_path = model_obj.model_path
        model_sha = model_obj.metadata["model_sha"]
        for segment in ("/model/", "/models/", "/preproc/"):
            model_path = model_path.replace(segment, f"{segment}{model_sha}_")
        return str(self.script_dir / cache_folder_rel_path / model_path.lstrip("/"))

    @staticmethod
    def prepare_model_shape(model_obj):
        model_name = model_obj.model
        model_shape = [1, 1, 64, 64]
        if "io_ports" in model_obj.metadata:
            model_shape = model_obj.metadata["io_ports"]["inputs"][0]["shape"]
        if "R-CNN" in model_name or "FCN" in model_name or "YOLOv3" in model_name:
            model_shape = [1, 3, 224, 224]
        return model_shape

    @classmethod
    def prepare_model_input_dimension(cls, model_obj):
        model_shape = cls.prepare_model_shape(model_obj).copy()
        if model_shape:
            model_shape.pop(0)

        return [
            dimension
            for dimension in model_shape
            if not isinstance(dimension, str) and dimension > 5
        ]
