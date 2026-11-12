import json
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
    def load(report_path):
        with Path(report_path).open("r", encoding="utf-8") as report_file:
            return json.load(report_file)

    @staticmethod
    def save(report_path, report):
        report_path = Path(report_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        with report_path.open("w", encoding="utf-8") as report_file:
            json.dump(report, report_file, indent=2)
