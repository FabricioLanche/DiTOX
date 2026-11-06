class OptimizerHelper:
    """Pass catalogs and composed pipelines for the supported optimizers."""

    TVM_ISOLATION_DEPENDENCIES = {
        "AdjustMatmulOrder": (),
        "CanonicalizeBindings": (),
        "FoldBatchnormToConv2D": (),
        "FastMathTransform": (),
        "EliminateCommonSubexpr": (),
        "FuseTransposeMatmul": (),
        "InlinePrivateFunctions": (),
        "CombineParallelMatmul": ("ConvertToDataflow", "ExpandMatmulOfSum"),
        "ReorderPermuteDimsAfterConcat": (
            "ConvertToDataflow",
            "ExpandMatmulOfSum",
            "CombineParallelMatmul",
        ),
        "ReorderTakeAfterMatmul": (),
        "RemoveRedundantReshape": (),
        "ToMixedPrecision": ("ConvertToDataflow",),
        "FoldConstant": ("ConvertToDataflow",),
        "FuseOps": ("ConvertToDataflow",),
        "DataflowUseInplaceCalls": ("ConvertToDataflow",),
        "FuseTIR": (
            "ConvertToDataflow",
            "AnnotateTIROpPattern",
            "FuseOps",
        ),
        "SpecializePrimFuncBasedOnCallSite": (),
        "RewriteDataflowReshape": ("ConvertToDataflow",),
        "TopologicalSort": (),
        "RemoveUnusedOutputs": (),
        "RemoveUnusedParameters": (),
        "DeadCodeElimination": (),
        "LazyTransformParams": (),
        "StaticPlanBlockMemory": (),
        "KillAfterLastUse": (),
    }

    def __init__(self, target="onnx"):
        if target == "onnx":
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
            self.passes = [
                ("ConvertToDataflow", "DEPENDENCY"),                                # DEPENDENCY
                ("ToMixedPrecision", "OPTIMIZATION"),                               # OPTIMIZATION
                ("ExpandMatmulOfSum", "DEPENDENCY"),                                # DEPENDENCY
                ("AdjustMatmulOrder", "OPTIMIZATION"),                              # OPTIMIZATION
                ("CanonicalizeBindings", "OPTIMIZATION"),                           # OPTIMIZATION
                ("FoldBatchnormToConv2D", "OPTIMIZATION"),                          # OPTIMIZATION
                ("FastMathTransform", "OPTIMIZATION"),                              # OPTIMIZATION
                ("EliminateCommonSubexpr", "OPTIMIZATION"),                         # OPTIMIZATION
                ("FuseTransposeMatmul", "OPTIMIZATION"),                            # OPTIMIZATION
                ("InlinePrivateFunctions", "OPTIMIZATION"),                         # OPTIMIZATION
                ("CombineParallelMatmul", "OPTIMIZATION"),                          # OPTIMIZATION
                ("ReorderPermuteDimsAfterConcat", "OPTIMIZATION"),                  # OPTIMIZATION
                ("ReorderTakeAfterMatmul", "OPTIMIZATION"),                         # OPTIMIZATION
                ("RemoveRedundantReshape", "OPTIMIZATION"),                         # OPTIMIZATION
                ("LegalizeOps", "DEFAULT"),                                         # DEFAULT
                ("AnnotateTIROpPattern", "DEPENDENCY"),                             # DEPENDENCY
                ("FoldConstant", "OPTIMIZATION"),                                   # OPTIMIZATION
                ("FuseOps", "OPTIMIZATION"),                                        # OPTIMIZATION
                ("DataflowUseInplaceCalls", "OPTIMIZATION"),                        # OPTIMIZATION
                ("FuseTIR", "OPTIMIZATION"),                                        # OPTIMIZATION
                ("SpecializePrimFuncBasedOnCallSite", "OPTIMIZATION"),              # OPTIMIZATION
                ("RewriteDataflowReshape", "OPTIMIZATION"),                         # OPTIMIZATION
                ("TopologicalSort", "OPTIMIZATION"),                                # OPTIMIZATION
                ("RemoveUnusedOutputs", "OPTIMIZATION"),                            # OPTIMIZATION
                ("RemoveUnusedParameters", "OPTIMIZATION"),                         # OPTIMIZATION
                ("DeadCodeElimination", "OPTIMIZATION"),                            # OPTIMIZATION
                ("ToNonDataflow", "DEFAULT"),                                       # DEFAULT
                ("RemovePurityChecking", "DEFAULT"),                                # DEFAULT
                ("LazyTransformParams", "OPTIMIZATION"),                            # OPTIMIZATION
                ("CallTIRRewrite", "DEFAULT"),                                      # DEFAULT
                ("StaticPlanBlockMemory", "OPTIMIZATION"),                          # OPTIMIZATION
                ("LowerAllocTensor", "DEFAULT"),                                    # DEFAULT
                ("KillAfterLastUse", "OPTIMIZATION"),                               # OPTIMIZATION
                ("LowerRuntimeBuiltin", "DEFAULT"),                                 # DEFAULT
                ("ComputePrimValue", "DEFAULT"),                                    # DEFAULT
                ("VMShapeLower", "DEFAULT"),                                        # DEFAULT
                ("AttachGlobalSymbol", "DEFAULT"),                                  # DEFAULT
            ]
        else:
            raise ValueError(f"Unknown optimization target: {target}")

    def get_tvm_relax_pipeline(self):
        import tvm
        from tvm import relax

        return tvm.transform.Sequential([
            relax.backend.DispatchSampling(),           # DEFAULT
            relax.backend.DispatchSortScan(),           # DEFAULT
            *[
                getattr(relax.transform, name)()
                for name, _ in self.passes
            ],
        ])

    def get_tvm_isolation_dependencies(self, optimization):
        if optimization not in self.TVM_ISOLATION_DEPENDENCIES:
            raise ValueError(f"Unknown TVM optimization: {optimization}")
        return list(self.TVM_ISOLATION_DEPENDENCIES[optimization])

    def get_tvm_isolation_pipeline(
        self, optimization, dependencies=None, include_optimization=True
    ):
        import tvm
        from tvm import relax

        required = set(
            self.get_tvm_isolation_dependencies(optimization)
            if dependencies is None
            else dependencies
        )
        if include_optimization:
            required.add(optimization)

        selected_passes = [
            name
            for name, kind in self.passes
            if kind == "DEFAULT" or name in required
        ]
        return tvm.transform.Sequential([
            relax.backend.DispatchSampling(),
            relax.backend.DispatchSortScan(),
            *[getattr(relax.transform, name)() for name in selected_passes],
        ])

    def get_optimizer_passes(self, filter=None):
        if self.passes and isinstance(self.passes[0], tuple):
            passes = [
                name for name, kind in self.passes if kind == "OPTIMIZATION"
            ]
        else:
            passes = self.passes
        if filter is not None:
            return [p for p in passes if filter in p]
        return list(passes)
