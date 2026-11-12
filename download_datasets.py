import argparse
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DATASETS_DIR = PROJECT_ROOT / "configs" / "dataset"

COCO_DIR = DATASETS_DIR / "COCO"
COCO_EXPECTED_IMAGES = 5000

SQUAD_DIR = DATASETS_DIR / "SQuAD_v2"
IMDB_DIR = DATASETS_DIR / "IMDB"
LIBRISPEECH_DIR = DATASETS_DIR / "LibriSpeech"
COCO_KEYPOINTS_DIR = DATASETS_DIR / "COCO_Keypoints"
COCO_KEYPOINTS_IMAGES_DIR = COCO_KEYPOINTS_DIR / "images"

PARQUET_REVISION = "refs/convert/parquet"

DATASET_TARGETS = {
    "squad_v2": ("rajpurkar/squad_v2", SQUAD_DIR, [("validation", None)]),
    "imdb": ("stanfordnlp/imdb", IMDB_DIR, [("test", None)]),
    "librispeech": (
        "openslr/librispeech_asr",
        LIBRISPEECH_DIR,
        [("test", "clean")],
    ),
    "coco_keypoints": ("rom1x38/COCO_keypoints", COCO_KEYPOINTS_DIR, [("val", None)]),
}


def load_huggingface():
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise SystemExit(
            "Faltan dependencias. Instala con: pip install datasets pillow pyarrow"
        ) from exc
    return load_dataset


def download_coco(load_dataset, force=False):
    existing = list(COCO_DIR.glob("*.jpg")) if COCO_DIR.exists() else []
    if len(existing) >= COCO_EXPECTED_IMAGES and not force:
        print(
            f"[COCO] Ya hay {len(existing)} imagenes en {COCO_DIR}. Se omite la descarga."
        )
        return

    print("[COCO] Descargando rafaelpadilla/coco2017 (split=val)...")
    COCO_DIR.mkdir(parents=True, exist_ok=True)
    dataset = load_dataset("rafaelpadilla/coco2017", split="val")

    saved = skipped = 0
    for row in dataset:
        image_id = row.get("image_id", row.get("id"))
        if image_id is None:
            raise ValueError("El registro de COCO no contiene image_id/id.")
        target = COCO_DIR / f"{int(image_id):012d}.jpg"
        if target.exists() and not force:
            skipped += 1
            continue
        image = row["image"]
        if image.mode != "RGB":
            image = image.convert("RGB")
        image.save(target, format="JPEG")
        saved += 1

    total = len(list(COCO_DIR.glob("*.jpg")))
    print(f"[COCO] Guardadas: {saved}, ya existentes: {skipped}, total: {total}.")
    if total < COCO_EXPECTED_IMAGES:
        print(
            f"[COCO] Advertencia: se esperaban {COCO_EXPECTED_IMAGES} imagenes y hay {total}."
        )


def _match_shards(files, split, config=None):
    shards = []
    for filename in files:
        if not filename.endswith(".parquet"):
            continue
        parts = filename.split("/")
        directories = parts[:-1]
        basename = parts[-1]
        split_matches = (
            split in directories
            or basename.startswith(f"{split}-")
            or basename.startswith(f"{split}.")
        )
        config_matches = config is None or config in directories
        if split_matches and config_matches:
            shards.append(filename)
    return sorted(shards)


def _find_parquet_shards(repo_id, split, config=None):
    from huggingface_hub import HfApi

    api = HfApi()
    try:
        files = api.list_repo_files(
            repo_id, repo_type="dataset", revision=PARQUET_REVISION
        )
    except Exception:
        files = []
    shards = _match_shards(files, split, config)
    if shards:
        return shards, PARQUET_REVISION

    files = api.list_repo_files(repo_id, repo_type="dataset")
    return _match_shards(files, split, config), None


