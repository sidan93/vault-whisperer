import httpx


class GitSyncClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def sync(self) -> None:
        response = httpx.post(f"{self._base_url}/sync", timeout=30.0)
        response.raise_for_status()
