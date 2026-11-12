class SpeechComparator:

    def __init__(self, evaluation, comparisons):
        self.evaluation = evaluation
        self.comparisons = comparisons

    def update(self, model_name, current_pass="all"):
        wer = self.evaluation["wer"]
        cer = self.evaluation["cer"]
        base_wer = self.evaluation.get("base_wer")
        base_cer = self.evaluation.get("base_cer")
        is_dissimilar = (
            (base_wer is not None and wer > base_wer)
            or (base_cer is not None and cer > base_cer)
        )

        print("WER for " + current_pass + ": " + str(wer))
        print("CER for " + current_pass + ": " + str(cer))
        self.comparisons[model_name][current_pass] = {
            "wer": float(wer),
            "cer": float(cer),
            "wer_delta": (float(wer) - float(base_wer)) if base_wer is not None else None,
            "cer_delta": (float(cer) - float(base_cer)) if base_cer is not None else None,
        }
        if base_wer is not None:
            self.comparisons[model_name][current_pass]["base_wer"] = float(base_wer)
        if base_cer is not None:
            self.comparisons[model_name][current_pass]["base_cer"] = float(base_cer)

        if is_dissimilar:
            self.comparisons[model_name]["different"] += 1

        self.comparisons["no_dissimilar"] += 1 if is_dissimilar else 0
