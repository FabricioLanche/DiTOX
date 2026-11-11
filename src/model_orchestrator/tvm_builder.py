import hashlib
import inspect
import json
import os
import platform
import tempfile
from pathlib import Path
from urllib.parse import quote


class TVMBuilder:
    """Build Relax models and cached base executables from ONNX models."""

    TARGET = "llvm"

    def __init__(self, compiled_cache_dir=None):
        self.compiled_cache_dir = (
            Path(compiled_cache_dir) if compiled_cache_dir is not None else None
        )

    @staticmethod
    def _input_names(relax_model):
        names = []
        for parameter in relax_model["main"].params:
            name = getattr(parameter, "name_hint", None) or getattr(
                parameter, "name", None
            )
            if name is None:
                raise RuntimeError("Unable to determine a Relax model input name.")
            names.append(name)
        return names

    def build_relax(self, onnx_model, shape_dict=None, dtype_dict=None):
        from tvm.relax.frontend.onnx import from_onnx

        return from_onnx(
            onnx_model,
            shape_dict=shape_dict,
            dtype_dict=dtype_dict,
        )

    @staticmethod
    def get_default_relax_pipeline():
        import tvm
        from tvm import relax

        return tvm.transform.Sequential([
            relax.backend.DispatchSampling(),
            relax.backend.DispatchSortScan(),
            relax.transform.LegalizeOps(),
            relax.transform.ToNonDataflow(),
            relax.transform.RemovePurityChecking(),
            relax.transform.CallTIRRewrite(),
            relax.transform.LowerAllocTensor(),
            relax.transform.LowerRuntimeBuiltin(),
            relax.transform.ComputePrimValue(),
            relax.transform.VMShapeLower(),
            relax.transform.AttachGlobalSymbol(),
        ])

    def build_base_artifacts(
        self,
        onnx_model,
        *,
        source_key,
        model_hash,
        shape_dict=None,
    ):
        """Return Relax IR, its input names, and a cached default executable."""
        import tvm

        relax_model = self.build_relax(onnx_model, shape_dict=shape_dict)
        input_names = self._input_names(relax_model)
        pipeline_signature = hashlib.sha256(
            inspect.getsource(self.get_default_relax_pipeline).encode("utf-8")
        ).hexdigest()
        cache_identity = {
            "source_key": source_key,
            "model_hash": model_hash,
            "shape_dict": shape_dict or {},
            "target": self.TARGET,
            "tvm_version": getattr(tvm, "__version__", "unknown"),
            "machine": platform.machine(),
            "pipeline_signature": pipeline_signature,
        }

        if self.compiled_cache_dir is None:
            executable = self._compile(
                relax_model, self.get_default_relax_pipeline()
            )
            return relax_model, input_names, executable

        self.compiled_cache_dir.mkdir(parents=True, exist_ok=True)
        cache_stem = quote(str(source_key), safe="._-")
        executable_path = self.compiled_cache_dir / f"{cache_stem}.so"
        metadata_path = self.compiled_cache_dir / f"{cache_stem}.json"

        if executable_path.is_file() and metadata_path.is_file():
            try:
                with metadata_path.open("r", encoding="utf-8") as metadata_file:
                    cached_identity = json.load(metadata_file)
                if cached_identity == cache_identity:
                    executable = tvm.runtime.load_module(str(executable_path))
                    print(f"Loaded cached TVM executable: {executable_path.name}")
                    return relax_model, input_names, executable
            except Exception as error:
                print(f"Ignoring invalid TVM executable cache entry: {error}")

        pipeline = self.get_default_relax_pipeline()
        executable = self._compile(relax_model, pipeline)
        temporary_path = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=self.compiled_cache_dir,
                prefix=f".{cache_stem}-",
                suffix=".so",
                delete=False,
            ) as temporary_file:
                temporary_path = Path(temporary_file.name)
            temporary_path.unlink()
            executable.export_library(str(temporary_path))
            os.replace(temporary_path, executable_path)
            with metadata_path.open("w", encoding="utf-8") as metadata_file:
                json.dump(cache_identity, metadata_file, indent=2, sort_keys=True)
            executable = tvm.runtime.load_module(str(executable_path))
        except Exception as error:
            print(f"Could not persist TVM executable cache: {error}")
            executable_path.unlink(missing_ok=True)
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

        return relax_model, input_names, executable

    def _compile(self, relax_model, relax_pipeline):
        import tvm

        return tvm.compile(
            relax_model,
            target=tvm.target.Target(self.TARGET),
            relax_pipeline=relax_pipeline,
        )
