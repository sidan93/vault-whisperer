import os
from contextlib import asynccontextmanager

import chromadb
from fastapi import FastAPI
from pydantic import BaseModel

from chroma_writer import ChromaWriter
from embedder import get_embedder
from embedder.base import EmbedderBase
from watcher import start_watcher

_VAULT_PATH = os.getenv("VAULT_PATH", "/vault")
_CHROMA_HOST = os.getenv("CHROMA_HOST", "http://chromadb:8000")

_embedder: EmbedderBase | None = None
_writer: ChromaWriter | None = None
_observer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedder, _writer, _observer
    h, _, p = _CHROMA_HOST.removeprefix("http://").partition(":")
    client = chromadb.HttpClient(host=h, port=int(p) if p else 8000)
    _embedder = get_embedder()
    _writer = ChromaWriter(client)
    _observer = start_watcher(_embedder, _writer, _VAULT_PATH)
    yield
    if _observer:
        _observer.stop()
        _observer.join()


app = FastAPI(lifespan=lifespan)


class SearchRequest(BaseModel):
    query: str
    n_results: int = 5


@app.post("/search")
def search(req: SearchRequest) -> dict:
    query_emb = _embedder.embed([req.query], task_type="retrieval_query")[0]
    results = _writer.search(query_emb, n_results=req.n_results)
    return {"results": results}
