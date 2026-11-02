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

    def compile_tvm_model(self, relax_model):
        import tvm
        from tvm import relax

        self.virtual_machine = None
        self.device = None
        self.tensor = None
        self.input_names = None

        target_cls = tvm.target.Target
        cpu = tvm.cpu
        self.tensor = tvm.runtime.tensor

        target = target_cls("llvm")
        executable = tvm.compile(
            relax_model,
            target=target,
            relax_pipeline=relax.get_default_pipeline(target),
        )
        device_id = self.config.get("device_id", 0)
        device = cpu(device_id)

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

    def execute_relax_model(self, relax_model, images_paths, config, print_percentage=True, include_certainties=False):
        from pathlib import Path
        from PIL import Image
        from scipy.special import softmax
        from processors.model_preprocessor import ModelPreprocessor

        self.compile_tvm_model(relax_model)

        has_symbolic_input = False
        input_dimension = config.get("input_dimension", [224, 224])
        if len(input_dimension) == 0:
            input_dimension = [224, 224]
            has_symbolic_input = True

        preprocessing_data = {
            "input": config.get("input_shape", [1, 3, 224, 224]),
            "input_dimension": input_dimension,
            "library": None
        }
        model_preprocessor = ModelPreprocessor(preprocessing_data)

        output_data = {}
        count = 0
        images_length = len(images_paths)
        step = (images_length // 4) if images_length > 10 else images_length

        input_name = config.get("input_name", self.input_names[0] if self.input_names else "data")

        for img_path in images_paths:
            if print_percentage and step > 0 and count % step == 0:
                print("Complete: " + str((count // step) * 25) + "%")
            count += 1

            img_name = Path(img_path).name
            img = Image.open(img_path)

            input_shape = config.get("input_shape", [1, 3, 224, 224])
            if len(input_shape) > 3 and (input_shape[1] == 1 or input_shape[3] == 1):
                img = img.convert("L")
            else:
                if img.mode in ("L", "BGR"):
                    img = img.convert("RGB")

            img = img.resize(input_dimension)
            img = model_preprocessor.preprocess(config.get("model_name", ""), img, True)

            if len(input_shape) < len(img.shape):
                img = np.squeeze(img)

            input_dict = {input_name: img.astype(np.float32)}
            outputs = self.execute_tvm_model(input_dict)

            if len(outputs) == 1 and np.array(outputs).ndim == 3:
                output = softmax(outputs)
                output = np.squeeze(output)
                ranks = np.argsort(output)[::-1]
                extracted_ranks = ranks[0:self.topK]
                if include_certainties:
                    output_data[img_name] = [(rank, str(output[rank])) for rank in extracted_ranks.tolist()]
                else:
                    output_data[img_name] = extracted_ranks.tolist()
            else:
                output_data[img_name] = outputs

        return output_data