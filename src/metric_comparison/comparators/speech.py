class SpeechComparator:

    def __init__(self, evaluation, comparisons):
        self.evaluation = evaluation
        self.comparisons = comparisons

    def update(self, model_name, current_pass="all"):
        wer = self.evaluation["wer"]
        cer = self.evaluation["cer"]
        is_dissimilar = wer > 0 or cer > 0

        print("WER for " + current_pass + ": " + str(wer))
        print("CER for " + current_pass + ": " + str(cer))
        self.comparisons[model_name][current_pass] = {
            "wer": str(wer),
            "cer": str(cer)
        }

        if is_dissimilar:
            self.comparisons[model_name]["different"] += 1

        self.comparisons["no_dissimilar"] += 1 if is_dissimilar else 0