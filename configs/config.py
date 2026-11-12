import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _env_int(name, minimum):
    """Return an optional integer from the environment, validating its range."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return None
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer, got {raw!r}.") from exc
    if value < minimum:
        raise ValueError(f"{name} must be >= {minimum}, got {value}.")
    return value


def _apply_runtime_overrides(data):
    """Overlay runtime.tvm values with DITOX_* environment variables.

    This keeps the JSON configs as the source of truth while allowing Slurm
    scripts to tune workers/threads per job without rewriting files.
    """
    model_workers = _env_int("DITOX_MODEL_WORKERS", 1)
    threads_per_worker = _env_int("DITOX_THREADS_PER_WORKER", 0)
    if model_workers is None and threads_per_worker is None:
        return data

    runtime = data.get("runtime")
    if runtime is None:
        runtime = {}
        data["runtime"] = runtime
    if not isinstance(runtime, dict):
        return data
    tvm_runtime = runtime.get("tvm")
    if tvm_runtime is None:
        tvm_runtime = {}
        runtime["tvm"] = tvm_runtime
    if not isinstance(tvm_runtime, dict):
        return data
    if model_workers is not None:
        tvm_runtime["model_workers"] = model_workers
    if threads_per_worker is not None:
        tvm_runtime["threads_per_worker"] = threads_per_worker
    return data


@dataclass(frozen=True)
class PipelineConfig:
    """Configuration sections for one DiTOX run."""

    path: Path
    images: dict[str, Any]
    general: dict[str, Any]
    hub: dict[str, Any]
    optimizer: dict[str, Any]
    runtime: dict[str, Any]
    logging: dict[str, Any]
    tvm: dict[str, Any]
    text: dict[str, Any]
    checkpoint: dict[str, Any]
    task: dict[str, Any]
    backend: str


def load_pipeline_config(config_path=None):
    """Load the run configuration JSON, defaulting to the repository config."""
    if config_path is None:
        path = Path(__file__).resolve().parent / "run" / "config.json"
    else:
        path = Path(config_path).expanduser()
        if not path.is_absolute():
            path = Path.cwd() / path

    with path.open("r", encoding="utf-8") as config_file:
        data = json.load(config_file)

    if not isinstance(data, dict):
        raise ValueError(f"Pipeline configuration must be a JSON object: {path}")

    data = _apply_runtime_overrides(data)

    required_sections = ("images", "general", "hub", "optimizer")
    missing_sections = [section for section in required_sections if section not in data]
    if missing_sections:
        raise ValueError(
            f"Pipeline configuration is missing sections {missing_sections}: {path}"
        )

    invalid_sections = [
        section
        for section in required_sections
        + ("runtime", "tvm", "logging", "text", "checkpoint")
        + ("task",)
        if section in data and not isinstance(data[section], dict)
    ]
    if invalid_sections:
        raise ValueError(
            f"Pipeline configuration sections must be JSON objects "
            f"({invalid_sections}): {path}"
        )

    task = data.get("task", {})
    if task:
        task_type = task.get("type")
        if task_type not in {"body_recognition", "speech_recognition"}:
            raise ValueError(
                "task.type must be 'body_recognition' or 'speech_recognition'."
            )
        task_path_keys = (
            ("dataset_path", "images_dir")
            if task_type == "body_recognition"
            else ("dataset_path",)
        )
        for key in task_path_keys:
            if not isinstance(task.get(key), str) or not task[key].strip():
                raise ValueError(f"task.{key} must be a non-empty path.")
        if "limit" in task and (type(task["limit"]) is not int or task["limit"] < 1):
            raise ValueError("task.limit must be a positive integer.")

    general = data["general"]
    runtime = data.get("runtime", {})
    tvm_runtime = runtime.get("tvm", {})
    if not isinstance(tvm_runtime, dict):
        raise ValueError("runtime.tvm must be an object.")
    model_workers = tvm_runtime.get("model_workers", 1)
    threads_per_worker = tvm_runtime.get("threads_per_worker", 0)
    if type(model_workers) is not int or model_workers < 1:
        raise ValueError("runtime.tvm.model_workers must be a positive integer.")
    if type(threads_per_worker) is not int or threads_per_worker < 0:
        raise ValueError(
            "runtime.tvm.threads_per_worker must be a non-negative integer."
        )
    checkpoint = data.get("checkpoint", {})
    if type(checkpoint.get("enabled", True)) is not bool:
        raise ValueError("checkpoint.enabled must be a boolean.")
    if type(checkpoint.get("resume", True)) is not bool:
        raise ValueError("checkpoint.resume must be a boolean.")
    checkpoint_directory = checkpoint.get("directory", "results/checkpoints")
    if not isinstance(checkpoint_directory, str) or not checkpoint_directory.strip():
        raise ValueError("checkpoint.directory must be a non-empty string.")
    checkpoint = {
        "enabled": checkpoint.get("enabled", True),
        "resume": checkpoint.get("resume", True),
        "directory": checkpoint_directory,
    }

    return PipelineConfig(
        path=path.resolve(),
        images=data["images"],
        general=general,
        hub=data["hub"],
        optimizer=data["optimizer"],
        runtime=runtime,
        logging=data.get("logging", data.get("runtime", {}).get("logging", {})),
        tvm=data.get("tvm", {}),
        text=data.get("text", {}),
        checkpoint=checkpoint,
        task=data.get("task", {}),
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
