import os
import google.generativeai as genai
from embedder.base import EmbedderBase


class GoogleEmbedder(EmbedderBase):
    def __init__(self) -> None:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
        self._model = "models/text-embedding-004"

    def embed(self, texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
        results = []
        for text in texts:
            response = genai.embed_content(
                model=self._model,
                content=text,
                task_type=task_type,
            )
            results.append(response["embedding"])
        return results
