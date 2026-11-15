class TextComparator:
    """Record text-generation, classification, QA and encoder comparisons."""

    def __init__(self, evaluation, comparisons):
        self.evaluation = evaluation
        self.comparisons = comparisons

    def update(self, model_name, current_pass="all", include_certainties=False):
        task = self.evaluation.get("task", "generation")
        output_change = {
            "changed_samples": int(self.evaluation["changed_samples"]),
            "total_samples": int(self.evaluation["total_samples"]),
            "change_rate": float(self.evaluation["change_rate"]),
        }

        if task == "generation":
            mean_bleu = self.evaluation["mean_bleu"]
            median_bleu = self.evaluation["median_bleu"]
            print("Mean BLEU for " + current_pass + ": " + str(mean_bleu))
            print("Median BLEU for " + current_pass + ": " + str(median_bleu))
            family_metrics = {"text_generation": {
                "mean_bleu": mean_bleu,
                "median_bleu": median_bleu,
            }}
        elif task == "classification":
            print("Label agreement for " + current_pass + ": " + str(
                self.evaluation["label_agreement"]
            ))
            print("Mean cosine similarity for " + current_pass + ": " + str(
                self.evaluation["mean_cosine_similarity"]
            ))
            family_metrics = {"text_classification": {
                "label_agreement": self.evaluation["label_agreement"],
                "mean_cosine_similarity": self.evaluation["mean_cosine_similarity"],
                "mean_max_abs_diff": self.evaluation["mean_max_abs_diff"],
            }}
        elif task == "question_answering":
            print("Span agreement for " + current_pass + ": " + str(
                self.evaluation["span_agreement"]
            ))
            family_metrics = {"text_question_answering": {
                "span_agreement": self.evaluation["span_agreement"],
                "mean_max_abs_diff": self.evaluation["mean_max_abs_diff"],
            }}
        else:
            print("Mean cosine similarity for " + current_pass + ": " + str(
                self.evaluation["mean_cosine_similarity"]
            ))
            family_metrics = {"text_encoder": {
                "mean_cosine_similarity": self.evaluation["mean_cosine_similarity"],
                "mean_max_abs_diff": self.evaluation["mean_max_abs_diff"],
            }}

        self.comparisons[model_name][current_pass] = {
            "output_change": output_change,
            "family_metrics": family_metrics,
        }

        if self.evaluation["changed_samples"] > 0:
            self.comparisons[model_name]["different"] += 1
        self.comparisons["no_dissimilar"] += int(
            self.evaluation["changed_samples"] > 0
        )
