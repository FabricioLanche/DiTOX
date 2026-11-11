from tvm.relax.frontend.onnx import from_onnx

class TVMBuilder:

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

    @staticmethod
    def get_optimized_relax_pipeline():
        from src.optimizer.optimizer_helper import OptimizerHelper

        helper = OptimizerHelper(target="tvm")
        return helper.get_tvm_relax_pipeline()
    
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

