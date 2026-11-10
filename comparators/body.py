class BodyComparator:

    def __init__(self, evaluation, comparisons):
        self.evaluation = evaluation
        self.comparisons = comparisons

    def update(self, model_name, current_pass="all"):
        pck = self.evaluation["pck"]
        dissimilar_percentage = 100 - pck

        print("PCK for " + current_pass + ": " + str(pck))
        self.comparisons[model_name][current_pass] = {
            "pck": str(pck)
        }

        if dissimilar_percentage > 0:
            self.comparisons[model_name]["different"] += 1

        self.comparisons["no_dissimilar"] += 1 if dissimilar_percentage != 0 else 0