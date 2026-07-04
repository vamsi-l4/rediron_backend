from abc import ABC, abstractmethod


class AIProviderError(Exception):
    pass


class BaseAIProvider(ABC):
    name = "base"

    @abstractmethod
    def generate_json(self, prompt, schema_name):
        raise NotImplementedError

