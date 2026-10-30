class TVMBuilder:

    def build_relax(self, onnx_model, shape_dict=None, dtype_dict=None):
        from tvm.relax.frontend.onnx import from_onnx

        return from_onnx(
            onnx_model,
            shape_dict=shape_dict,
            dtype_dict=dtype_dict,
        )
