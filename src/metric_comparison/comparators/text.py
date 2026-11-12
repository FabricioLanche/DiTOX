class TextComparator:
    """Record BLEU-based text generation comparisons."""

    def __init__(self, evaluation, comparisons):
        self.evaluation = evaluation
        self.comparisons = comparisons

    def update(self, model_name, current_pass="all", include_certainties=False):
        mean_bleu = self.evaluation["mean_bleu"]
        median_bleu = self.evaluation["median_bleu"]

        print("Mean BLEU for " + current_pass + ": " + str(mean_bleu))
        print("Median BLEU for " + current_pass + ": " + str(median_bleu))

        self.comparisons[model_name][current_pass] = {
            "mean_bleu": mean_bleu,
            "median_bleu": median_bleu,
        }

        if mean_bleu < 1.0:
            self.comparisons[model_name]["different"] += 1
        self.comparisons["no_dissimilar"] += 1 if mean_bleu == 1.0 else 0
