# Multi-User Mode Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить whitelist разрешённых пользователей, DM-only режим, и сегрегацию заметок и RAG-поиска по `user_id`.

**Architecture:** Новый модуль `auth.py` в боте обеспечивает access control (sync, легко тестируется). Vault пишется в `/vault/{user_id}/`, watcher извлекает `user_id` из первого компонента пути и добавляет в metadata ChromaDB. Поиск фильтрует по `user_id` через `where` в ChromaDB.

**Tech Stack:** python-telegram-bot, FastAPI (indexer), ChromaDB, pytest (MagicMock для unit-тестов, chromadb.EphemeralClient для интеграционных)

---

## File Map

| Действие | Файл | Роль |
|---|---|---|
| Create | `services/bot/src/auth.py` | `load_whitelist()`, `access_error()` |
| Create | `services/bot/tests/test_auth.py` | тесты auth модуля |
| Modify | `services/bot/src/handlers/capture.py` | user subfolder, access check |
| Modify | `services/bot/tests/test_capture.py` | обновить тесты |
| Modify | `services/bot/src/handlers/search.py` | user_id в поиск, access check |
| Modify | `services/bot/tests/test_search.py` | обновить тесты |
| Modify | `services/bot/src/clients/indexer.py` | добавить user_id в запрос |
| Modify | `services/bot/tests/test_clients.py` | обновить тесты |
| Modify | `services/bot/src/main.py` | загрузка whitelist при старте |
| Modify | `services/indexer/src/chroma_writer.py` | user_id в metadata + where фильтр |
| Modify | `services/indexer/tests/test_chroma_writer.py` | обновить тесты |
| Modify | `services/indexer/src/watcher.py` | извлечение user_id из пути |
| Modify | `services/indexer/tests/test_watcher.py` | обновить тесты |
| Modify | `services/indexer/src/main.py` | user_id в SearchRequest |
| Modify | `services/indexer/tests/test_api.py` | обновить тесты |
| Modify | `docker-compose.yml` | монтировать allowed_users.txt в bot |
| Create | `allowed_users.txt` | шаблон файла whitelist |
| Modify | `.gitignore` | добавить allowed_users.txt |

---

## Task 1: Auth module

**Files:**
- Create: `services/bot/src/auth.py`
- Create: `services/bot/tests/test_auth.py`

- [ ] **Step 1: Write failing tests**

`services/bot/tests/test_auth.py`:
```python
import pytest
from pathlib import Path
from auth import load_whitelist, access_error


def test_load_whitelist_reads_user_ids(tmp_path):
    f = tmp_path / "allowed.txt"
    f.write_text("123456789\n987654321\n")
    assert load_whitelist(str(f)) == {123456789, 987654321}


def test_load_whitelist_skips_comments(tmp_path):
    f = tmp_path / "allowed.txt"
    f.write_text("# Family\n123456789\n")
    assert load_whitelist(str(f)) == {123456789}


def test_load_whitelist_skips_empty_lines(tmp_path):
    f = tmp_path / "allowed.txt"
    f.write_text("123456789\n\n987654321\n")
    assert load_whitelist(str(f)) == {123456789, 987654321}


def test_access_error_rejects_group():
    error = access_error("group", 123, {123})
    assert error == "Бот работает только в личных сообщениях."


def test_access_error_rejects_supergroup():
    error = access_error("supergroup", 123, {123})
    assert error == "Бот работает только в личных сообщениях."


def test_access_error_rejects_unknown_user():
    error = access_error("private", 999, {123})
    assert error == "У вас нет доступа."


def test_access_error_allows_whitelisted_user():
    error = access_error("private", 123, {123})
    assert error is None
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/bot && python -m pytest tests/test_auth.py -v
```

Expected: `ModuleNotFoundError: No module named 'auth'`

- [ ] **Step 3: Implement auth.py**

