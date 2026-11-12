import json
import logging
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from time import perf_counter
from uuid import uuid4


class _JsonLineFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.fromtimestamp(
                record.created, tz=timezone.utc
            ).isoformat(timespec="milliseconds"),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        payload.update(getattr(record, "trace_fields", {}))
        return json.dumps(payload, ensure_ascii=False, default=str)


class PipelineTrace:
    """Emit pipeline events to the console and a structured JSONL trace."""

    def __init__(self, logger, run_id):
        self.logger = logger
        self.run_id = run_id
        self.started = perf_counter()

    def event(self, event_name, level=logging.INFO, **fields):
        fields.setdefault(
            "run_elapsed_seconds", round(perf_counter() - self.started, 6)
        )
        trace_fields = {"event": event_name, "run_id": self.run_id, **fields}
        message = f"{event_name} {json.dumps(fields, ensure_ascii=False, default=str)}"
        self.logger.log(
            level,
            message,
            extra={"trace_fields": trace_fields},
        )

    @contextmanager
    def stage(self, stage_name, **context):
        started = perf_counter()
        self.event("stage.started", stage=stage_name, **context)
        try:
            yield
        except Exception as error:
            self.event(
                "stage.failed",
                level=logging.ERROR,
                stage=stage_name,
                elapsed_seconds=round(perf_counter() - started, 6),
                error=repr(error),
                **context,
            )
            raise
        else:
            self.event(
                "stage.completed",
                stage=stage_name,
                elapsed_seconds=round(perf_counter() - started, 6),
                **context,
            )


def configure_pipeline_logger(project_root, settings=None):
    settings = settings or {}
    run_id = uuid4().hex[:12]
    logger = logging.getLogger("ditox.pipeline")
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
        handler.close()
    logger.propagate = False
    level_name = str(settings.get("level", "INFO")).upper()
    level = getattr(logging, level_name, None)
    if not isinstance(level, int):
        raise ValueError(f"Unknown pipeline logging level: {level_name}")
    logger.setLevel(level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(console_handler)

    trace_path = settings.get(
        "file", f"results/logs/pipeline-{run_id}.jsonl"
    )
    if trace_path:
        trace_path = Path(trace_path).expanduser()
        if not trace_path.is_absolute():
            trace_path = Path(project_root) / trace_path
        trace_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(trace_path, encoding="utf-8")
        file_handler.setFormatter(_JsonLineFormatter())
        logger.addHandler(file_handler)

    return PipelineTrace(logger, run_id)
