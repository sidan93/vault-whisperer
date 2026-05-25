import os
from google import genai
from google.genai import types
from embedder.base import EmbedderBase


class GoogleEmbedder(EmbedderBase):
    def __init__(self) -> None:
        self._client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))
        self._model = "text-embedding-004"

    def embed(self, texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
        results = []
        for text in texts:
            response = self._client.models.embed_content(
                model=self._model,
                contents=text,
                config=types.EmbedContentConfig(task_type=task_type.upper()),
            )
            results.append(response.embeddings[0].values)
        return results
