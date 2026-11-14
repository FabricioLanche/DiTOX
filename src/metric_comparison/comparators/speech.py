class SpeechComparator:
    def __init__(self, evaluation, comparisons):
        self.evaluation = evaluation
        self.comparisons = comparisons

    def update(self, model_name, current_pass="all"):
        different_words = self.evaluation["different_words"]
        is_dissimilar = different_words > 0
        self.comparisons[model_name][current_pass] = {
            "output_change": {
                "changed_samples": int(self.evaluation["different_samples"]),
                "total_samples": int(self.evaluation["total_samples"]),
                "change_rate": float(self.evaluation["change_rate"]),
            },
            "family_metrics": {"transcription_diff": {
                "wer": float(self.evaluation["wer"]),
                "cer": float(self.evaluation["cer"]),
                "substitutions": int(self.evaluation["substitutions"]),
                "insertions": int(self.evaluation["insertions"]),
                "deletions": int(self.evaluation["deletions"]),
            }},
        }
        if is_dissimilar:
            self.comparisons[model_name]["different"] += 1
        self.comparisons["no_dissimilar"] += int(is_dissimilar)
