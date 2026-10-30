import numpy as np

from evaluators.evalgenerator import EvaluationGenerator


class TVMRunner:

    def __init__(self, config, topK=10):
        self.config = config
        self.evaluation_generator = EvaluationGenerator()
        self.topK = topK
        self.virtual_machine = None
        self.device = None
        self.tensor = None
        self.input_names = None

    def evaluate(self, source_run_obj, target_run_obj, type=["classification"],
                 include_certainties=False, enable_kt_on_one_dim_tensor=True):
        return self.evaluation_generator.generate_objects_comparison(
            source_run_obj,
            target_run_obj,
            type,
            include_certainties,
            enable_kt_on_one_dim_tensor,
        )

    def compile_tvm_model(self, relax_model, target=None):
        import tvm
        from tvm import relax

        self.virtual_machine = None
        self.device = None
        self.tensor = None
        self.input_names = None

        try:
            import tvm_tirx
        except ImportError:
            tvm_tirx = None

        if tvm_tirx is not None:
            target_cls = tvm_tirx.target.Target
            cpu = tvm_tirx.cpu
            self.tensor = tvm_tirx.runtime.tensor
        else:
            target_cls = tvm.target.Target
            cpu = tvm.cpu
            self.tensor = tvm.runtime.tensor

        if target is None:
            target = self.config.get(
                "target",
                self.config.get("build", {}).get("target", "llvm"),
            )
        target = target_cls(target)
        executable = tvm.compile(
            relax_model,
            target=target,
            relax_pipeline=relax.get_default_pipeline(target),
        )
        device_id = self.config.get("device_id", 0)
        device_type = self.config.get("device_type", target.kind.name)
        if device_type in ("cpu", "llvm"):
            device = cpu(device_id)
        elif hasattr(tvm, "device"):
            device = tvm.device(device_type, device_id)
        else:
            raise RuntimeError(
                f"TVM runtime does not provide a device for target '{device_type}'."
            )

        virtual_machine = relax.VirtualMachine(executable, device)
        input_names = []
        for parameter in relax_model["main"].params:
            name = getattr(parameter, "name_hint", None) or getattr(
                parameter, "name", None
            )
            if name is None:
                raise RuntimeError("Unable to determine a Relax model input name.")
            input_names.append(name)
        self.virtual_machine = virtual_machine
        self.device = device
        self.input_names = input_names
        return virtual_machine

    def execute_tvm_model(self, inputs):
        if self.virtual_machine is None:
            raise RuntimeError("Compile a Relax model before executing it.")

        if isinstance(inputs, dict):
            missing_inputs = [name for name in self.input_names if name not in inputs]
            if missing_inputs:
                raise ValueError(f"Missing Relax model inputs: {missing_inputs}")
            unexpected_inputs = [name for name in inputs if name not in self.input_names]
            if unexpected_inputs:
                raise ValueError(f"Unexpected Relax model inputs: {unexpected_inputs}")
            input_values = [inputs[name] for name in self.input_names]
        elif isinstance(inputs, (list, tuple)):
            input_values = list(inputs)
        else:
            input_values = [inputs]

        if len(input_values) != len(self.input_names):
            raise ValueError(
                f"Expected {len(self.input_names)} inputs, received {len(input_values)}."
            )

        runtime_inputs = [
            self.tensor(np.ascontiguousarray(value), device=self.device)
            for value in input_values
        ]
        outputs = self.virtual_machine["main"](*runtime_inputs)
        if isinstance(outputs, (list, tuple)):
            output_values = outputs
        elif not hasattr(outputs, "numpy") and hasattr(outputs, "__iter__"):
            output_values = list(outputs)
        else:
            output_values = [outputs]
        return [
            np.asarray(output.numpy() if hasattr(output, "numpy") else output)
            for output in output_values
        ]

    def execute_single(self, inputs):
        return self.execute_tvm_model(inputs)