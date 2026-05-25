import chromadb


class ChromaWriter:
    def __init__(self, client: chromadb.ClientAPI) -> None:
        self._col = client.get_or_create_collection("vault")

    def upsert_file(
        self,
        source: str,
        chunks: list[str],
        embeddings: list[list[float]],
        tags: list[str],
        user_id: str,
    ) -> None:
        existing = self._col.get(where={"source": source})
        if existing["ids"]:
            self._col.delete(ids=existing["ids"])
        if not chunks:
            return
        ids = [f"{source}__{i}" for i in range(len(chunks))]
        self._col.add(
            ids=ids,
            documents=chunks,
            embeddings=embeddings,
            metadatas=[
                {"source": source, "tags": ",".join(tags), "chunk_index": i, "user_id": user_id}
                for i in range(len(chunks))
            ],
        )

    def search(self, query_embedding: list[float], user_id: str, n_results: int = 5) -> list[dict]:
        count = self._col.count()
        if count == 0:
            return []
        results = self._col.query(
            query_embeddings=[query_embedding],
            n_results=min(n_results, count),
            include=["documents", "metadatas"],
        )
        output = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            tags = [t for t in meta["tags"].split(",") if t] if meta["tags"] else []
            output.append({"text": doc, "source": meta["source"], "tags": tags})
        return output
