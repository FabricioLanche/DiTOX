import numpy as np


class TextRunner:
    """Generate text from causal LMs and compare outputs with BLEU."""

    def __init__(self, config=None):
        self.config = config or {}
        self.tokenizer_name = self.config.get("tokenizer", "gpt2")
        self.max_length = int(self.config.get("max_length", 128))
        self.temperature = float(self.config.get("temperature", 1.0))
        self._tokenizer = None

    @property
    def tokenizer(self):
        if self._tokenizer is None:
            from transformers import GPT2Tokenizer

            tokenizer = GPT2Tokenizer.from_pretrained(self.tokenizer_name)
            tokenizer.pad_token = tokenizer.eos_token
            self._tokenizer = tokenizer
        return self._tokenizer

    def create_session(self, model):
        import onnxruntime as ort

        return ort.InferenceSession(
            model.SerializeToString(), providers=["CPUExecutionProvider"]
        )

    def generate(self, session, prompt):
        import torch

        inputs = self.tokenizer(prompt, return_tensors="np", padding=False)
        input_ids = np.expand_dims(inputs["input_ids"].astype(np.int64), axis=0)
        input_name = session.get_inputs()[0].name
        output_name = session.get_outputs()[0].name
        generated_tokens = []

        for _ in range(self.max_length):
            outputs = session.run([output_name], {input_name: input_ids})
            logits = torch.tensor(outputs[0]).squeeze(0)[:, -1, :]
            logits /= self.temperature
            probs = torch.nn.functional.softmax(logits, dim=-1)
            next_token = torch.argmax(probs, dim=-1)
            if next_token.item() == self.tokenizer.eos_token_id:
                break
            generated_tokens.append(next_token.item())
            step = np.array(next_token.numpy().reshape(1, 1, 1))
            input_ids = np.concatenate([input_ids, step], axis=-1)

        return self.tokenizer.decode(
            generated_tokens,
            skip_special_tokens=True,
            clean_up_tokenization_spaces=True,
        )

    def execute_text_model(self, model, prompts, config=None):
        session = self.create_session(model)
        return {index: self.generate(session, prompt) for index, prompt in enumerate(prompts)}

    @staticmethod
    def _fallback_bleu(prediction, reference, max_order=4):
        from collections import Counter

        if not prediction:
            return 0.0
        precisions = []
        for order in range(1, max_order + 1):
            pred_counts = Counter(
                tuple(prediction[i:i + order])
                for i in range(len(prediction) - order + 1)
            )
            ref_counts = Counter(
                tuple(reference[i:i + order])
                for i in range(len(reference) - order + 1)
            )
            matches = sum(min(c, ref_counts[g]) for g, c in pred_counts.items())
            total = max(len(prediction) - order + 1, 0)
            precisions.append((matches + 1) / (total + 1))
        brevity = min(1.0, len(prediction) / max(len(reference), 1))
        return brevity * float(np.prod(precisions)) ** (1.0 / max_order)

    def _sentence_bleu(self, prediction, reference):
        try:
            from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu

            return sentence_bleu(
                [reference], prediction, smoothing_function=SmoothingFunction().method4
            )
        except ImportError:
            return self._fallback_bleu(prediction, reference)

    def evaluate(self, base_outputs, optimized_outputs):
        scores = []
        for index, base_text in base_outputs.items():
            optimized_text = optimized_outputs.get(index, "")
            prediction = base_text.split()
            reference = optimized_text.split()
            scores.append(self._sentence_bleu(prediction, reference))
        if not scores:
            return {"mean_bleu": 0.0, "median_bleu": 0.0, "scores": []}
        return {
            "mean_bleu": float(np.mean(scores)),
            "median_bleu": float(np.median(scores)),
            "scores": [float(score) for score in scores],
        }
