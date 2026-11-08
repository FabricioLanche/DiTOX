class OptimizerHelper:
    """Pass catalogs for the supported optimizers."""

    def __init__(self, target="onnx"):
        if target == "onnx":
            self.target = "onnx"
            self.passes = ["adjust_add", "rename_input_output", "set_unique_name_for_nodes", \
                "nop", "eliminate_nop_cast", "eliminate_nop_dropout", "eliminate_nop_flatten", \
                "extract_constant_to_initializer", "eliminate_consecutive_idempotent_ops", \
                "eliminate_if_with_const_cond", "eliminate_nop_monotone_argmax", "eliminate_nop_pad", \
                "eliminate_nop_concat", "eliminate_nop_split", "eliminate_nop_expand", "eliminate_shape_gather", \
                "eliminate_slice_after_shape", "eliminate_nop_transpose", "fuse_add_bias_into_conv", "fuse_bn_into_conv", \
                "fuse_consecutive_concats", "fuse_consecutive_log_softmax", "fuse_consecutive_reduce_unsqueeze", "fuse_consecutive_squeezes", \
                "fuse_consecutive_transposes", "fuse_matmul_add_bias_into_gemm", "fuse_pad_into_conv", "fuse_pad_into_pool", "fuse_transpose_into_gemm", \
                "replace_einsum_with_matmul", "lift_lexical_references", "split_init", "split_predict", "fuse_concat_into_reshape", \
                "eliminate_nop_reshape", "eliminate_nop_with_unit", "eliminate_common_subexpression", "fuse_qkv", "fuse_consecutive_unsqueezes", \
                "eliminate_deadend", "eliminate_identity", "eliminate_shape_op", "fuse_consecutive_slices", "eliminate_unused_initializer", \
                "eliminate_duplicate_initializer", "adjust_slice_and_matmul", "rewrite_input_dtype"]
        elif target == "tvm":
            self.target = "tvm"
            self.dependencies = {
                "CombineParallelMatmul": [
                    "ConvertToDataflow",
                    "ExpandMatmulOfSum",
                ],
                "ReorderPermuteDimsAfterConcat": [
                    "ConvertToDataflow",
                    "ExpandMatmulOfSum",
                    "CombineParallelMatmul",
                ],
                "ToMixedPrecision": [
                    "ConvertToDataflow"
                ],
                "FoldConstant": [
                    "ConvertToDataflow"
                ],
                "FuseOps": [
                    "ConvertToDataflow",
                    "AnnotateTIROpPattern"
                ],
                "DataflowUseInplaceCalls": [
                    "ConvertToDataflow"
                ],
                "FuseTIR": [
                    "ConvertToDataflow",
                    "AnnotateTIROpPattern",
                    "FuseOps",
                ],
                "RewriteDataflowReshape": [
                    "ConvertToDataflow"
                ]
            }
            self.passes = [
                "ToMixedPrecision",
                "AdjustMatmulOrder",
                "CanonicalizeBindings",
                "FoldBatchnormToConv2D",
                "FastMathTransform",
                "EliminateCommonSubexpr",
                "FuseTransposeMatmul",
                "InlinePrivateFunctions",
                "CombineParallelMatmul",
                "ReorderPermuteDimsAfterConcat",
                "ReorderTakeAfterMatmul",
                "RemoveRedundantReshape",
                "DataflowUseInplaceCalls",
                "FoldConstant",
                "FuseOps",
                "FuseTIR",
                "SpecializePrimFuncBasedOnCallSite",
                "RewriteDataflowReshape",
                "TopologicalSort",
                "RemoveUnusedOutputs",
                "RemoveUnusedParameters",
                "DeadCodeElimination",
                "LazyTransformParams",
                "StaticPlanBlockMemory",
                "KillAfterLastUse",
            ]
        else:
            raise ValueError(f"Unknown optimization target: {target}")

    def get_optimizer_passes(self, filter=None):
        if filter is not None:
            return [p for p in self.passes if filter in p]
        return list(self.passes)
