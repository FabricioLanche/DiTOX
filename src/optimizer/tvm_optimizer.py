class TVMOptimizer:
    """Compose TVM Relax optimization pipelines and compile optimized executables."""

    PASSES = (
        ("ConvertToDataflow", "DEPENDENCY"),
        ("ToMixedPrecision", "OPTIMIZATION"),
        ("ExpandMatmulOfSum", "DEPENDENCY"),
        ("AdjustMatmulOrder", "OPTIMIZATION"),
        ("CanonicalizeBindings", "OPTIMIZATION"),
        ("FoldBatchnormToConv2D", "OPTIMIZATION"),
        ("FastMathTransform", "OPTIMIZATION"),
        ("EliminateCommonSubexpr", "OPTIMIZATION"),
        ("FuseTransposeMatmul", "OPTIMIZATION"),
        ("InlinePrivateFunctions", "OPTIMIZATION"),
        ("CombineParallelMatmul", "OPTIMIZATION"),
        ("ReorderPermuteDimsAfterConcat", "OPTIMIZATION"),
        ("ReorderTakeAfterMatmul", "OPTIMIZATION"),
        ("RemoveRedundantReshape", "OPTIMIZATION"),
        ("DataflowUseInplaceCalls", "OPTIMIZATION"),
        ("LegalizeOps", "DEFAULT"),
        ("AnnotateTIROpPattern", "DEPENDENCY"),
        ("FoldConstant", "OPTIMIZATION"),
        ("FuseOps", "OPTIMIZATION"),
        ("FuseTIR", "OPTIMIZATION"),
        ("SpecializePrimFuncBasedOnCallSite", "OPTIMIZATION"),
        ("RewriteDataflowReshape", "OPTIMIZATION"),
        ("TopologicalSort", "OPTIMIZATION"),
        ("RemoveUnusedOutputs", "OPTIMIZATION"),
        ("RemoveUnusedParameters", "OPTIMIZATION"),
        ("DeadCodeElimination", "OPTIMIZATION"),
        ("ToNonDataflow", "DEFAULT"),
        ("RemovePurityChecking", "DEFAULT"),
        ("LazyTransformParams", "OPTIMIZATION"),
        ("CallTIRRewrite", "DEFAULT"),
        ("StaticPlanBlockMemory", "OPTIMIZATION"),
        ("LowerAllocTensor", "DEFAULT"),
        ("KillAfterLastUse", "OPTIMIZATION"),
        ("LowerRuntimeBuiltin", "DEFAULT"),
        ("ComputePrimValue", "DEFAULT"),
        ("VMShapeLower", "DEFAULT"),
        ("AttachGlobalSymbol", "DEFAULT"),
    )

    DEPENDENCIES = {
        "AdjustMatmulOrder": (),
        "CanonicalizeBindings": (),
        "FoldBatchnormToConv2D": (),
        "FastMathTransform": (),
        "EliminateCommonSubexpr": (),
        "FuseTransposeMatmul": (),
        "InlinePrivateFunctions": (),
        "CombineParallelMatmul": ("ConvertToDataflow", "ExpandMatmulOfSum"),
        "ReorderPermuteDimsAfterConcat": (
            "ConvertToDataflow", "ExpandMatmulOfSum", "CombineParallelMatmul"
        ),
        "ReorderTakeAfterMatmul": (),
        "RemoveRedundantReshape": (),
        "ToMixedPrecision": ("ConvertToDataflow",),
        "FoldConstant": ("ConvertToDataflow",),
        "FuseOps": ("ConvertToDataflow",),
        "DataflowUseInplaceCalls": ("ConvertToDataflow",),
        "FuseTIR": ("ConvertToDataflow", "AnnotateTIROpPattern", "FuseOps"),
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

    def get_optimizer_passes(self, filter=None):
        optimizations = [name for name, kind in self.PASSES if kind == "OPTIMIZATION"]
        if filter is not None:
            optimizations = [name for name in optimizations if filter in name]
        return optimizations

    def get_isolation_dependencies(self, optimization):
        if optimization not in self.DEPENDENCIES:
            raise ValueError(f"Unknown TVM optimization: {optimization}")
        return list(self.DEPENDENCIES[optimization])

    @staticmethod
    def _compose_pipeline(pass_names):
        import tvm
        from tvm import relax

        return tvm.transform.Sequential([
            relax.backend.DispatchSampling(),
            relax.backend.DispatchSortScan(),
            *[getattr(relax.transform, name)() for name in pass_names],
        ])

    def get_optimized_pipeline(self):
        return self._compose_pipeline([name for name, _ in self.PASSES])

    def get_isolation_pipeline(
        self, optimization, dependencies, include_optimization=True
    ):
        required = set(dependencies)
        if include_optimization:
            required.add(optimization)
        selected_passes = [
            name
            for name, kind in self.PASSES
            if kind == "DEFAULT" or name in required
        ]
        return self._compose_pipeline(selected_passes)

    @staticmethod
    def generate_executable(relax_model, relax_pipeline, target="llvm"):
        """Compile a Relax model with its selected optimization pipeline."""
        import tvm

        return tvm.compile(
            relax_model,
            target=tvm.target.Target(target),
            relax_pipeline=relax_pipeline,
        )
