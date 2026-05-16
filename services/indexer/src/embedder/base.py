from abc import ABC, abstractmethod


class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
        ...
