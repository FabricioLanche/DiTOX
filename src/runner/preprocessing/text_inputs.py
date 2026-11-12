class TextInputProvider:
    """Load and format text prompts used by text backends."""

    DEFAULT_TEMPLATE = "Context: {context} Question: {question}"

    def __init__(self, config=None):
        self.config = config or {}
        self.dataset_name = self.config.get("dataset", "squad_v2")
        self.split = self.config.get("split", "validation")
        self.template = self.config.get("prompt_template", self.DEFAULT_TEMPLATE)
        self._prompts = None

    def load(self):
        if self._prompts is not None:
            return self._prompts
        from datasets import load_dataset

        dataset = load_dataset(self.dataset_name, split=self.split)
        prompts = []
        for row in dataset:
            try:
                prompts.append(self.template.format(**row))
            except (KeyError, IndexError):
                prompts.append(str(row))
        self._prompts = prompts
        return self._prompts
