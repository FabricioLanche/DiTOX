#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import re
import sys
import tempfile
from pathlib import Path, PurePosixPath
from urllib.parse import quote
from urllib.request import urlopen


MANIFEST_URL = os.environ.get(
    "ONNX_HUB_MANIFEST_URL",
    "https://raw.githubusercontent.com/onnx/models/main/ONNX_HUB_MANIFEST.json",
)
MODELS_BASE_URL = os.environ.get(
    "ONNX_HUB_MODELS_BASE_URL",
    "https://media.githubusercontent.com/media/onnx/models/main/",
)
CHUNK_SIZE = 1024 * 1024


def read_json_url(url):
    with urlopen(url, timeout=60) as response:
        return json.load(response)


def cache_path(cache_dir, model):
    model_path = PurePosixPath(model["model_path"])
    model_sha = model.get("metadata", {}).get("model_sha")
    if model_path.is_absolute() or ".." in model_path.parts:
        raise ValueError(f"Unsafe model path in ONNX Hub manifest: {model_path}")
    if not isinstance(model_sha, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", model_sha):
        raise ValueError(f"Missing or invalid model SHA256 for {model['model']}")

    return cache_dir.joinpath(*model_path.parts[:-1], f"{model_sha}_{model_path.name}")


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as file:
        while chunk := file.read(CHUNK_SIZE):
            digest.update(chunk)
    return digest.hexdigest()


def download_model(cache_dir, model):
    destination = cache_path(cache_dir, model)
    expected_sha = model["metadata"]["model_sha"].lower()
    if destination.is_file():
        if sha256_file(destination) == expected_sha:
            print(f"Cached: {model['model']}-{model['opset_version']}")
            return

    destination.parent.mkdir(parents=True, exist_ok=True)
    url = MODELS_BASE_URL.rstrip("/") + "/" + quote(model["model_path"], safe="/")
    print(f"Downloading {model['model']}-{model['opset_version']} from {url}", flush=True)
    digest = hashlib.sha256()
    temp_path = None
    try:
        with urlopen(url, timeout=60) as response:
            with tempfile.NamedTemporaryFile(
                dir=destination.parent, prefix=".download-", delete=False
            ) as output:
                temp_path = Path(output.name)
                while True:
                    chunk = response.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    digest.update(chunk)
                    output.write(chunk)

        if digest.hexdigest() != expected_sha:
            raise ValueError(
                f"SHA256 mismatch for {model['model']}-{model['opset_version']}: "
                f"expected {expected_sha}, got {digest.hexdigest()}"
            )
        os.replace(temp_path, destination)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()

    print(f"Downloaded: {model['model']}-{model['opset_version']}")


def selected_models(project_root, catalog):
    with (project_root / "config_tvm_vision.json").open(encoding="utf-8") as file:
        config = json.load(file)
    hub_config = config["hub"]
    general_config = config["general"]

    with (project_root / hub_config["model_manifest_rel_path"].lstrip("/\\")).open(
        encoding="utf-8"
    ) as file:
        project_manifest = json.load(file)

    catalog_by_id = {
        (model["model"], int(model["opset_version"])): model for model in catalog
    }
    categories = {
        (item["model"], int(item["opset"])): item["category"]
        for item in project_manifest["models"]
    }
    included_categories = set(hub_config["tags_of_models_to_consider"])
    excluded_names = set(general_config.get("exclude_name_filters", []))
    name_filters = general_config.get("name_filters", [])
    exact_match = general_config.get("match_filter_exact", True)
    minimum_opset = int(hub_config["opset_bottom_threshold"])
    skip_until = int(general_config.get("skip_until_model_id", 0))
    run_up_to = int(general_config.get("run_up_to_model_id", sys.maxsize))

    ordered_models = [
        (index, catalog_by_id[model_id], categories[model_id])
        for index, model_id in enumerate(categories, start=1)
        if model_id in catalog_by_id
    ]
    missing = [model_id for model_id in categories if model_id not in catalog_by_id]
    if missing:
        print(
            "Warning: models absent from the current ONNX Hub catalog: "
            + ", ".join(f"{name}-{opset}" for name, opset in missing),
            file=sys.stderr,
        )

    selected = []
    for index, model, category in ordered_models:
        model_id = f"{model['model']}-{model['opset_version']}"
        if index < skip_until or index > run_up_to:
            continue
        if category not in included_categories:
            continue
        if model_id in excluded_names or int(model["opset_version"]) < minimum_opset:
            continue
        if name_filters and not any(
            model_id == value if exact_match else value in model_id
            for value in name_filters
        ):
            continue
        selected.append(model)

    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("project_root", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate the prepared cache without accessing the network",
    )
    args = parser.parse_args()
    project_root = args.project_root.resolve()
    cache_dir = project_root / "models_cache"

    catalog_path = cache_dir / "ONNX_HUB_MANIFEST.json"
    if args.check:
        if not cache_dir.is_dir():
            raise FileNotFoundError(
                f"Offline ONNX model cache not found: {cache_dir}. Run setup.sh."
            )
        if not catalog_path.is_file():
            raise FileNotFoundError(
                f"Offline ONNX Hub catalog not found: {catalog_path}. Run setup.sh."
            )
        with catalog_path.open(encoding="utf-8") as file:
            catalog = json.load(file)
    else:
        cache_dir.mkdir(parents=True, exist_ok=True)
        print(f"Fetching ONNX Hub catalog from {MANIFEST_URL}...")
        catalog = read_json_url(MANIFEST_URL)
    if not isinstance(catalog, list):
        raise ValueError("The ONNX Hub catalog must be a JSON list.")

    if not args.check:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=cache_dir, prefix=".manifest-", delete=False
        ) as output:
            manifest_temp = Path(output.name)
            json.dump(catalog, output)
            output.write("\n")
        os.replace(manifest_temp, catalog_path)

    models = selected_models(project_root, catalog)
    if args.check:
        missing = [
            str(cache_path(cache_dir, model))
            for model in models
            if not cache_path(cache_dir, model).is_file()
            or cache_path(cache_dir, model).stat().st_size == 0
        ]
        if missing:
            raise FileNotFoundError(
                f"{len(missing)} of {len(models)} required vision models are missing:\n"
                + "\n".join(missing)
                + "\nRun setup.sh before submitting the vision job."
            )
        print(f"Offline cache ready: catalog and all {len(models)} vision models found.")
        return

    print(f"Preparing {len(models)} vision models in {cache_dir}...")
    for model in models:
        download_model(cache_dir, model)
    print(f"Prepared {len(models)} vision models for offline runs.")


if __name__ == "__main__":
    main()
