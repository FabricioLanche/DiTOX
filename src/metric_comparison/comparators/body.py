class BodyComparator:
    def __init__(self, evaluation, comparisons):
        self.evaluation = evaluation
        self.comparisons = comparisons

    def update(self, model_name, current_pass="all"):
        different_keypoints = self.evaluation["different_keypoints"]
        total_keypoints = self.evaluation["total_keypoints"]
        is_dissimilar = different_keypoints > 0

        self.comparisons[model_name][current_pass] = {
            "output_change": {
                "changed_samples": int(self.evaluation["different_samples"]),
                "total_samples": int(self.evaluation["total_samples"]),
                "change_rate": float(self.evaluation["change_rate"]),
            },
            "family_metrics": {"keypoint_agreement": {
                "oks": float(self.evaluation["oks"]),
                "pck": float(self.evaluation["pck"]),
                "mean_normalized_displacement": float(self.evaluation["mean_normalized_displacement"]),
            }},
        }

        if is_dissimilar:
            self.comparisons[model_name]["different"] += 1
        self.comparisons["no_dissimilar"] += int(is_dissimilar)
