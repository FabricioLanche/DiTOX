from pathlib import Path
import tempfile

import numpy as np
from PIL import Image

from src.runner.preprocessing.model_preprocessor import ModelPreprocessor


class PreparedImageInputs:
    """Preprocess an image batch once and keep its tensors in a temporary memmap."""

    def __init__(self, images_paths, config, subbatch_size=32):
        self.images_paths = list(images_paths)
        self._indices = {
            Path(image_path).name: index
            for index, image_path in enumerate(self.images_paths)
        }
        self._temporary_directory = tempfile.TemporaryDirectory(
            prefix="ditox-preprocessed-"
        )
        self._array = None
        self._prepare(config, max(1, int(subbatch_size)))

    def _preprocess_image(self, image_path, config, model_preprocessor):
        input_dimension = config.get("input_dimension", [224, 224])
        if not input_dimension:
            input_dimension = [224, 224]
        input_shape = config.get("input_shape", [1, 3, 224, 224])

        with Image.open(image_path) as source_image:
            image = source_image.copy()

        if len(input_shape) > 3 and (
            input_shape[1] == 1 or input_shape[3] == 1
        ):
            image = image.convert("L")
        elif image.mode in ("L", "BGR"):
            image = image.convert("RGB")

        image = image.resize(input_dimension)
        image = model_preprocessor.preprocess(
            config.get("model_name", ""), image, True
        )

        if len(input_shape) < len(image.shape):
            image = np.squeeze(image)
        return np.asarray(image, dtype=np.float32)

    def _prepare(self, config, subbatch_size):
        input_dimension = config.get("input_dimension", [224, 224])
        if not input_dimension:
            input_dimension = [224, 224]
        preprocessing_data = {
            "input": config.get("input_shape", [1, 3, 224, 224]),
            "input_dimension": input_dimension,
            "library": None,
        }
        model_preprocessor = ModelPreprocessor(preprocessing_data)
        array_path = Path(self._temporary_directory.name) / "inputs.npy"

        for start in range(0, len(self.images_paths), subbatch_size):
            stop = min(start + subbatch_size, len(self.images_paths))
            prepared_subbatch = [
                self._preprocess_image(path, config, model_preprocessor)
                for path in self.images_paths[start:stop]
            ]

            if self._array is None:
                first = prepared_subbatch[0]
                self._array = np.lib.format.open_memmap(
                    array_path,
                    mode="w+",
                    dtype=first.dtype,
                    shape=(len(self.images_paths), *first.shape),
                )

            for offset, image in enumerate(prepared_subbatch):
                index = start + offset
                if image.shape != self._array.shape[1:]:
                    raise ValueError(
                        "Preprocessed image shapes differ within one model batch: "
                        f"expected {self._array.shape[1:]}, received {image.shape}."
                    )
                self._array[index] = image

            del prepared_subbatch

        if self._array is not None:
            self._array.flush()

    def get(self, image_path):
        if self._array is None:
            raise RuntimeError("No prepared image inputs are available.")
        image_name = Path(image_path).name
        try:
            return self._array[self._indices[image_name]]
        except KeyError as error:
            raise KeyError(f"Image was not part of the prepared batch: {image_name}") from error

    def close(self):
        if self._array is not None:
            self._array.flush()
            self._array = None
        if self._temporary_directory is not None:
            self._temporary_directory.cleanup()
            self._temporary_directory = None