`services/bot/src/auth.py`:
```python
def load_whitelist(path: str) -> set[int]:
    result = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                result.add(int(line))
    return result


def access_error(chat_type: str, user_id: int, allowed_users: set[int]) -> str | None:
    if chat_type != "private":
        return "Бот работает только в личных сообщениях."
    if user_id not in allowed_users:
        return "У вас нет доступа."
    return None
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd services/bot && python -m pytest tests/test_auth.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add services/bot/src/auth.py services/bot/tests/test_auth.py
git commit -m "feat(bot): add auth module with whitelist and access_error"
```

---

## Task 2: ChromaWriter — user_id в metadata и поиске

**Files:**
- Modify: `services/indexer/src/chroma_writer.py`
- Modify: `services/indexer/tests/test_chroma_writer.py`

- [ ] **Step 1: Write failing tests**

Заменить весь `services/indexer/tests/test_chroma_writer.py`:
```python
import chromadb
import pytest
from chroma_writer import ChromaWriter


@pytest.fixture
def writer():
    client = chromadb.EphemeralClient()
    try:
        client.delete_collection("vault")
    except Exception:
        pass
    return ChromaWriter(client)


def test_upsert_adds_chunks(writer):
    writer.upsert_file(
        source="notes/test.md",
        chunks=["chunk one content", "chunk two content"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        tags=["python"],
        user_id="123",
    )
    results = writer.search([0.1, 0.2], user_id="123", n_results=5)
    assert len(results) == 2


def test_upsert_replaces_existing_chunks(writer):
    writer.upsert_file(
        source="notes/test.md",
        chunks=["old chunk one", "old chunk two", "old chunk three"],
        embeddings=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        tags=[],
        user_id="123",
    )
    writer.upsert_file(
        source="notes/test.md",
        chunks=["new chunk one"],
        embeddings=[[0.1, 0.2]],
        tags=[],
        user_id="123",
    )
    results = writer.search([0.1, 0.2], user_id="123", n_results=10)
    sources = [r["source"] for r in results]
    assert sources.count("notes/test.md") == 1


def test_search_returns_source_and_tags(writer):
    writer.upsert_file(
        source="notes/python.md",
        chunks=["Python is a programming language"],
        embeddings=[[0.1, 0.2, 0.3]],
        tags=["python", "programming"],
        user_id="123",
    )
    results = writer.search([0.1, 0.2, 0.3], user_id="123", n_results=1)
    assert results[0]["source"] == "notes/python.md"
    assert "python" in results[0]["tags"]


def test_search_returns_empty_when_no_data(writer):
    results = writer.search([0.1, 0.2], user_id="123", n_results=5)
    assert results == []


def test_search_filters_by_user_id(writer):
    writer.upsert_file(
        source="123/alice.md",
        chunks=["Alice note content"],
        embeddings=[[0.9, 0.9]],
        tags=[],
        user_id="123",
    )
    writer.upsert_file(
        source="456/bob.md",
        chunks=["Bob note content"],
        embeddings=[[0.9, 0.9]],
        tags=[],
        user_id="456",
    )
    alice_results = writer.search([0.9, 0.9], user_id="123", n_results=5)
    bob_results = writer.search([0.9, 0.9], user_id="456", n_results=5)
    assert all(r["source"] == "123/alice.md" for r in alice_results)
    assert all(r["source"] == "456/bob.md" for r in bob_results)
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/indexer && python -m pytest tests/test_chroma_writer.py -v
```

Expected: `TypeError: upsert_file() got an unexpected keyword argument 'user_id'`

- [ ] **Step 3: Implement updated ChromaWriter**

Заменить `services/indexer/src/chroma_writer.py`:
```python
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
            where={"user_id": user_id},
        )
        output = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            tags = [t for t in meta["tags"].split(",") if t] if meta["tags"] else []
            output.append({"text": doc, "source": meta["source"], "tags": tags})
        return output
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd services/indexer && python -m pytest tests/test_chroma_writer.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add services/indexer/src/chroma_writer.py services/indexer/tests/test_chroma_writer.py
git commit -m "feat(indexer): add user_id to ChromaWriter metadata and search filter"
```

