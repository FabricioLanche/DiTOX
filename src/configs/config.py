import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration sections for one DiTOX run."""

    path: Path
    images: dict[str, Any]
    general: dict[str, Any]
    hub: dict[str, Any]
    optimizer: dict[str, Any]
    runtime: dict[str, Any]
    tvm: dict[str, Any]
    backend: str


def load_pipeline_config(config_path=None):
    """Load the run configuration JSON, defaulting to the repository config."""
    if config_path is None:
        path = Path(__file__).resolve().parent / "configs" / "run" / "config.json"
    else:
        path = Path(config_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path

    with path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)

    if not isinstance(data, dict):
        raise ValueError(f"Pipeline configuration must be a JSON object: {path}")

    required_sections = ("images", "general", "hub", "optimizer")
    missing_sections = [section for section in required_sections if section not in data]
    if missing_sections:
        raise ValueError(
            f"Pipeline configuration is missing sections {missing_sections}: {path}"
        )

    invalid_sections = [
        section
        for section in required_sections + ("runtime", "tvm")
        if section in data and not isinstance(data[section], dict)
    ]
    if invalid_sections:
        raise ValueError(
            f"Pipeline configuration sections must be JSON objects "
            f"({invalid_sections}): {path}"
        )

    general = data["general"]

    return PipelineConfig(
        path=path.resolve(),
        images=data["images"],
        general=general,
        hub=data["hub"],
        optimizer=data["optimizer"],
        runtime=data.get("runtime", {}),
        tvm=data.get("tvm", {}),
        backend=general.get(
            "backend", data.get("runtime", {}).get("backend", "ort")
        ),
    )


def load_model_config(model_path):
    """Load an optional JSON sidecar stored next to an ONNX model."""
    model_path = Path(model_path)
    config_path = model_path.with_suffix(".json")
    if not config_path.exists():
        print(
            f"Warning: config for {model_path} was not found.\n"
            "Using default config..."
        )
        return {}

    with config_path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)
    if not isinstance(data, dict):
        raise ValueError(f"Model configuration must be a JSON object: {config_path}")
    return data
