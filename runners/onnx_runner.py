import onnx
import onnxruntime as ort
import numpy as np

from scipy.special import softmax

from processors.model_preprocessor import ModelPreprocessor
from evaluators.evalgenerator import EvaluationGenerator

from pathlib import Path
from PIL import Image

class ONNXRunner:

    def __init__(self, config, topK=10):
        self.evaluation_generator = EvaluationGenerator()
        self.topK = topK

    def evaluate(self, source_run_obj, target_run_obj, type=["classification"], include_certainties=False, enable_kt_on_one_dim_tensor=True):
        return self.evaluation_generator.generate_objects_comparison(source_run_obj, target_run_obj, type, include_certainties, enable_kt_on_one_dim_tensor)

    def execute_and_evaluate_single_model(self, onnx_model, run_obj, image_path, config, include_certainties=False):
        image_obj = self.execute_onnx_model(onnx_model, [image_path], config, print_percentage=False, include_certainties=include_certainties)
        image_name = list(image_obj.keys())[0]
        return self.evaluate(run_obj, image_obj, include_certainties)["images"][image_name]

    def execute_and_evaluate_single(self, onnx_path, run_obj, image_path, config, include_certainties=False):
        image_obj = self.execute_onnx_path(onnx_path, [image_path], config, print_percentage=False, include_certainties=include_certainties)
        image_name = list(image_obj.keys())[0]
        return self.evaluate(run_obj, image_obj, include_certainties)["images"][image_name]

    def evaluate_single(self, run_obj, image_obj, include_certainties=False):
        # Return single evaluation.
        image_name = list(image_obj.keys())[0]
        return self.evaluate(run_obj, image_obj, include_certainties)["images"][image_name]        
 
    def execute_single(self, onnx_path, image_path, config, include_certainties=False):
        # Execute and return for single image.
        return self.execute_onnx_path(onnx_path, [image_path], config, include_certainties)

    def execute_onnx_path(self, onnx_path, images_paths, config, image_names=None, print_percentage=True, include_certainties=False): 
        onnx_model = onnx.load(onnx_path)
        return self.execute_onnx_model(onnx_model, images_paths, config, image_names, print_percentage, include_certainties)

    def get_nodes_containing_input(self, base_model, input_name):

        base_nodes = base_model.graph.node
        nodes_found = []
        for base_node in base_nodes:
            if input_name in base_node.input:
                nodes_found.append(base_node)
        return nodes_found


    def prepare_onnx_inputs(self, onnx_model, images_paths, config):
        has_symbolic_input = False
        input_dimension = config["input_dimension"]
        if len(input_dimension) == 0:
            input_dimension = [224, 224]
            has_symbolic_input = True
        
        self.preprocessing_data = {
            "input": config["input_shape"],
            "input_dimension": input_dimension,
            "library": None
        }

        # Best effort approach for symbolic dimensions.
        # Set library to None, so that the name is utilized for preprocessing selection.
        model_preprocessor = ModelPreprocessor(self.preprocessing_data)
        prepared_inputs = {}
        for img_path in images_paths:
            img_name = Path(img_path).name
            img = Image.open(img_path)

            # Convert monochrome to RGB.
            if (len(config["input_shape"]) > 3 and \
                (config["input_shape"][1] == 1 or config["input_shape"][3] == 1)):
                img = img.convert("L")
            else:
                if(img.mode == "L" or img.mode == "BGR"):
                    img = img.convert("RGB")
                

            img = img.resize(input_dimension)
            img = model_preprocessor.preprocess(config["model_name"], img, True)

            input_name = onnx_model.graph.input[0].name if "input_name" not in config else config["input_name"]
            shape = onnx_model.graph.input[0].type.tensor_type.shape.dim
            if (len(shape) < len(img.shape)):
                img = np.squeeze(img)
            
            input_obj = {input_name: img.astype(np.uint8 if has_symbolic_input else np.float32)}
            if len(onnx_model.graph.input) == 2:
                input_obj["image_shape"] = [[224.0, 224.0]]
            prepared_inputs[img_name] = input_obj

        return prepared_inputs

    def format_outputs(self, output, include_certainties=False):
        if len(output) == 1 and np.array(output).ndim == 3:
            output = softmax(output)
            output = np.squeeze(output)
            ranks = np.argsort(output)[::-1]
            extracted_ranks = ranks[0:self.topK]
            if include_certainties:
                return [(rank, str(output[rank])) for rank in extracted_ranks.tolist()]
            return extracted_ranks.tolist()
        return output

    def execute_onnx_model(self, onnx_model, images_paths, config, image_names=None,
                           print_percentage=True, include_certainties=False,
                           prepared_inputs=None):
        if prepared_inputs is None:
            prepared_inputs = self.prepare_onnx_inputs(onnx_model, images_paths, config)

        sess_options = ort.SessionOptions()
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_DISABLE_ALL
        ort_sess = ort.InferenceSession(
            onnx_model.SerializeToString(),
            sess_options=sess_options,
            providers=['CPUExecutionProvider'],
        )

        output_data = {}
        images_length = len(images_paths)
        step = (images_length // 4) if images_length > 10 else images_length

        for count, img_path in enumerate(images_paths):
            if print_percentage and count % step == 0:
                print("Complete: " + str((count // step) * 25) + "%")

            img_name = Path(img_path).name
            output = ort_sess.run(None, prepared_inputs[img_name])
            output_data[img_name] = self.format_outputs(output, include_certainties)

        return output_data
    