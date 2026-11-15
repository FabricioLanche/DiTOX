import atexit
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


class ONNXOptimizer:
    """Run ONNX Optimizer passes and expose its available pass catalog."""

    PASSES = [
        "adjust_add", "rename_input_output", "set_unique_name_for_nodes",
        "nop", "eliminate_nop_cast", "eliminate_nop_dropout", "eliminate_nop_flatten",
        "extract_constant_to_initializer", "eliminate_consecutive_idempotent_ops",
        "eliminate_if_with_const_cond", "eliminate_nop_monotone_argmax", "eliminate_nop_pad",
        "eliminate_nop_concat", "eliminate_nop_split", "eliminate_nop_expand", "eliminate_shape_gather",
        "eliminate_slice_after_shape", "eliminate_nop_transpose", "fuse_add_bias_into_conv", "fuse_bn_into_conv",
        "fuse_consecutive_concats", "fuse_consecutive_log_softmax", "fuse_consecutive_reduce_unsqueeze", "fuse_consecutive_squeezes",
        "fuse_consecutive_transposes", "fuse_matmul_add_bias_into_gemm", "fuse_pad_into_conv", "fuse_pad_into_pool", "fuse_transpose_into_gemm",
        "replace_einsum_with_matmul", "lift_lexical_references", "split_init", "split_predict", "fuse_concat_into_reshape",
        "eliminate_nop_reshape", "eliminate_nop_with_unit", "eliminate_common_subexpression", "fuse_qkv", "fuse_consecutive_unsqueezes",
        "eliminate_deadend", "eliminate_identity", "eliminate_shape_op", "fuse_consecutive_slices", "eliminate_unused_initializer",
        "eliminate_duplicate_initializer", "adjust_slice_and_matmul", "rewrite_input_dtype",
    ]

    def __init__(self):
        self._sanitized_models = {}
        self._sanitized_directory = None

    def _sanitized_model_path(self, model_path):
        import onnx

        path = Path(model_path)
        cache_key = str(path.resolve())
        cached = self._sanitized_models.get(cache_key)
        if cached is not None and cached.is_file():
            return cached

        model = onnx.load(str(path))
        unique_metadata = {}
        for prop in model.metadata_props:
            unique_metadata.setdefault(prop.key, prop.value)
        if len(unique_metadata) == len(model.metadata_props):
            return path

        if self._sanitized_directory is None:
            self._sanitized_directory = Path(
                tempfile.mkdtemp(prefix="ditox-onnx-")
            )
            atexit.register(
                shutil.rmtree, self._sanitized_directory, ignore_errors=True
            )
        with tempfile.NamedTemporaryFile(
            dir=self._sanitized_directory, suffix=".onnx", delete=False
        ) as temporary_file:
            sanitized_path = Path(temporary_file.name)

        model.ClearField("metadata_props")
        for key, value in unique_metadata.items():
            prop = model.metadata_props.add()
            prop.key = key
            prop.value = value
        onnx.save(model, str(sanitized_path))
        self._sanitized_models[cache_key] = sanitized_path
        return sanitized_path

    def get_optimizer_passes(self, filter=None):
        if filter is None:
            return list(self.PASSES)
        return [optimization for optimization in self.PASSES if filter in optimization]

    def optimize_model(self, model_path, output_path, optimization=None):
        model_path = self._sanitized_model_path(model_path)
        command = [sys.executable, "-m", "onnxoptimizer", str(model_path), str(output_path)]
        if optimization and optimization != "all":
            command.extend(["-p", optimization])
        return subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            check=False,
        )