---

## Task 3: Watcher — извлечение user_id из пути

**Files:**
- Modify: `services/indexer/src/watcher.py`
- Modify: `services/indexer/tests/test_watcher.py`

- [ ] **Step 1: Write failing tests**

Заменить весь `services/indexer/tests/test_watcher.py`:
```python
from unittest.mock import MagicMock
from pathlib import Path
from watchdog.events import FileCreatedEvent, FileModifiedEvent, DirModifiedEvent
from watcher import VaultHandler


def make_handler(tmp_path):
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1, 0.2]]
    writer = MagicMock()
    return VaultHandler(embedder=embedder, writer=writer, vault_path=str(tmp_path))


def test_on_created_indexes_md_file_in_subdir(tmp_path):
    handler = make_handler(tmp_path)
    user_dir = tmp_path / "123456789"
    user_dir.mkdir()
    md_file = user_dir / "note.md"
    md_file.write_text("# Title\n\n" + "Content " * 20, encoding="utf-8")
    handler.on_created(FileCreatedEvent(str(md_file)))
    handler._writer.upsert_file.assert_called_once()


def test_on_modified_indexes_md_file_in_subdir(tmp_path):
    handler = make_handler(tmp_path)
    user_dir = tmp_path / "123456789"
    user_dir.mkdir()
    md_file = user_dir / "note.md"
    md_file.write_text("# Title\n\n" + "Content " * 20, encoding="utf-8")
    handler.on_modified(FileModifiedEvent(str(md_file)))
    handler._writer.upsert_file.assert_called_once()


def test_root_level_md_files_are_skipped(tmp_path):
    handler = make_handler(tmp_path)
    md_file = tmp_path / "note.md"
    md_file.write_text("# Title\n\n" + "Content " * 20, encoding="utf-8")
    handler.on_created(FileCreatedEvent(str(md_file)))
    handler._writer.upsert_file.assert_not_called()


def test_non_md_files_are_ignored(tmp_path):
    handler = make_handler(tmp_path)
    user_dir = tmp_path / "123456789"
    user_dir.mkdir()
    txt_file = user_dir / "note.txt"
    txt_file.write_text("some text", encoding="utf-8")
    handler.on_created(FileCreatedEvent(str(txt_file)))
    handler._writer.upsert_file.assert_not_called()


def test_directory_events_are_ignored(tmp_path):
    handler = make_handler(tmp_path)
    handler.on_modified(DirModifiedEvent(str(tmp_path / "somedir")))
    handler._writer.upsert_file.assert_not_called()


def test_upsert_called_with_correct_source_and_user_id(tmp_path):
    handler = make_handler(tmp_path)
    user_dir = tmp_path / "123456789"
    user_dir.mkdir()
    md_file = user_dir / "my_note.md"
    md_file.write_text("# Title\n\n" + "Content " * 20, encoding="utf-8")
    handler.on_created(FileCreatedEvent(str(md_file)))
    call_kwargs = handler._writer.upsert_file.call_args.kwargs
    assert call_kwargs["source"] == str(Path("123456789") / "my_note.md")
    assert call_kwargs["user_id"] == "123456789"
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/indexer && python -m pytest tests/test_watcher.py -v
```

Expected: несколько FAILED (root files не пропускаются, user_id не передаётся)

- [ ] **Step 3: Implement updated watcher**

