import json
import os
import tempfile
from pathlib import Path


class ReportManager:
    """Build, inspect, and persist per-chunk pipeline reports."""

    def __init__(self, project_root, report_file_base_rel_path):
        self.project_root = Path(project_root)
        self.report_file_base_rel_path = report_file_base_rel_path

    def chunk_path(self, starts_from, ends_at):
        report_path = self.project_root / self.report_file_base_rel_path.lstrip("/\\")
        report_stem = report_path.stem.split("_chunk", 1)[0]
        return report_path.with_name(
            f"{report_stem}_chunk_{starts_from}_{ends_at}{report_path.suffix}"
        )

    @staticmethod
    def new_report(
        manifest_categories=None,
        manifest_missing_models=None,
        manifest_excluded_by_config=None,
    ):
        report = {
            "no_dissimilar": 0,
            "base_models_run": 0,
            "model_instances_run": 0,
            "failed_conversions_no": 0,
            "skipped_models": [],
            "failed_models": [],
            "conversion_errors": {},
        }
        if manifest_categories is not None:
            missing_models = manifest_missing_models or []
            excluded_models = manifest_excluded_by_config or []
            report.update(
                {
                    "manifest_models_expected": len(manifest_categories),
                    "manifest_models_not_found": missing_models,
                    "manifest_models_excluded_by_config": excluded_models,
                    "manifest_models_selected_by_config": (
                        len(manifest_categories)
                        - len(missing_models)
                        - len(excluded_models)
                    ),
                }
            )
        return report

    @staticmethod
    def problematic_models(report_path):
        report = ReportManager.load(report_path)

        return (
            set(report.get("failed_models", []))
            | {
                model
                for model, error in report.get("conversion_errors", {}).items()
                if error
            }
            | {
                model
                for model, result in report.items()
                if isinstance(result, dict)
                and any(result.get(key) for key in ("different", "failed", "blocked"))
            }
        )

    @staticmethod
    def model_ids(report, candidates):
        completed_models = set()
        for model_id in candidates:
            result = report.get(model_id)
            if not isinstance(result, dict):
                continue
            if result.get("failed") or result.get("blocked"):
                continue
            if result.get("run", 0) > 0 or result.get("baseline_only"):
                completed_models.add(model_id)
        return completed_models

    @staticmethod
    def clear_model_failures(report, model_id):
        for key in ("failed_models", "skipped_models"):
            report[key] = [
                reported_model
                for reported_model in report.get(key, [])
                if reported_model != model_id
            ]
        report.setdefault("conversion_errors", {}).pop(model_id, None)

    @staticmethod
    def is_compatible(existing_report, expected_report):
        metadata_keys = (
            "manifest_models_expected",
            "manifest_models_not_found",
            "manifest_models_excluded_by_config",
            "manifest_models_selected_by_config",
        )
        return all(
            key in existing_report
            and existing_report[key] == expected_report.get(key)
            for key in metadata_keys
        )

    @staticmethod
    def load(report_path):
        with Path(report_path).open("r", encoding="utf-8") as report_file:
            return json.load(report_file)

    @staticmethod
    def save(report_path, report):
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=report_path.parent,
                prefix=f".{report_path.name}-",
                suffix=".tmp",
                delete=False,
            ) as report_file:
                temporary_path = Path(report_file.name)
                json.dump(report, report_file, indent=2)
                report_file.flush()
                os.fsync(report_file.fileno())
            os.replace(temporary_path, report_path)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    @staticmethod
    def extract_model_result(before, after, model_id):
        """Return only the report contribution added while processing one model."""
        result = {
            key: after.get(key, 0) - before.get(key, 0)
            for key in (
                "no_dissimilar",
                "base_models_run",
                "model_instances_run",
                "failed_conversions_no",
            )
        }
        for key in ("skipped_models", "failed_models"):
            old_length = len(before.get(key, []))
            result[key] = after.get(key, [])[old_length:]
        if model_id in after.get("conversion_errors", {}):
            result["conversion_errors"] = {
                model_id: after["conversion_errors"][model_id]
            }
        if model_id in after:
            result[model_id] = after[model_id]
        return result

    @staticmethod
    def merge_model_result(report, model_result):
        """Merge one isolated model report into a coordinator-owned report."""
        counter_keys = (
            "no_dissimilar",
            "base_models_run",
            "model_instances_run",
            "failed_conversions_no",
        )
        list_keys = ("skipped_models", "failed_models")
        header_keys = {
            "manifest_models_expected",
            "manifest_models_not_found",
            "manifest_models_excluded_by_config",
            "manifest_models_selected_by_config",
        }

        for key in counter_keys:
            report[key] = report.get(key, 0) + model_result.get(key, 0)
        for key in list_keys:
            report.setdefault(key, []).extend(model_result.get(key, []))
        report.setdefault("conversion_errors", {}).update(
            model_result.get("conversion_errors", {})
        )
        for key, value in model_result.items():
            if key not in {*counter_keys, *list_keys, "conversion_errors", *header_keys}:
                report[key] = value
