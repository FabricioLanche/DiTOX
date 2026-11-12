from pathlib import Path
from io import BytesIO

import numpy as np

_FORMATS = {
    ".parquet": "parquet",
    ".json": "json",
    ".jsonl": "json",
    ".csv": "csv",
}


class DatasetInputProvider:
    """Load dataset rows from the local benchmark files or Hugging Face."""
    def __init__(self, config=None):
        self.config = config or {}
        self.dataset_name = self.config.get("dataset", "squad_v2")
        self.split = self.config.get("split", "validation")

    def _resolve_local_path(self):
        path = Path(self.dataset_name).expanduser()
        if not path.is_absolute() and not path.exists():
            repo_root = Path(__file__).resolve().parents[3]
            candidate = repo_root / path
            if candidate.exists():
                path = candidate
        if path.is_dir():
            for extension in _FORMATS:
                candidate = path / f"{self.split}{extension}"
                if candidate.exists():
                    return candidate
            raise FileNotFoundError(
                f"No se encontro {self.split}.parquet/.json/.csv en {path}"
            )
        return path if path.is_file() else None

    def _load_dataset(self, load_dataset):
        local_path = self._resolve_local_path()
        if local_path is not None:
            data_format = _FORMATS.get(local_path.suffix.lower())
            if data_format is None:
                raise ValueError(
                    f"Formato de dataset no soportado: {local_path.suffix}"
                )
            return load_dataset(
                data_format, data_files=str(local_path), split="train"
            )
        return load_dataset(self.dataset_name, split=self.split)

    def load_rows(self):
        from datasets import load_dataset

        dataset = self._load_dataset(load_dataset)
        return list(dataset)

    @staticmethod
    def load_pose_samples(parquet_path, images_dir, limit=None):
        """Read COCO Keypoints rows and pair annotations with extracted images."""
        import pyarrow.parquet as pq
        from PIL import Image

        images_dir = Path(images_dir)
        records = []
        parquet = pq.ParquetFile(parquet_path)
        for batch in parquet.iter_batches(
            batch_size=64, columns=["image_id", "keypoints", "bboxes"]
        ):
            for row in batch.to_pylist():
                candidates = []
                for index, person in enumerate(row.get("keypoints") or []):
                    points = np.asarray(person, dtype=np.float32).reshape(-1, 3)
                    visible = points[:, 2] > 0
                    if not np.any(visible):
                        continue
                    boxes = row.get("bboxes") or []
                    box = np.asarray(boxes[index], dtype=np.float32).reshape(-1) if index < len(boxes) else np.asarray([])
                    valid_box = (
                        box.size >= 4
                        and np.isfinite(box[:4]).all()
                        and box[2] > 0
                        and box[3] > 0
                    )
                    if valid_box:
                        scale = float(np.hypot(box[2], box[3]))
                        person_box = box[:4]
                    else:
                        visible_xy = points[visible, :2]
                        bounds_min = visible_xy.min(0)
                        bounds_size = np.maximum(visible_xy.max(0) - bounds_min, 1.0)
                        scale = float(np.linalg.norm(bounds_size))
                        person_box = np.r_[bounds_min, bounds_size]
                    candidates.append((
                        int(visible.sum()), points, max(scale, 1e-6),
                        person_box,
                    ))
                if not candidates:
                    continue
                _, points, scale, bbox = max(candidates, key=lambda item: item[0])
                image_id = int(row["image_id"])
                image_path = images_dir / f"{image_id:012d}.jpg"
                if not image_path.is_file():
                    image_path = images_dir / f"{image_id:012d}.png"
                if not image_path.is_file():
                    continue
                with Image.open(image_path) as image:
                    image_size = (image.height, image.width)
                records.append({
                    "id": str(image_id),
                    "image_path": str(image_path),
                    "image_size": image_size,
                    "reference_keypoints": points,
                    "scale": scale,
                    "bbox": bbox.tolist(),
                })
                if limit is not None and len(records) >= int(limit):
                    return records
        return records

    @staticmethod
    def load_speech_samples(parquet_path, limit=None):
        """Decode local LibriSpeech audio records while preserving references."""
        import pyarrow.parquet as pq
        import soundfile as sf

        records = []
        parquet = pq.ParquetFile(parquet_path)
        for batch in parquet.iter_batches(
            batch_size=16, columns=["id", "audio", "text"]
        ):
            for row in batch.to_pylist():
                audio_record = row.get("audio") or {}
                encoded = audio_record.get("bytes")
                if encoded is not None:
                    audio, rate = sf.read(BytesIO(encoded), dtype="float32")
                else:
                    audio_path = audio_record.get("path")
                    if not audio_path or not Path(audio_path).is_file():
                        continue
                    audio, rate = sf.read(audio_path, dtype="float32")
                records.append({
                    "id": str(row.get("id", len(records))),
                    "audio": audio,
                    "sample_rate": int(rate),
                    "reference": str(row.get("text", "")),
                })
                if limit is not None and len(records) >= int(limit):
                    return records
        return records


class TextInputProvider(DatasetInputProvider):
    """Load and format text prompts used by text backends."""

    DEFAULT_TEMPLATE = "Context: {context} Question: {question}"

    def __init__(self, config=None):
        super().__init__(config)
        self.template = self.config.get("prompt_template", self.DEFAULT_TEMPLATE)
        self._prompts = None

    def load(self):
        if self._prompts is not None:
            return self._prompts
        prompts = []
        for row in self.load_rows():
            try:
                prompts.append(self.template.format(**row))
            except (KeyError, IndexError):
                prompts.append(str(row))
        self._prompts = prompts
        return self._prompts