def _download_parquet_split(repo_id, split, target, config=None):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download

    shards, revision = _find_parquet_shards(repo_id, split, config)
    if not shards:
        return None

    download_kwargs = {"repo_type": "dataset"}
    if revision is not None:
        download_kwargs["revision"] = revision
    local_shards = [
        hf_hub_download(repo_id, filename, **download_kwargs)
        for filename in shards
    ]
    tables = [pq.read_table(path) for path in local_shards]
    table = pa.concat_tables(tables) if len(tables) > 1 else tables[0]
    target.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, target)
    return table.num_rows


def extract_keypoints_images(parquet_path, images_dir, force=False):
    import pyarrow.parquet as pq

    if not parquet_path.exists():
        print(f"[COCO Keypoints] Falta {parquet_path}; se omite la extraccion.")
        return

    parquet = pq.ParquetFile(parquet_path)
    total = parquet.metadata.num_rows
    existing = len(list(images_dir.glob("*.jpg"))) if images_dir.exists() else 0
    if existing >= total and not force:
        print(
            f"[COCO Keypoints] Ya hay {existing} imagenes en {images_dir}. "
            "Se omite la extraccion."
        )
        return

    images_dir.mkdir(parents=True, exist_ok=True)
    saved = skipped = 0
    for batch in parquet.iter_batches(
        batch_size=64, columns=["image_id", "image"]
    ):
        for row in batch.to_pylist():
            image = row.get("image") or {}
            suffix = Path(image.get("path") or "").suffix or ".jpg"
            target = images_dir / f"{int(row['image_id']):012d}{suffix}"
            if target.exists() and not force:
                skipped += 1
                continue
            data = image.get("bytes")
            if data is None:
                raise ValueError(
                    f"La imagen {row['image_id']} no tiene bytes embebidos."
                )
            target.write_bytes(data)
            saved += 1

    print(
        f"[COCO Keypoints] Imagenes guardadas: {saved}, ya existentes: {skipped}, "
        f"total: {len(list(images_dir.glob('*.jpg')))}."
    )


def download_split(load_dataset, repo_id, split, target, config=None, force=False):
    if target.exists() and not force:
        print(f"[{repo_id}] {target} ya existe. Se omite.")
        return

    label = f"{config}/{split}" if config else split
    print(f"[{repo_id}] Descargando {label}...")
    count = _download_parquet_split(repo_id, split, target, config)
    if count is None:
        print(
            f"[{repo_id}] No hay conversion Parquet para {label}; "
            "usando datasets.load_dataset (puede descargar otros splits)."
        )
        if config:
            dataset = load_dataset(repo_id, config, split=split)
        else:
            dataset = load_dataset(repo_id, split=split)
        dataset.to_parquet(str(target))
        count = len(dataset)

    print(f"[{repo_id}] {label}: {count} registros -> {target}")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Descarga los datasets de benchmark en configs/dataset."
    )
    parser.add_argument(
        "--datasets",
        nargs="+",
        default=["all"],
        choices=["all", "coco", *DATASET_TARGETS],
        help="Datasets a descargar (por defecto: all).",
    )
    parser.add_argument(
        "--extract-images",
        action=argparse.BooleanOptionalAction,
        default=True,
        help=(
            "Extrae las imagenes embebidas de COCO Keypoints a "
            "COCO_Keypoints/images/ (por defecto: si)."
        ),
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Sobrescribe archivos e imagenes ya descargados.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    selected = set(args.datasets)
    if "all" in selected:
        selected = {"coco", *DATASET_TARGETS}

    load_dataset = load_huggingface()

    if "coco" in selected:
        download_coco(load_dataset, force=args.force)

    for name, (repo_id, target_dir, splits) in DATASET_TARGETS.items():
        if name not in selected:
            continue
        for split, config in splits:
            download_split(
                load_dataset,
                repo_id,
                split,
                target_dir / f"{split}.parquet",
                config=config,
                force=args.force,
            )

    if "coco_keypoints" in selected and args.extract_images:
        extract_keypoints_images(
            COCO_KEYPOINTS_DIR / "val.parquet",
            COCO_KEYPOINTS_IMAGES_DIR,
            force=args.force,
        )


if __name__ == "__main__":
    main()
