from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app


def test_search_returns_results():
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.1, 0.2, 0.3]]
    mock_writer = MagicMock()
    mock_writer.search.return_value = [
        {"text": "chunk content", "source": "123/note.md", "tags": ["python"]}
    ]

    with patch("main._embedder", mock_embedder), patch("main._writer", mock_writer):
        client = TestClient(app)
        response = client.post(
            "/search", json={"query": "how does python work?", "user_id": "123"}
        )

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["source"] == "123/note.md"
    mock_embedder.embed.assert_called_once_with(
        ["how does python work?"], task_type="retrieval_query"
    )


def test_search_passes_user_id_to_writer():
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.1, 0.2]]
    mock_writer = MagicMock()
    mock_writer.search.return_value = []

    with patch("main._embedder", mock_embedder), patch("main._writer", mock_writer):
        client = TestClient(app)
        client.post("/search", json={"query": "test", "user_id": "456"})

    call_kwargs = mock_writer.search.call_args.kwargs
    assert call_kwargs["user_id"] == "456"


def test_search_returns_empty_list_when_no_results():
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.1, 0.2]]
    mock_writer = MagicMock()
    mock_writer.search.return_value = []

    with patch("main._embedder", mock_embedder), patch("main._writer", mock_writer):
        client = TestClient(app)
        response = client.post("/search", json={"query": "unknown topic", "user_id": "123"})

    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_search_passes_n_results_to_writer():
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.1]]
    mock_writer = MagicMock()
    mock_writer.search.return_value = []

    with patch("main._embedder", mock_embedder), patch("main._writer", mock_writer):
        client = TestClient(app)
        client.post("/search", json={"query": "test", "user_id": "123", "n_results": 3})

    call_kwargs = mock_writer.search.call_args.kwargs
    assert call_kwargs["n_results"] == 3