Заменить `services/indexer/src/watcher.py`:
```python
import os
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from chunker import chunk_markdown
from chroma_writer import ChromaWriter
from embedder.base import EmbedderBase


class VaultHandler(FileSystemEventHandler):
    def __init__(self, embedder: EmbedderBase, writer: ChromaWriter, vault_path: str) -> None:
        self._embedder = embedder
        self._writer = writer
        self._vault_path = vault_path

    def _handle(self, path: str) -> None:
        if not path.endswith(".md"):
            return
        source = os.path.relpath(path, self._vault_path)
        parts = Path(source).parts
        if len(parts) < 2:
            return
        user_id = parts[0]
        content = Path(path).read_text(encoding="utf-8")
        chunks = chunk_markdown(content, source)
        if not chunks:
            return
        texts = [c.text for c in chunks]
        embeddings = self._embedder.embed(texts)
        self._writer.upsert_file(
            source=source,
            chunks=texts,
            embeddings=embeddings,
            tags=chunks[0].tags,
            user_id=user_id,
        )

    def on_created(self, event) -> None:
        if not event.is_directory:
            self._handle(event.src_path)

    def on_modified(self, event) -> None:
        if not event.is_directory:
            self._handle(event.src_path)


def start_watcher(embedder: EmbedderBase, writer: ChromaWriter, vault_path: str) -> Observer:
    handler = VaultHandler(embedder=embedder, writer=writer, vault_path=vault_path)
    observer = Observer()
    observer.schedule(handler, vault_path, recursive=True)
    observer.start()
    return observer
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd services/indexer && python -m pytest tests/test_watcher.py -v
```

Expected: 6 passed

- [ ] **Step 5: Commit**

```bash
git add services/indexer/src/watcher.py services/indexer/tests/test_watcher.py
git commit -m "feat(indexer): extract user_id from vault path, skip root-level files"
```

---

## Task 4: Indexer API — user_id в SearchRequest

**Files:**
- Modify: `services/indexer/src/main.py`
- Modify: `services/indexer/tests/test_api.py`

- [ ] **Step 1: Write failing tests**

Заменить весь `services/indexer/tests/test_api.py`:
```python
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
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/indexer && python -m pytest tests/test_api.py -v
```

Expected: FAILED (422 Unprocessable Entity из-за отсутствия `user_id` в теле)

- [ ] **Step 3: Implement updated indexer main.py**

Заменить `services/indexer/src/main.py`:
```python
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
    user_id: str
    n_results: int = 5


@app.post("/search")
def search(req: SearchRequest) -> dict:
    query_emb = _embedder.embed([req.query], task_type="retrieval_query")[0]
    results = _writer.search(query_emb, user_id=req.user_id, n_results=req.n_results)
    return {"results": results}
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd services/indexer && python -m pytest tests/test_api.py -v
```

Expected: 4 passed

- [ ] **Step 5: Run all indexer tests**

```bash
cd services/indexer && python -m pytest -v
```

Expected: все тесты зелёные

- [ ] **Step 6: Commit**

```bash
git add services/indexer/src/main.py services/indexer/tests/test_api.py
git commit -m "feat(indexer): add user_id to SearchRequest and pass to ChromaWriter"
```

---

## Task 5: IndexerClient — user_id параметр

**Files:**
- Modify: `services/bot/src/clients/indexer.py`
- Modify: `services/bot/tests/test_clients.py`

- [ ] **Step 1: Write failing tests**

В `services/bot/tests/test_clients.py` заменить только тесты IndexerClient (тесты GitSyncClient оставить как есть):
```python
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
            "results": [{"text": "content", "source": "123/note.md", "tags": []}]
        }
        mock_post.return_value = mock_response

        client = IndexerClient("http://indexer:8000")
        results = client.search("python query", user_id="123")

        assert len(results) == 1
        assert results[0]["source"] == "123/note.md"


def test_indexer_client_passes_user_id():
    with patch("clients.indexer.httpx.post") as mock_post:
        mock_response = MagicMock(status_code=200)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        client = IndexerClient("http://indexer:8000")
        client.search("query", user_id="456")

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["user_id"] == "456"


def test_indexer_client_passes_n_results():
    with patch("clients.indexer.httpx.post") as mock_post:
        mock_response = MagicMock(status_code=200)
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {"results": []}
        mock_post.return_value = mock_response

        client = IndexerClient("http://indexer:8000")
        client.search("query", user_id="123", n_results=3)

        call_kwargs = mock_post.call_args.kwargs
        assert call_kwargs["json"]["n_results"] == 3
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/bot && python -m pytest tests/test_clients.py -v
```

