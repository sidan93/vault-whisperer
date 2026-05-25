import os
from google import genai
from google.genai import types
from embedder.base import EmbedderBase

# Task instruction prefixes recommended for gemini-embedding-2
_TASK_INSTRUCTIONS: dict[str, str] = {
    "RETRIEVAL_DOCUMENT": "Represent this document for retrieval: ",
    "RETRIEVAL_QUERY": "Represent this query for retrieving relevant documents: ",
    "SEMANTIC_SIMILARITY": "Represent this text for semantic similarity: ",
    "CLASSIFICATION": "Classify: ",
    "CLUSTERING": "Cluster: ",
}


class GoogleEmbedder(EmbedderBase):
    def __init__(self) -> None:
        self._client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY", ""))
        self._model = "gemini-embedding-2"

    def embed(self, texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
        task_key = task_type.upper()
        prefix = _TASK_INSTRUCTIONS.get(task_key, "")
        results = []
        for text in texts:
            response = self._client.models.embed_content(
                model=self._model,
                contents=f"{prefix}{text}",
                config=types.EmbedContentConfig(task_type=task_key),
            )
            results.append(response.embeddings[0].values)
        return results
