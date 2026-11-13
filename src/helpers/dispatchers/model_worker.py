"""Isolated process entry point for one model's complete test run."""

import hashlib
import os
import tempfile
from pathlib import Path


def _model_hash(model, model_path):
    path = Path(model_path)
    if path.is_file():
        return hashlib.md5(path.read_bytes()).hexdigest()
    return hashlib.md5(model.SerializeToString()).hexdigest()


def _load_model(model_spec, project_root, run_config, hub_cache_dir):
    from onnx import hub
    import onnx

    from src.model_orchestrator.model_orchestrator import (
        load_onnx_hub_model,
        load_text_model,
    )

    tags = model_spec["tags"]
    hub.set_dir(str(hub_cache_dir))
    if model_spec.get("external"):
        model_path = Path(model_spec["model_path"])
        model = onnx.load(str(model_path))
    elif "text" in tags:
        model, model_path = load_text_model(
            project_root,
            run_config.hub,
            model_spec["model_name"],
            model_spec["opset"],
        )
        model_path = Path(model_path)
    else:
        model = load_onnx_hub_model(
            model_spec["model_name"], model_spec["opset"]
        )
        model_path = Path(model_spec["model_path"])
    return model, model_path


def _build_tvm_artifacts(
    model,
    model_spec,
    original_hash,
    run_config,
    project_root,
    hub_cache_dir,
    pipeline_trace,
):
    if run_config.backend != "tvmr" or "text" in model_spec["tags"]:
        return None, None, None, None

    from src.model_orchestrator.tvm_builder import TVMBuilder

    runtime_tvm_config = run_config.runtime.get("tvm", {})
    compiled_cache_dir = (
        runtime_tvm_config.get("compiled_cache_dir")
        or run_config.tvm.get("compiled_cache_dir")
    )
    if compiled_cache_dir is None:
        compiled_cache_dir = hub_cache_dir / "tvm_compiled"
    else:
        compiled_cache_dir = Path(compiled_cache_dir).expanduser()
        if not compiled_cache_dir.is_absolute():
            compiled_cache_dir = project_root / compiled_cache_dir

    try:
        tvm_builder = TVMBuilder(compiled_cache_dir, pipeline_trace=pipeline_trace)
        return tvm_builder.build_base_artifacts(
            model,
            source_key=model_spec["source_key"],
            model_hash=original_hash,
            shape_dict=model_spec["shape_dict"],
        ) + (None,)
    except Exception as error:
        print(
            f"Could not prepare base TVM executable for "
            f"{model_spec['source_key']}: {error}"
        )
        return None, None, None, error


def run_model_task(task):
    """Load, compile, and test one model in a fresh worker process."""
    threads_per_worker = task["threads_per_worker"]
    if threads_per_worker > 0:
        os.environ["TVM_NUM_THREADS"] = str(threads_per_worker)

    # Import project components only after setting the per-worker TVM limit.
    from configs.config import load_pipeline_config
    from main import _process_model_batch
    from src.helpers.dispatchers import BackendDispatcher, ModelComparisonDispatcher
    from src.helpers.reports import ReportManager
    from src.helpers.reports.logger import configure_pipeline_logger
    from src.runner.preprocessing.text_inputs import TextInputProvider

    project_root = Path(task["project_root"])
    (project_root / "results").mkdir(parents=True, exist_ok=True)
    run_config = load_pipeline_config(task["config_path"])
    model_spec = task["model_spec"]
    model_name_opset = model_spec["model_name_opset"]
    model_token = hashlib.sha256(model_name_opset.encode("utf-8")).hexdigest()[:12]
    worker_id = f"{os.getpid()}-{model_token}"
    log_settings = dict(run_config.logging)
    log_settings["file"] = str(
        Path("results/logs/model-workers") / f"{worker_id}.jsonl"
    )
    pipeline_trace = configure_pipeline_logger(project_root, log_settings)
    pipeline_trace.event(
        "model.worker.started",
        model=model_name_opset,
        threads_per_worker=threads_per_worker,
    )

    hub_config = run_config.hub
    hub_cache_dir = project_root / hub_config["cache_folder_rel_path"].lstrip("/\\")
    model, model_path = _load_model(
        model_spec,
        project_root,
        run_config,
        hub_cache_dir,
    )
    original_hash = _model_hash(model, model_path)
    relax_model, relax_input_names, base_executable, tvm_build_error = (
        _build_tvm_artifacts(
            model,
            model_spec,
            original_hash,
            run_config,
            project_root,
            hub_cache_dir,
            pipeline_trace,
        )
    )
    model_data = {
        **model_spec,
        "model": model,
        "model_path": str(model_path),
        "relax_model": relax_model,
        "relax_input_names": relax_input_names,
        "base_executable": base_executable,
        "tvm_build_error": tvm_build_error,
        "original_hash": original_hash,
        "opt_model_path": str(model_path).replace(".onnx", "_opt.onnx"),
    }

    backend_dispatcher = BackendDispatcher(
        run_config, pipeline_trace=pipeline_trace
    )
    comparison_dispatcher = ModelComparisonDispatcher()
    worker_report_manager = ReportManager(project_root, "worker.json")
    text_input_provider = TextInputProvider(run_config.text)
    preloaded_text_prompts = (
        text_input_provider.load() if "text" in model_spec["tags"] else None
    )
    results = []

    with tempfile.TemporaryDirectory(
        prefix="ditox-model-worker-", dir=str(project_root / "results")
    ) as temporary_dir:
        temporary_dir = Path(temporary_dir)
        for batch_index, source_batch in enumerate(task["batch_states"]):
            batch_state = dict(source_batch)
            batch_state["report_path"] = temporary_dir / f"batch-{batch_index}.json"
            batch_state["report_started"] = False
            if preloaded_text_prompts is not None:
                batch_state["text_prompts"] = preloaded_text_prompts
            _process_model_batch(
                model_data,
                batch_state,
                report_manager=worker_report_manager,
                backend_dispatcher=backend_dispatcher,
                comparison_dispatcher=comparison_dispatcher,
                onnx_runner=backend_dispatcher.onnx_runner,
                general_config=run_config.general,
                images_config=run_config.images,
                optimizer_config=run_config.optimizer,
                include_certainties=run_config.general["include_certainties"],
                enable_kt_on_one_dim_tensor=run_config.general[
                    "enable_kt_on_one_dim_tensor"
                ],
                pipeline_trace=pipeline_trace,
                text_input_provider=text_input_provider,
            )
            results.append(ReportManager.load(batch_state["report_path"]))

    pipeline_trace.event(
        "model.worker.completed",
        model=model_name_opset,
        batch_count=len(results),
    )
    return {"model_name_opset": model_name_opset, "reports": results}
