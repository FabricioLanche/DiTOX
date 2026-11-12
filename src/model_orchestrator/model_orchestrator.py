import hashlib
import json
import os
import tempfile
from contextlib import nullcontext
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import onnx
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
        tvm_builder=None,
        pipeline_trace=None,
    ):
        self.general_config = general_config
        self.hub_config = hub_config
        self.script_dir = Path(script_dir)
        self.check_prob_models = check_prob_models
        self.tvm_builder = tvm_builder
        self.pipeline_trace = pipeline_trace

        self.manifest_categories = None
        self.manifest_source_keys = {}
        self.manifest_missing_models = []
        self.manifest_excluded_by_config = []

        cache_dir = self.script_dir / hub_config["cache_folder_rel_path"]
        hub.set_dir(str(cache_dir))
        self.external_model_paths = self._download_configured_external_models(
            cache_dir
        )
        self.external_model_specs = self._load_external_model_specs()
        self.all_models = self._discover_models()

    def _load_external_model_specs(self):
        manifest_rel_path = self.hub_config.get(
            "external_model_manifest_rel_path",
            "configs/models/external_models.json",
        )
        manifest_path = self.script_dir / manifest_rel_path.lstrip("/\\")
        if not manifest_path.is_file():
            return {}
        with manifest_path.open("r", encoding="utf-8") as stream:
            return json.load(stream).get("models", {})

    def _download_configured_external_models(self, cache_dir):
        """Fetch configured Hugging Face artifacts alongside ONNX Hub models."""
        requested_models = self.hub_config.get("external_model_names", [])
        if not requested_models:
            return {}
        if not isinstance(requested_models, list) or not all(
            isinstance(name, str) for name in requested_models
        ):
            raise ValueError("hub.external_model_names must be a list of strings.")

        manifest_rel_path = self.hub_config.get(
            "external_model_manifest_rel_path",
            "configs/models/external_models.json",
        )
        manifest_path = self.script_dir / manifest_rel_path.lstrip("/\\")
        with manifest_path.open("r", encoding="utf-8") as manifest_file:
            model_specs = json.load(manifest_file).get("models", {})

        if "all" in requested_models:
            if len(requested_models) != 1:
                raise ValueError(
                    "hub.external_model_names cannot combine 'all' with model names."
                )
            selected_names = list(model_specs)
        else:
            selected_names = list(dict.fromkeys(requested_models))
        unknown_models = [name for name in selected_names if name not in model_specs]
        if unknown_models:
            raise ValueError(
                "Unknown external model(s) in hub.external_model_names: "
                + ", ".join(unknown_models)
            )

        try:
            from huggingface_hub import HfApi, hf_hub_download
        except ImportError as error:
            raise RuntimeError(
                "External model downloads require huggingface-hub. "
                "Install it with: pip install -r requirements.txt"
            ) from error

        output_root = cache_dir / "external"
        force_download = self.hub_config.get(
            "external_model_force_download", False
        )
        api = HfApi()
        resolved_revisions = {}
        downloaded_models = {}

        for model_name in selected_names:
            spec = model_specs[model_name]
            model_dir = output_root / model_name
            model_dir.mkdir(parents=True, exist_ok=True)
            artifacts = []
            for artifact in spec["artifacts"]:
                repo_id = artifact["repo_id"]
                requested_revision = artifact.get("revision", "main")
                revision_key = (repo_id, requested_revision)
                if revision_key not in resolved_revisions:
                    resolved_revisions[revision_key] = api.model_info(
                        repo_id, revision=requested_revision
                    ).sha
                resolved_revision = resolved_revisions[revision_key]
                local_path = hf_hub_download(
                    repo_id=repo_id,
                    filename=artifact["filename"],
                    revision=resolved_revision,
                    local_dir=str(model_dir),
                    force_download=force_download,
                )
                artifacts.append(
                    {
                        "repo_id": repo_id,
                        "revision": resolved_revision,
                        "filename": artifact["filename"],
                        "size_bytes": Path(local_path).stat().st_size,
                    }
                )
                print(
                    f"Downloaded {model_name}: {repo_id}@"
                    f"{resolved_revision[:8]}/{artifact['filename']}"
                )

            provenance = {
                "model": model_name,
                "task": spec["task"],
                "downloaded_at": datetime.now(timezone.utc).isoformat(
                    timespec="seconds"
                ),
                "artifacts": artifacts,
            }
            self._atomic_json_save(model_dir / "_source.json", provenance)
            downloaded_models[model_name] = model_dir

        return downloaded_models

    @staticmethod
    def _atomic_json_save(path, payload):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=path.parent,
                prefix=f".{path.name}-",
                suffix=".tmp",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
                json.dump(payload, temporary_file, indent=2)
                temporary_file.flush()
                os.fsync(temporary_file.fileno())
            os.replace(temporary_path, path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _discover_models(self):
        if self.hub_config.get("external_models_only", False):
            self.manifest_categories = {}
            self.manifest_source_keys = {}
            self.manifest_missing_models = []
            self.manifest_excluded_by_config = []
            return self._discover_external_models()

        manifest_rel_path = self.hub_config.get("model_manifest_rel_path")
        if not manifest_rel_path:
            return hub.list_models(tags=self.hub_config["tags"]) + self._discover_external_models()

        manifest_path = self.script_dir / manifest_rel_path.lstrip("/\\")
        with manifest_path.open("r", encoding="utf-8") as manifest_stream:
            manifest = json.load(manifest_stream)

        self.manifest_categories = {}
        self.manifest_source_keys = {}
        for item in manifest["models"]:
            model_id = (item["model"], int(item["opset"]))
            self.manifest_categories[model_id] = item["category"]
            self.manifest_source_keys[model_id] = item.get(
                "source_key", f"{item['model']}-{item['opset']}"
            )
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

        hub_models = [
            catalog_by_id[model_id]
            for model_id in self.manifest_categories
            if model_id in catalog_by_id
        ]
        return hub_models + self._discover_external_models()

    def _discover_external_models(self):
        """Expose downloaded task models through the normal model iteration."""
        selected_names = self.hub_config.get("external_model_names", [])
        discovered = []
        for model_name in selected_names:
            if model_name == "all":
                names = list(self.external_model_specs)
            else:
                names = [model_name]
            for name in names:
                model_dir = self.external_model_paths.get(name)
                if model_dir is None:
                    continue
                spec = self.external_model_specs[name]
                primary = spec.get("primary_artifact")
                if primary is None:
                    primary = next(
                        artifact["filename"]
                        for artifact in spec["artifacts"]
                        if artifact["filename"].endswith(".onnx")
                    )
                model_path = model_dir / primary
                if not model_path.is_file():
                    raise FileNotFoundError(
                        f"Primary ONNX artifact for {name} not found: {model_path}"
                    )
                model = onnx.load(str(model_path), load_external_data=False)
                opset = max(
                    (item.version for item in model.opset_import), default=17
                )
                inputs = []
                for graph_input in model.graph.input:
                    tensor_type = graph_input.type.tensor_type
                    shape = [
                        dimension.dim_value or dimension.dim_param
                        for dimension in tensor_type.shape.dim
                    ]
                    inputs.append({
                        "name": graph_input.name,
                        "shape": shape,
                        "dtype": onnx.TensorProto.DataType.Name(tensor_type.elem_type).lower(),
                    })
                metadata = {"io_ports": {"inputs": inputs}}
                discovered.append(SimpleNamespace(
                    model=name,
                    opset=opset,
                    tags=[spec["task"]],
                    metadata=metadata,
                    is_external=True,
                    external_spec=spec,
                    external_model_path=str(model_path),
                    external_model_dir=str(model_dir),
                ))
        return discovered

    def get_models(
        self,
        problematic_models=None,
        *,
        metadata_only=False,
        exclude_models=None,
    ):
        """Yield selected model metadata and, unless requested otherwise, artifacts."""
        problematic_models = set(problematic_models or [])
        exclude_models = set(exclude_models or [])
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

            if model_name_opset in exclude_models:
                continue
            if self.check_prob_models and model_name_opset not in problematic_models:
                continue
            if model_name_opset in excluded_names:
                continue
            if getattr(model_obj, "is_external", False):
                tags = [model_obj.external_spec["task"]]
            elif self.manifest_categories is not None:
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

            if getattr(model_obj, "is_external", False):
                if len(model_shape) == 4:
                    external_nhwc = model_shape[-1] == 3
                    spatial = model_shape[1:3] if external_nhwc else model_shape[-2:]
                else:
                    spatial = []
                model_config.update({
                    "external": True,
                    "task": model_obj.external_spec["task"],
                    "model_name": model_name,
                    "input_specs": model_obj.metadata["io_ports"]["inputs"],
                    "model_dir": model_obj.external_model_dir,
                    "primary_model_path": model_obj.external_model_path,
                    "input_dimension": spatial,
                })

            model_path = (
                model_obj.external_model_path
                if getattr(model_obj, "is_external", False)
                else self.get_model_path(
                    model_obj,
                    self.hub_config["cache_folder_rel_path"],
                )
            )
            source_key = self.manifest_source_keys.get(
                (model_name, model_opset), model_name_opset
            )
            if metadata_only:
                yield {
                    "model_no": model_no,
                    "model_name": model_name,
                    "model_name_opset": model_name_opset,
                    "opset": model_opset,
                    "source_key": source_key,
                    "tags": list(tags),
                    "model_config": model_config,
                    "model_path": model_path,
                    "shape_dict": {first_input["name"]: model_shape},
                    "external": getattr(model_obj, "is_external", False),
                    "external_spec": getattr(model_obj, "external_spec", None),
                    "external_model_dir": getattr(model_obj, "external_model_dir", None),
                }
                continue
            model_stage = (
                self.pipeline_trace.stage(
                    "model.onnx_load", model=model_name_opset
                )
                if self.pipeline_trace
                else nullcontext()
            )
            with model_stage:
                if getattr(model_obj, "is_external", False):
                    model = onnx.load(model_path)
                elif "text" in tags:
                    model, model_path = self._load_text_model(
                        model_name, model_opset
                    )
                else:
                    model = hub.load(model_name, opset=model_opset)

            hash_stage = (
                self.pipeline_trace.stage(
                    "model.source_hash", model=model_name_opset
                )
                if self.pipeline_trace
                else nullcontext()
            )
            with hash_stage:
                with open(model_path, "rb") as model_file:
                    original_hash = hashlib.md5(model_file.read()).hexdigest()
            relax_model = None
            relax_input_names = None
            base_executable = None
            tvm_build_error = None
            if self.tvm_builder is not None and "text" not in tags:
                try:
                    builder_stage = (
                        self.pipeline_trace.stage(
                            "model.tvm_artifacts", model=model_name_opset
                        )
                        if self.pipeline_trace
                        else nullcontext()
                    )
                    with builder_stage:
                        relax_model, relax_input_names, base_executable = (
                            self.tvm_builder.build_base_artifacts(
                                model,
                                source_key=source_key,
                                model_hash=original_hash,
                                shape_dict={first_input["name"]: model_shape},
                            )
                        )
                except Exception as error:
                    tvm_build_error = error
                    print(f"Could not prepare base TVM executable for {source_key}: {error}")

            print("Model Number: " + str(model_no))
            print("Model Name: " + model_name)
            print(model_obj)
            print(first_input["shape"])

            yield {
                "model_name": model_name,
                "model_name_opset": model_name_opset,
                "source_key": source_key,
                "tags": tags,
                "model_config": model_config,
                "model_path": model_path,
                "model": model,
                "relax_model": relax_model,
                "relax_input_names": relax_input_names,
                "base_executable": base_executable,
                "tvm_build_error": tvm_build_error,
                "original_hash": original_hash,
                "opt_model_path": model_path.replace(".onnx", "_opt.onnx"),
                "external": getattr(model_obj, "is_external", False),
                "external_spec": getattr(model_obj, "external_spec", None),
                "external_model_dir": getattr(model_obj, "external_model_dir", None),
            }

    def _load_text_model(self, model_name, model_opset):
        return load_text_model(
            self.script_dir,
            self.hub_config,
            model_name,
            model_opset,
        )


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


def load_text_model(script_dir, hub_config, model_name, model_opset):
    """Load a text model artifact; shared by the coordinator and workers."""
    try:
        data_dir = Path(hub.download_model_with_test_data(model_name))
        candidates = [
            path
            for path in data_dir.rglob("GPT-2-LM-HEAD/*.onnx")
            if "_opt" not in path.name
        ]
        if candidates:
            model_path = sorted(candidates)[0]
            print("Text model path: " + str(model_path))
            return onnx.load(str(model_path)), str(model_path)
    except Exception as error:
        print(f"Could not load text model artifacts for {model_name}: {error}")
    model = hub.load(model_name, opset=model_opset)
    fallback = (
        Path(script_dir)
        / hub_config["cache_folder_rel_path"]
        / "text"
        / f"{model_name}-{model_opset}.onnx"
    )
    fallback.parent.mkdir(parents=True, exist_ok=True)
    onnx.save(model, str(fallback))
    return model, str(fallback)