Expected: `TypeError: IndexerClient.search() got an unexpected keyword argument 'user_id'`

- [ ] **Step 3: Implement updated IndexerClient**

Заменить `services/bot/src/clients/indexer.py`:
```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd services/bot && python -m pytest tests/test_clients.py -v
```

Expected: 5 passed

- [ ] **Step 5: Commit**

```bash
git add services/bot/src/clients/indexer.py services/bot/tests/test_clients.py
git commit -m "feat(bot): add user_id parameter to IndexerClient.search"
```

---

## Task 6: capture_handler — user subfolder и access check

**Files:**
- Modify: `services/bot/src/handlers/capture.py`
- Modify: `services/bot/tests/test_capture.py`

- [ ] **Step 1: Write failing tests**

Заменить весь `services/bot/tests/test_capture.py`:
```python
from unittest.mock import MagicMock
from pathlib import Path
from handlers.capture import _filename_from_content, _structure_and_save


def test_filename_from_frontmatter_title():
    content = '---\ntitle: "My Python Note"\n---\n\nContent here'
    filename = _filename_from_content(content)
    assert filename == "my-python-note.md"


def test_filename_strips_special_chars():
    content = '---\ntitle: "Notes: Python & Tips!"\n---\n\nContent'
    filename = _filename_from_content(content)
    assert filename.endswith(".md")
    assert ":" not in filename
    assert "&" not in filename


def test_filename_fallback_to_timestamp_when_no_title():
    content = "# Header\n\nNo frontmatter here"
    filename = _filename_from_content(content)
    assert filename.endswith(".md")
    assert len(filename) > 4


def test_structure_and_save_writes_to_user_subfolder(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = '---\ntitle: "Test Note"\n---\n\nContent'
    git_sync = MagicMock()

    filename = _structure_and_save("raw input", user_id=123, deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path))

    saved_file = tmp_path / "123" / filename
    assert saved_file.exists()
    assert saved_file.read_text(encoding="utf-8") == '---\ntitle: "Test Note"\n---\n\nContent'


def test_structure_and_save_creates_user_dir_if_missing(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = "# Note\n\nContent"
    git_sync = MagicMock()

    _structure_and_save("raw input", user_id=987, deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path))

    assert (tmp_path / "987").is_dir()


def test_structure_and_save_calls_git_sync(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = "# Note\n\nContent"
    git_sync = MagicMock()

    _structure_and_save("raw input", user_id=123, deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path))

    git_sync.sync.assert_called_once()


def test_structure_and_save_passes_text_to_deepseek(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = "# Note\n\nContent"
    git_sync = MagicMock()

    _structure_and_save("my raw text", user_id=123, deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path))

    deepseek.structure_note.assert_called_once_with("my raw text")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/bot && python -m pytest tests/test_capture.py -v
```

Expected: `TypeError: _structure_and_save() got an unexpected keyword argument 'user_id'`

- [ ] **Step 3: Implement updated capture_handler**

