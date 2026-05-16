from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@patch("main.sync_vault")
def test_post_sync_returns_ok(mock_sync):
    response = client.post("/sync")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_sync.assert_called_once()


@patch("main.sync_vault", side_effect=Exception("git push failed"))
def test_post_sync_returns_500_on_error(mock_sync):
    response = client.post("/sync")
    assert response.status_code == 500
    assert "git push failed" in response.json()["detail"]
