import numpy as np


_TASK_ALIASES = {
    "generation": "generation",
    "text_generation": "generation",
    "causal_lm": "generation",
    "sentiment": "classification",
    "classification": "classification",
    "text_classification": "classification",
    "qa": "question_answering",
    "question_answering": "question_answering",
    "question-answering": "question_answering",
    "squad": "question_answering",
    "summarization": "summarization",
    "summarisation": "summarization",
    "encoder": "summarization",
    "forward": "forward",
}

_DEFAULT_TOKENIZERS = {
    "generation": "gpt2",
    "question_answering": "bert-base-uncased",
    "classification": "roberta-base",
    "summarization": "t5-base",
    "forward": "bert-base-uncased",
}


def _normalize_task(value):
    if not value:
        return None
    return _TASK_ALIASES.get(str(value).strip().lower())


class TextRunner:
    """Run generation and encoder/classification text models on dataset samples."""

    def __init__(self, config=None):
        self.config = config or {}
        self.task = _normalize_task(self.config.get("task"))
        self.tokenizer_name = self.config.get("tokenizer")
        self.max_length = int(self.config.get("max_length", 128))
        self.temperature = float(self.config.get("temperature", 1.0))
        self._tokenizers = {}

    def _load_tokenizer(self, name):
        if name not in self._tokenizers:
            from transformers import AutoTokenizer

            try:
                tokenizer = AutoTokenizer.from_pretrained(name)
            except Exception:
                tokenizer = AutoTokenizer.from_pretrained(name, use_fast=False)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token or tokenizer.sep_token
            self._tokenizers[name] = tokenizer
        return self._tokenizers[name]

    def _tokenizer_for(self, task):
        name = self.tokenizer_name or _DEFAULT_TOKENIZERS.get(task, "bert-base-uncased")
        return self._load_tokenizer(name)

    @property
    def tokenizer(self):
        return self._tokenizer_for("generation")

    def create_session(self, model):
        import onnxruntime as ort

        return ort.InferenceSession(
            model.SerializeToString(), providers=["CPUExecutionProvider"]
        )

    def _resolve_task(self, model_config, session):
        task = self.task or _normalize_task(model_config.get("text_task"))
        if task:
            return task
        model_name = str(model_config.get("model_name") or "").lower()
        if "gpt" in model_name:
            return "generation"
        if "squad" in model_name:
            return "question_answering"
        if "roberta" in model_name or "classification" in model_name:
            return "classification"
        if "t5" in model_name:
            return "summarization"
        if any(len(getattr(item, "shape", ())) == 3 for item in session.get_inputs()):
            return "generation"
        return "forward"

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

    @staticmethod
    def _sample_text(sample):
        if isinstance(sample, str):
            return sample
        for key in ("prompt", "text", "sentence", "context"):
            value = sample.get(key)
            if isinstance(value, str) and value:
                return value
        return str(sample)

    @staticmethod
    def _fixed_sequence_length(session):
        for input_item in session.get_inputs():
            for dimension in input_item.shape[1:]:
                if isinstance(dimension, int) and dimension > 0:
                    return dimension
        return None

    def _prepare_inputs(self, session, sample, task):
        tokenizer = self._tokenizer_for(task)
        fixed_length = self._fixed_sequence_length(session)
        max_length = fixed_length or self.max_length
        padding = "max_length" if fixed_length else False

        if (
            task == "question_answering"
            and isinstance(sample, dict)
            and isinstance(sample.get("question"), str)
            and isinstance(sample.get("context"), str)
        ):
            encoded = tokenizer(
                sample["question"],
                sample["context"],
                max_length=max_length,
                padding=padding,
                truncation="only_second",
                return_tensors="np",
            )
        else:
            encoded = tokenizer(
                self._sample_text(sample),
                max_length=max_length,
                padding=padding,
                truncation=True,
                return_tensors="np",
            )

        input_ids = np.asarray(encoded["input_ids"], dtype=np.int64)
        attention_mask = np.asarray(
            encoded.get("attention_mask", np.ones_like(input_ids)), dtype=np.int64
        )
        token_type_ids = np.asarray(
            encoded.get("token_type_ids", np.zeros_like(input_ids)), dtype=np.int64
        )

        feed = {}
        for input_item in session.get_inputs():
            name = input_item.name
            lower_name = name.lower()
            if "unique" in lower_name:
                feed[name] = np.zeros((1,), dtype=np.int64)
            elif "segment" in lower_name or "token_type" in lower_name:
                feed[name] = token_type_ids
            elif "mask" in lower_name:
                feed[name] = attention_mask
            elif "id" in lower_name or "input" in lower_name:
                feed[name] = input_ids
            elif input_item.type == "tensor(int64)":
                feed[name] = input_ids
            else:
                feed[name] = np.zeros((1,), dtype=np.float32)
        return feed

    @staticmethod
    def _softmax(values):
        values = np.asarray(values, dtype=np.float64)
        shifted = values - np.max(values)
        exponentials = np.exp(shifted)
        return exponentials / np.sum(exponentials)

    def _format_prediction(self, outputs, task, output_names=None):
        if task == "classification":
            logits = np.asarray(outputs[0], dtype=np.float64).reshape(-1)
            return {
                "task": task,
                "label": int(np.argmax(logits)),
                "scores": self._softmax(logits).tolist(),
                "logits": logits.tolist(),
            }

        if task == "question_answering":
            output_names = output_names or []
            if "unstack:1" in output_names and "unstack:0" in output_names:
                start_index = output_names.index("unstack:0")
                end_index = output_names.index("unstack:1")
            elif len(outputs) > 1:
                start_index, end_index = 0, 1
            else:
                start_index = end_index = 0
            start_logits = np.asarray(outputs[start_index], dtype=np.float64).reshape(-1)
            end_logits = np.asarray(outputs[end_index], dtype=np.float64).reshape(-1)
            if end_logits.shape != start_logits.shape:
                end_logits = np.zeros_like(start_logits)
            return {
                "task": task,
                "start": int(np.argmax(start_logits)),
                "end": int(np.argmax(end_logits)),
                "start_logits": start_logits.tolist(),
                "end_logits": end_logits.tolist(),
            }

        embedding = np.asarray(outputs[0], dtype=np.float64)
        if embedding.ndim >= 2:
            embedding = embedding.reshape(-1, embedding.shape[-1]).mean(axis=0)
        else:
            embedding = embedding.reshape(-1)
        return {"task": task, "embedding": embedding.tolist()}

    def _execute_forward(self, session, samples, task):
        predictions = {}
        for index, sample in enumerate(samples):
            feed = self._prepare_inputs(session, sample, task)
            outputs = session.run(None, feed)
            output_names = [item.name for item in session.get_outputs()]
            predictions[index] = self._format_prediction(outputs, task, output_names)
        return predictions

    def execute_text_model(self, model, prompts, config=None, samples=None):
        session = self.create_session(model)
        model_config = config or {}
        task = self._resolve_task(model_config, session)
        if task == "generation":
            return {
                index: self.generate(session, self._sample_text(prompt))
                for index, prompt in enumerate(prompts)
            }
        return self._execute_forward(
            session, samples if samples is not None else prompts, task
        )

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

    @staticmethod
    def _paired(base_outputs, optimized_outputs):
        return [
            (base_outputs[key], optimized_outputs[key])
            for key in base_outputs
            if key in optimized_outputs
        ]

    @staticmethod
    def _cosine_similarity(left, right):
        left = np.asarray(left, dtype=np.float64).reshape(-1)
        right = np.asarray(right, dtype=np.float64).reshape(-1)
        if left.shape != right.shape:
            return 0.0
        denominator = np.linalg.norm(left) * np.linalg.norm(right)
        if denominator == 0:
            return 1.0 if np.array_equal(left, right) else 0.0
        return float(np.dot(left, right) / denominator)

    def _evaluate_generation(self, base_outputs, optimized_outputs):
        scores = []
        changed_samples = 0
        for index, base_text in base_outputs.items():
            optimized_text = optimized_outputs.get(index, "")
            if isinstance(base_text, dict):
                base_text = base_text.get("text", "")
            if isinstance(optimized_text, dict):
                optimized_text = optimized_text.get("text", "")
            prediction = str(base_text).split()
            reference = str(optimized_text).split()
            scores.append(self._sentence_bleu(prediction, reference))
            changed_samples += int(base_text != optimized_text)
        if not scores:
            return {
                "task": "generation",
                "mean_bleu": 0.0,
                "median_bleu": 0.0,
                "scores": [],
                "changed_samples": 0,
                "total_samples": 0,
                "change_rate": 0.0,
            }
        return {
            "task": "generation",
            "mean_bleu": float(np.mean(scores)),
            "median_bleu": float(np.median(scores)),
            "scores": [float(score) for score in scores],
            "changed_samples": changed_samples,
            "total_samples": len(scores),
            "change_rate": 100.0 * changed_samples / len(scores),
        }

    def _evaluate_classification(self, pairs):
        changed_samples = 0
        agreements = 0
        cosines = []
        max_diffs = []
        for base, optimized in pairs:
            base_logits = np.asarray(base.get("logits", []), dtype=np.float64)
            optimized_logits = np.asarray(optimized.get("logits", []), dtype=np.float64)
            if base_logits.shape == optimized_logits.shape:
                max_diffs.append(float(np.max(np.abs(base_logits - optimized_logits))))
                cosines.append(self._cosine_similarity(base_logits, optimized_logits))
            label_changed = base.get("label") != optimized.get("label")
            agreements += int(not label_changed)
            changed_samples += int(label_changed)
        total = len(pairs)
        return {
            "task": "classification",
            "changed_samples": changed_samples,
            "total_samples": total,
            "change_rate": 100.0 * changed_samples / total if total else 0.0,
            "label_agreement": 100.0 * agreements / total if total else 0.0,
            "mean_cosine_similarity": float(np.mean(cosines)) if cosines else 1.0,
            "mean_max_abs_diff": float(np.mean(max_diffs)) if max_diffs else 0.0,
        }

    def _evaluate_question_answering(self, pairs):
        changed_samples = 0
        agreements = 0
        max_diffs = []
        for base, optimized in pairs:
            base_start = np.asarray(base.get("start_logits", []), dtype=np.float64)
            base_end = np.asarray(base.get("end_logits", []), dtype=np.float64)
            optimized_start = np.asarray(
                optimized.get("start_logits", []), dtype=np.float64
            )
            optimized_end = np.asarray(
                optimized.get("end_logits", []), dtype=np.float64
            )
            if base_start.shape == optimized_start.shape:
                max_diffs.append(
                    float(np.max(np.abs(base_start - optimized_start)))
                )
            if base_end.shape == optimized_end.shape:
                max_diffs.append(float(np.max(np.abs(base_end - optimized_end))))
            span_changed = (
                base.get("start") != optimized.get("start")
                or base.get("end") != optimized.get("end")
            )
            agreements += int(not span_changed)
            changed_samples += int(span_changed)
        total = len(pairs)
        return {
            "task": "question_answering",
            "changed_samples": changed_samples,
            "total_samples": total,
            "change_rate": 100.0 * changed_samples / total if total else 0.0,
            "span_agreement": 100.0 * agreements / total if total else 0.0,
            "mean_max_abs_diff": float(np.mean(max_diffs)) if max_diffs else 0.0,
        }

    def _evaluate_embedding(self, pairs, task):
        changed_samples = 0
        cosines = []
        max_diffs = []
        for base, optimized in pairs:
            base_embedding = np.asarray(base.get("embedding", []), dtype=np.float64)
            optimized_embedding = np.asarray(
                optimized.get("embedding", []), dtype=np.float64
            )
            if base_embedding.shape != optimized_embedding.shape:
                changed_samples += 1
                cosines.append(0.0)
                continue
            max_diff = float(np.max(np.abs(base_embedding - optimized_embedding)))
            max_diffs.append(max_diff)
            cosines.append(self._cosine_similarity(base_embedding, optimized_embedding))
            changed_samples += int(max_diff > 1e-4)
        total = len(pairs)
        return {
            "task": task,
            "changed_samples": changed_samples,
            "total_samples": total,
            "change_rate": 100.0 * changed_samples / total if total else 0.0,
            "mean_cosine_similarity": float(np.mean(cosines)) if cosines else 1.0,
            "mean_max_abs_diff": float(np.mean(max_diffs)) if max_diffs else 0.0,
        }

    def evaluate(self, base_outputs, optimized_outputs):
        if not base_outputs:
            return self._evaluate_generation(base_outputs, optimized_outputs)
        first = next(iter(base_outputs.values()))
        task = first.get("task") if isinstance(first, dict) else "generation"
        if task in (None, "generation"):
            return self._evaluate_generation(base_outputs, optimized_outputs)

        pairs = self._paired(base_outputs, optimized_outputs)
        if task == "classification":
            return self._evaluate_classification(pairs)
        if task == "question_answering":
            return self._evaluate_question_answering(pairs)
        return self._evaluate_embedding(pairs, task)