Заменить `services/bot/src/handlers/capture.py`:
```python
import re
import datetime
from pathlib import Path

from auth import access_error


def _filename_from_content(content: str) -> str:
    match = re.search(r"title:\s*[\"']?([^\"'\n]+)[\"']?", content)
    if match:
        title = match.group(1).strip()
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        if slug:
            return f"{slug}.md"
    return f"{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"


def _structure_and_save(text: str, user_id: int, deepseek, git_sync, vault_path: str) -> str:
    structured = deepseek.structure_note(text)
    filename = _filename_from_content(structured)
    user_dir = Path(vault_path, str(user_id))
    user_dir.mkdir(exist_ok=True)
    (user_dir / filename).write_text(structured, encoding="utf-8")
    git_sync.sync()
    return filename


async def capture_handler(update, context) -> None:
    error = access_error(
        update.effective_chat.type,
        update.effective_user.id,
        context.bot_data["allowed_users"],
    )
    if error:
        await update.message.reply_text(error)
        return
    filename = _structure_and_save(
        update.message.text,
        user_id=update.effective_user.id,
        deepseek=context.bot_data["deepseek"],
        git_sync=context.bot_data["git_sync"],
        vault_path=context.bot_data["vault_path"],
    )
    await update.message.reply_text(f"Заметка сохранена: {filename}")
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd services/bot && python -m pytest tests/test_capture.py -v
```

Expected: 7 passed

- [ ] **Step 5: Commit**

```bash
git add services/bot/src/handlers/capture.py services/bot/tests/test_capture.py
git commit -m "feat(bot): write notes to user subfolder, add access check to capture"
```

---

## Task 7: search_handler — user_id и access check

**Files:**
- Modify: `services/bot/src/handlers/search.py`
- Modify: `services/bot/tests/test_search.py`

- [ ] **Step 1: Write failing tests**

Заменить весь `services/bot/tests/test_search.py`:
```python
from unittest.mock import MagicMock
from handlers.search import _perform_search


def test_perform_search_returns_synthesized_answer():
    indexer = MagicMock()
    indexer.search.return_value = [
        {"text": "Python is a language", "source": "123/python.md", "tags": []}
    ]
    deepseek = MagicMock()
    deepseek.synthesize_answer.return_value = "Python is a high-level language."

    result = _perform_search("what is python?", user_id="123", indexer=indexer, deepseek=deepseek)

    assert result == "Python is a high-level language."
    deepseek.synthesize_answer.assert_called_once_with(
        "what is python?",
        [{"text": "Python is a language", "source": "123/python.md", "tags": []}],
    )


def test_perform_search_returns_not_found_when_no_results():
    indexer = MagicMock()
    indexer.search.return_value = []
    deepseek = MagicMock()

    result = _perform_search("unknown topic", user_id="123", indexer=indexer, deepseek=deepseek)

    assert result == "Ничего не найдено."
    deepseek.synthesize_answer.assert_not_called()


def test_perform_search_passes_query_and_user_id_to_indexer():
    indexer = MagicMock()
    indexer.search.return_value = []
    deepseek = MagicMock()

    _perform_search("my specific query", user_id="456", indexer=indexer, deepseek=deepseek)

    indexer.search.assert_called_once_with("my specific query", user_id="456")
```

- [ ] **Step 2: Run tests to verify they fail**

```bash
cd services/bot && python -m pytest tests/test_search.py -v
```

Expected: `TypeError: _perform_search() got an unexpected keyword argument 'user_id'`

- [ ] **Step 3: Implement updated search_handler**

Заменить `services/bot/src/handlers/search.py`:
```python
from auth import access_error


def _perform_search(query: str, user_id: str, indexer, deepseek) -> str:
    chunks = indexer.search(query, user_id=user_id)
    if not chunks:
        return "Ничего не найдено."
    return deepseek.synthesize_answer(query, chunks)


async def search_handler(update, context) -> None:
    error = access_error(
        update.effective_chat.type,
        update.effective_user.id,
        context.bot_data["allowed_users"],
    )
    if error:
        await update.message.reply_text(error)
        return
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Использование: /search <запрос>")
        return
    user_id = str(update.effective_user.id)
    answer = _perform_search(
        query,
        user_id=user_id,
        indexer=context.bot_data["indexer"],
        deepseek=context.bot_data["deepseek"],
    )
    await update.message.reply_text(answer)
```

- [ ] **Step 4: Run tests to verify they pass**

