
class OptimizerHelper():

    def __init__(self, optimizer="ort"):
        if (optimizer == "ort"):
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

        elif (optimizer == "tvmr"):
            self.passes = [
                "NormalizeGlobalVar",
                "Normalize",
                "ConvertToDataflow",
                "ExpandMatmulOfSum",
                "CombineParallelMatmul",
                "ReorderPermuteDimsAfterConcat",
                "ReorderTakeAfterMatmul",
                "FoldBatchnormToConv2D",
                "DecomposeOpsForInference",
                "FuseTransposeMatmul",
                "RemoveRedundantReshape",
                "FoldConstant",
                "EliminateCommonSubexpr",
                "DeadCodeElimination",
                "RemoveUnusedParameters",
                "RemoveUnusedOutputs",
                "ComputePrimValue",
                "Normalize",
            ]

    def get_optimizer_passes(self, filter=None):

        if filter is not None:

            return [p for p in self.passes if filter in p]

        return self.passes

    def apply_tvm_passes(self, relax_model, pass_names, target="llvm"):
        import tvm
        from tvm import relax

        try:
            import tvm_tirx
        except ImportError:
            tvm_tirx = None

        if tvm_tirx is not None:
            target_cls = tvm_tirx.target.Target
            pass_context = tvm_tirx.ir.transform.PassContext
        else:
            target_cls = tvm.target.Target
            pass_context = tvm.ir.transform.PassContext

        target = target_cls(target)
        with target, pass_context(opt_level=2):
            for pass_name in pass_names:
                pass_factory = getattr(relax.transform, pass_name, None)
                if pass_factory is None:
                    raise ValueError(
                        f"TVM Relax does not provide the configured pass "
                        f"'{pass_name}'."
                    )
                relax_model = pass_factory()(relax_model)

        return relax_model
