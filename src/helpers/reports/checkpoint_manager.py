"""Persistent, execution-scoped progress for resumable pipeline runs."""

import copy
import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path


class CheckpointManager:
    SCHEMA_VERSION = 2

    def __init__(
        self,
        project_root,
        config_path,
        config_data,
        image_paths,
        model_ids,
        settings,
    ):
        self.project_root = Path(project_root).resolve()
        self.config_path = Path(config_path).resolve()
        self.settings = settings
        self.enabled = settings.get("enabled", True)
        self.state = None
        if not self.enabled:
            return

        identity = self._build_identity(config_data, image_paths)
        fingerprint = hashlib.sha256(
            json.dumps(identity, sort_keys=True, separators=(",", ":")).encode(
                "utf-8"
            )
        ).hexdigest()
        directory = Path(settings.get("directory", "results/checkpoints")).expanduser()
        if not directory.is_absolute():
            directory = self.project_root / directory
        run_name = fingerprint[:16]
        self.run_directory = directory / run_name
        self.state_path = self.run_directory / "state.json"
        self.journal_directory = self.run_directory / "models"
        self.fingerprint = fingerprint

        if settings.get("resume", True) and self.state_path.is_file():
            with self.state_path.open("r", encoding="utf-8") as state_file:
                state = json.load(state_file)
            if (
                state.get("schema_version") != self.SCHEMA_VERSION
                or state.get("fingerprint") != self.fingerprint
            ):
                raise ValueError(
                    f"Checkpoint is incompatible with this run: {self.state_path}"
                )
            self.state = state
            print(
                f"Resuming checkpoint {self.state_path} "
                f"({len(self.state.get('completed_models', []))} models complete)."
            )

    def _build_identity(self, config_data, image_paths):
        execution_config = copy.deepcopy(config_data)
        execution_config.pop("checkpoint", None)
        general_config = execution_config.get("general")
        if isinstance(general_config, dict):
            for key in (
                "check_reports_for_problematic_models",
                "exclude_name_filters",
                "match_filter_exact",
                "name_filters",
                "report_file_base_rel_path",
                "run_up_to_model_id",
                "skip_until_model_id",
            ):
                general_config.pop(key, None)
        hub_config = execution_config.get("hub")
        if isinstance(hub_config, dict):
            for key in (
                "opset_bottom_threshold",
                "tags",
                "tags_of_models_to_consider",
            ):
                hub_config.pop(key, None)

        image_inputs = []
        for image_path in image_paths:
            path = Path(image_path)
            try:
                stat = path.stat()
                image_inputs.append(
                    {
                        "path": str(path.resolve()),
                        "size": stat.st_size,
                        "mtime_ns": stat.st_mtime_ns,
                    }
                )
            except OSError:
                image_inputs.append({"path": str(path.resolve()), "missing": True})

        source_files = [
            self.project_root / "main.py",
            self.project_root / "requirements.txt",
        ]
        for source_root in (self.project_root / "configs", self.project_root / "src"):
            if source_root.is_dir():
                source_files.extend(source_root.rglob("*.py"))
        source_hashes = {}
        for path in sorted(set(source_files), key=str):
            if path.is_file():
                source_hashes[str(path.relative_to(self.project_root))] = (
                    hashlib.sha256(path.read_bytes()).hexdigest()
                )

        manifest_path = (
            self.project_root
            / config_data.get("hub", {}).get("model_manifest_rel_path", "")
        )
        manifest_hash = (
            hashlib.sha256(manifest_path.read_bytes()).hexdigest()
            if manifest_path.is_file()
            else None
        )
        return {
            "config": execution_config,
            "images": image_inputs,
            "manifest_sha256": manifest_hash,
            "source_sha256": source_hashes,
        }

    @property
    def active(self):
        return self.enabled

    @property
    def completed_models(self):
        if self.state is None:
            return set()
        return set(self.state.get("completed_models", []))

    @property
    def resumed(self):
        return self.state is not None

    def initialize(
        self,
        report_templates,
        problematic_models_by_report,
        completed_model_ids=None,
    ):
        if not self.enabled or self.state is not None:
            return
        seeded_models = sorted(set(completed_model_ids or []))
        self.state = {
            "schema_version": self.SCHEMA_VERSION,
            "fingerprint": self.fingerprint,
            "config_path": str(self.config_path),
            "status": "running",
            "created_at": self._now(),
            "updated_at": self._now(),
            "completed_models": list(seeded_models),
            "seeded_models": seeded_models,
            "report_templates": copy.deepcopy(report_templates),
            "problematic_models_by_report": copy.deepcopy(
                problematic_models_by_report
            ),
        }
        self._save_state()

    def reports_for(self, report_paths):
        if self.state is None:
            return None
        reports = copy.deepcopy(self.state["report_templates"])
        for model_id in self.state.get("completed_models", []):
            if model_id in self.state.get("seeded_models", []):
                continue
            journal_path = self._journal_path(model_id)
            with journal_path.open("r", encoding="utf-8") as journal_file:
                journal = json.load(journal_file)
            for report_path, model_result in journal["reports"].items():
                if report_path in reports:
                    from src.helpers.reports.report_manager import ReportManager

                    ReportManager.merge_model_result(reports[report_path], model_result)
        return {
            str(report_path): reports[str(report_path)]
            for report_path in report_paths
            if str(report_path) in reports
        }

    def problematic_models_for(self, report_path):
        if self.state is None:
            return None
        values = self.state.get("problematic_models_by_report", {}).get(
            str(report_path)
        )
        return None if values is None else set(values)

    def record_model(self, model_id, reports_by_path):
        if not self.enabled or self.state is None or model_id in self.completed_models:
            return
        self.journal_directory.mkdir(parents=True, exist_ok=True)
        journal = {
            "model_id": model_id,
            "reports": {
                str(path): copy.deepcopy(report)
                for path, report in reports_by_path.items()
            },
        }
        self._atomic_json_save(self._journal_path(model_id), journal)
        self.state["completed_models"].append(model_id)
        self.state["updated_at"] = self._now()
        self._save_state()

    def mark_run_completed(self):
        if not self.enabled or self.state is None:
            return
        self.state["status"] = "completed"
        self.state["updated_at"] = self._now()
        self._save_state()

    def _journal_path(self, model_id):
        model_token = hashlib.sha256(model_id.encode("utf-8")).hexdigest()
        return self.journal_directory / f"{model_token}.json"

    def _save_state(self):
        self._atomic_json_save(self.state_path, self.state)

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

    @staticmethod
    def _now():
        return datetime.now(timezone.utc).isoformat(timespec="seconds")
