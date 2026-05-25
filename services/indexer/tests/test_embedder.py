import pytest
from unittest.mock import patch, MagicMock
from embedder.base import EmbedderBase
from embedder import get_embedder


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


def test_get_embedder_returns_google_by_default():
    with patch.dict("os.environ", {"EMBEDDER_PROVIDER": "google", "GOOGLE_API_KEY": "dummy"}):
        from embedder.google import GoogleEmbedder
        embedder = get_embedder()
    assert isinstance(embedder, GoogleEmbedder)


def test_get_embedder_raises_on_unknown_provider():
    with patch.dict("os.environ", {"EMBEDDER_PROVIDER": "unknown_xyz"}):
        with pytest.raises(ValueError, match="EMBEDDER_PROVIDER"):
            get_embedder()


from embedder.google import GoogleEmbedder


def _make_mock_client(values):
    mock_client = MagicMock()
    mock_embedding = MagicMock()
    mock_embedding.values = values
    mock_client.models.embed_content.return_value.embeddings = [mock_embedding]
    return mock_client


@patch("embedder.google.genai.Client")
def test_google_embedder_returns_vectors(mock_client_class):
    mock_client_class.return_value = _make_mock_client([0.1, 0.2, 0.3])

    embedder = GoogleEmbedder()
    result = embedder.embed(["hello world"])

    assert len(result) == 1
    assert result[0] == [0.1, 0.2, 0.3]


@patch("embedder.google.genai.Client")
def test_google_embedder_passes_task_type(mock_client_class):
    mock_client = _make_mock_client([0.1])
    mock_client_class.return_value = mock_client

    embedder = GoogleEmbedder()
    embedder.embed(["query text"], task_type="retrieval_query")

    call_kwargs = mock_client.models.embed_content.call_args.kwargs
    config = call_kwargs.get("config")
    assert config.task_type == "RETRIEVAL_QUERY"


@patch("embedder.google.genai.Client")
def test_google_embedder_handles_multiple_texts(mock_client_class):
    mock_client = _make_mock_client([0.1, 0.2])
    mock_client_class.return_value = mock_client

    embedder = GoogleEmbedder()
    result = embedder.embed(["first", "second", "third"])

    assert len(result) == 3
    assert mock_client.models.embed_content.call_count == 3
