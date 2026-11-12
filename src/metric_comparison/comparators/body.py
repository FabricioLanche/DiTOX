class BodyComparator:

    def __init__(self, evaluation, comparisons):
        self.evaluation = evaluation
        self.comparisons = comparisons

    def update(self, model_name, current_pass="all"):
        pck = self.evaluation["pck"]
        base_pck = self.evaluation.get("base_pck")
        is_dissimilar = pck < base_pck if base_pck is not None else pck < 100

        print("PCK for " + current_pass + ": " + str(pck))
        self.comparisons[model_name][current_pass] = {
            "pck": float(pck),
            "pck_delta": (float(pck) - float(base_pck)) if base_pck is not None else None,
        }
        if base_pck is not None:
            self.comparisons[model_name][current_pass]["base_pck"] = float(base_pck)

        if is_dissimilar:
            self.comparisons[model_name]["different"] += 1

        self.comparisons["no_dissimilar"] += 1 if is_dissimilar else 0