```bash
cd services/bot && python -m pytest tests/test_search.py -v
```

Expected: 3 passed

- [ ] **Step 5: Run all bot tests**

```bash
cd services/bot && python -m pytest -v
```

Expected: все тесты зелёные

- [ ] **Step 6: Commit**

```bash
git add services/bot/src/handlers/search.py services/bot/tests/test_search.py
git commit -m "feat(bot): pass user_id to search, add access check to search handler"
```

---

## Task 8: bot main.py — загрузка whitelist

**Files:**
- Modify: `services/bot/src/main.py`

Здесь нет unit-тестов (main.py — точка входа), но изменение минимальное.

- [ ] **Step 1: Implement whitelist loading in main.py**

Заменить `services/bot/src/main.py`:
```python
import logging
import os

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from auth import load_whitelist
from clients.git_sync import GitSyncClient
from clients.indexer import IndexerClient
from handlers.capture import capture_handler
from handlers.search import search_handler
from llm.deepseek import DeepSeekClient

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main() -> None:
    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()

    app.bot_data["deepseek"] = DeepSeekClient(api_key=os.environ["DEEPSEEK_API_KEY"])
    app.bot_data["git_sync"] = GitSyncClient(os.getenv("GIT_SYNC_HOST", "http://git-sync:8000"))
    app.bot_data["indexer"] = IndexerClient(os.getenv("INDEXER_HOST", "http://indexer:8000"))
    app.bot_data["vault_path"] = os.getenv("VAULT_PATH", "/vault")
    app.bot_data["allowed_users"] = load_whitelist("/allowed_users.txt")

    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, capture_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Commit**

```bash
git add services/bot/src/main.py
git commit -m "feat(bot): load whitelist at startup from /allowed_users.txt"
```

---

## Task 9: docker-compose и конфиг-файлы

**Files:**
- Modify: `docker-compose.yml`
- Create: `allowed_users.txt`
- Modify: `.gitignore`

- [ ] **Step 1: Add allowed_users.txt to .gitignore**

Добавить строку в `.gitignore`:
```
allowed_users.txt
```

- [ ] **Step 2: Create allowed_users.txt template**

Создать `allowed_users.txt` в корне репо:
```
# Allowed Telegram user IDs (one per line)
# To find your ID: message @userinfobot in Telegram
# After editing: docker compose restart bot
```

- [ ] **Step 3: Mount allowed_users.txt into bot container**

В `docker-compose.yml` в секции `bot.volumes` добавить монтирование файла:
```yaml
  bot:
    build: ./services/bot
    env_file: ./services/bot/.env
    volumes:
      - vault:/vault
      - ./allowed_users.txt:/allowed_users.txt:ro
    networks:
      - internal
    depends_on:
      - git-sync
      - indexer
    restart: unless-stopped
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore allowed_users.txt docker-compose.yml
git commit -m "feat: mount allowed_users.txt into bot, add to .gitignore"
```

---

## Self-Review

**Spec coverage:**
- ✅ Whitelist-файл `/allowed_users.txt`, формат с `#` и пустыми строками — Task 1, 9
- ✅ Монтируется в контейнер, кешируется в `bot_data["allowed_users"]` — Task 8, 9
- ✅ `access_error` проверяет private chat + whitelist — Task 1, 6, 7
- ✅ Vault записывается в `/vault/{user_id}/` — Task 6
- ✅ Watcher извлекает `user_id` из пути, пропускает корневые файлы — Task 3
- ✅ ChromaDB: `user_id` в metadata при upsert, `where` фильтр при search — Task 2
- ✅ SearchRequest добавляет `user_id` — Task 4
- ✅ IndexerClient передаёт `user_id` — Task 5
- ✅ search_handler передаёт `user_id` — Task 7
- ✅ Перезагрузка whitelist через `docker compose restart bot` — Task 9 (документировано в комментарии файла)
