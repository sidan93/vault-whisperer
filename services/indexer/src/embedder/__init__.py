import os

from embedder.base import EmbedderBase


def get_embedder() -> EmbedderBase:
    provider = os.getenv("EMBEDDER_PROVIDER", "google").lower()
    if provider == "google":
        from embedder.google import GoogleEmbedder
        return GoogleEmbedder()
    raise ValueError(f"Unknown EMBEDDER_PROVIDER={provider!r}. Supported: google")
