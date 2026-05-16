import httpx


class IndexerClient:
    def __init__(self, base_url: str) -> None:
        self._base_url = base_url

    def search(self, query: str, user_id: str, n_results: int = 5) -> list[dict]:
        response = httpx.post(
            f"{self._base_url}/search",
            json={"query": query, "user_id": user_id, "n_results": n_results},
            timeout=30.0,
        )
        response.raise_for_status()
        return response.json()["results"]
