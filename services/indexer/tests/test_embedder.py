import pytest
from unittest.mock import patch, MagicMock
from embedder.base import EmbedderBase


def test_embedder_base_is_abstract():
    with pytest.raises(TypeError):
        EmbedderBase()


def test_concrete_embedder_must_implement_embed():
    class Incomplete(EmbedderBase):
        pass

    with pytest.raises(TypeError):
        Incomplete()


def test_concrete_embedder_works_when_embed_implemented():
    class Stub(EmbedderBase):
        def embed(self, texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
            return [[0.1] * 3 for _ in texts]

    stub = Stub()
    result = stub.embed(["hello"])
    assert len(result) == 1
    assert len(result[0]) == 3


from embedder.google import GoogleEmbedder


@patch("embedder.google.genai.embed_content")
def test_google_embedder_returns_vectors(mock_embed):
    mock_embed.return_value = {"embedding": [0.1, 0.2, 0.3]}

    embedder = GoogleEmbedder()
    result = embedder.embed(["hello world"])

    assert len(result) == 1
    assert result[0] == [0.1, 0.2, 0.3]


@patch("embedder.google.genai.embed_content")
def test_google_embedder_passes_task_type(mock_embed):
    mock_embed.return_value = {"embedding": [0.1]}

    embedder = GoogleEmbedder()
    embedder.embed(["query text"], task_type="retrieval_query")

    call_kwargs = mock_embed.call_args.kwargs
    assert call_kwargs.get("task_type") == "retrieval_query"


@patch("embedder.google.genai.embed_content")
def test_google_embedder_handles_multiple_texts(mock_embed):
    mock_embed.return_value = {"embedding": [0.1, 0.2]}

    embedder = GoogleEmbedder()
    result = embedder.embed(["first", "second", "third"])

    assert len(result) == 3
    assert mock_embed.call_count == 3
