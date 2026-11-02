from tvm.relax.frontend.onnx import from_onnx

class TVMBuilder:

    LLVM_RELAX_PIPELINE = [
        "DispatchSampling",
        "DispatchSortScan",
        "LegalizeOps",
        "ToNonDataflow",
        "RemovePurityChecking",
        "CallTIRRewrite",
        "LowerAllocTensor",
        "LowerRuntimeBuiltin",
        "ComputePrimValue",
        "VMShapeLower",
        "AttachGlobalSymbol",
    ]

    @staticmethod
    def get_llvm_relax_pipeline():
        import tvm
        from tvm import relax

        pipeline_passes = []
        unavailable_passes = []
        for pass_name in TVMBuilder.LLVM_RELAX_PIPELINE:
            pass_factory = getattr(relax.transform, pass_name, None)
            if pass_factory is None:
                unavailable_passes.append(pass_name)
                continue
            pipeline_passes.append(pass_factory())

        if unavailable_passes:
            print(
                "TVM pipeline passes unavailable in this installed version "
                f"(skipped): {', '.join(unavailable_passes)}"
            )

        return tvm.transform.Sequential(pipeline_passes)
    
    def build_relax(self, onnx_model, shape_dict=None, dtype_dict=None):
        return from_onnx(
            onnx_model,
            shape_dict=shape_dict,
            dtype_dict=dtype_dict,
        )

    def optimize_relax(self, relax_mod, pass_name, passes_list=None):
        from tvm import relax
        if pass_name == "all":
            passes = passes_list or []
            opt_mod = relax_mod
            for p in passes:
                if hasattr(relax.transform, p):
                    try:
                        opt_mod = getattr(relax.transform, p)()(opt_mod)
                    except Exception as e:
                        print(f"Warning: Relax pass {p} failed: {e}")
            return opt_mod
        else:
            if hasattr(relax.transform, pass_name):
                return getattr(relax.transform, pass_name)()(relax_mod)
            raise ValueError(f"Unknown TVM Relax pass: {pass_name}")

