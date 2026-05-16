import pytest
import httpx
from unittest.mock import patch, MagicMock
from clients.git_sync import GitSyncClient
from clients.indexer import IndexerClient


def test_git_sync_client_posts_to_sync():
    with patch("clients.git_sync.httpx.post") as mock_post:
        mock_response = MagicMock(status_code=200)
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        client = GitSyncClient("http://git-sync:8000")
        client.sync()

        mock_post.assert_called_once_with("http://git-sync:8000/sync", timeout=30.0)


def test_git_sync_client_raises_on_http_error():
    with patch("clients.git_sync.httpx.post") as mock_post:
        mock_response = MagicMock(status_code=500)
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Server Error", request=MagicMock(), response=MagicMock()
        )
        mock_post.return_value = mock_response

        client = GitSyncClient("http://git-sync:8000")
        with pytest.raises(httpx.HTTPStatusError):
            client.sync()


def test_indexer_client_returns_results():
    with patch("clients.indexer.httpx.post") as mock_post:
        mock_response = MagicMock(status_code=200)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            "results": [{"text": "content", "source": "note.md", "tags": []}]
        }
        mock_post.return_value = mock_response

        client = IndexerClient("http://indexer:8000")
        results = client.search("python query")

        assert len(results) == 1
        assert results[0]["source"] == "note.md"


def test_indexer_client_passes_n_results():
    with patch("clients.indexer.httpx.post") as mock_post:
        mock_response = MagicMock(status_code=200)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        client = IndexerClient("http://indexer:8000")
        client.search("query", n_results=3)

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["n_results"] == 3
