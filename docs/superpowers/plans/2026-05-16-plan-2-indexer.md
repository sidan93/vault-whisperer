# Indexer Service Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать indexer-сервис: следит за vault на предмет изменений .md-файлов, нарезает на чанки, эмбедит через Google API, хранит в ChromaDB, и выставляет POST /search для бота.

**Architecture:** Один Python-процесс: FastAPI-сервер (POST /search) + watchdog-observer в фоновом треде, запускаемый через lifespan. Изменение файла → чанки → Google embeddings → upsert в ChromaDB. Поиск → embed query → query ChromaDB → top-K чанков. EmbedderBase обёртывает провайдера: смена провайдера = новый файл без касания остального кода.

**Tech Stack:** Python 3.13, FastAPI, google-generativeai, chromadb (HttpClient в проде, EphemeralClient в тестах), watchdog, pytest

---

## File Map

```
services/indexer/
├── requirements-dev.txt        (pytest, httpx — уже разделены в Plan 1)
├── requirements.txt
└── src/
    ├── embedder/
    │   ├── __init__.py
    │   ├── base.py             (EmbedderBase ABC)
    │   └── google.py           (GoogleEmbedder)
    ├── chunker.py              (chunk_markdown → list[Chunk])
    ├── chroma_writer.py        (ChromaWriter: upsert_file + search)
    ├── watcher.py              (VaultHandler + start_watcher)
    └── main.py                 (FastAPI lifespan + POST /search)
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_embedder.py
    ├── test_chunker.py
    ├── test_chroma_writer.py
    ├── test_watcher.py
    └── test_api.py
```

---

### Task 1: Test infrastructure + EmbedderBase

**Files:**
- Create: `services/indexer/tests/__init__.py`
- Create: `services/indexer/tests/conftest.py`
- Create: `services/indexer/src/embedder/__init__.py`
- Create: `services/indexer/src/embedder/base.py`
- Create: `services/indexer/tests/test_embedder.py`

- [ ] **Step 1: Создать test infrastructure**

`services/indexer/tests/__init__.py`: пустой файл

`services/indexer/tests/conftest.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

`services/indexer/src/embedder/__init__.py`: пустой файл

- [ ] **Step 2: Написать падающий тест**

`services/indexer/tests/test_embedder.py`:
```python
import pytest
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
```

- [ ] **Step 3: Запустить тест — убедиться что падает**

```bash
cd services/indexer
pip install pytest
python -m pytest tests/test_embedder.py -v
```
Ожидаемо: `ModuleNotFoundError: No module named 'embedder.base'`

- [ ] **Step 4: Реализовать EmbedderBase**

`services/indexer/src/embedder/base.py`:
```python
from abc import ABC, abstractmethod


class EmbedderBase(ABC):
    @abstractmethod
    def embed(self, texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
        ...
```

- [ ] **Step 5: Запустить тест — убедиться что проходит**

```bash
python -m pytest tests/test_embedder.py -v
```
Ожидаемо: `3 passed`

- [ ] **Step 6: Commit**

```bash
cd E:\petproject\vault-whisperer
git add services/indexer/tests/ services/indexer/src/embedder/
git commit -m "feat(indexer): add EmbedderBase abstract interface"
```

---

### Task 2: GoogleEmbedder (TDD)

**Files:**
- Create: `services/indexer/src/embedder/google.py`
- Modify: `services/indexer/tests/test_embedder.py`

- [ ] **Step 1: Написать падающий тест**

Добавить в конец `services/indexer/tests/test_embedder.py`:
```python
from unittest.mock import patch, MagicMock
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
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd services/indexer
python -m pytest tests/test_embedder.py -v
```
Ожидаемо: `ModuleNotFoundError: No module named 'embedder.google'`

- [ ] **Step 3: Реализовать GoogleEmbedder**

`services/indexer/src/embedder/google.py`:
```python
import os
import google.generativeai as genai
from embedder.base import EmbedderBase


class GoogleEmbedder(EmbedderBase):
    def __init__(self) -> None:
        genai.configure(api_key=os.getenv("GOOGLE_API_KEY", ""))
        self._model = "models/text-embedding-004"

    def embed(self, texts: list[str], task_type: str = "retrieval_document") -> list[list[float]]:
        results = []
        for text in texts:
            response = genai.embed_content(
                model=self._model,
                content=text,
                task_type=task_type,
            )
            results.append(response["embedding"])
        return results
```

- [ ] **Step 4: Установить deps и запустить тесты**

```bash
cd services/indexer
pip install google-generativeai pytest
python -m pytest tests/test_embedder.py -v
```
Ожидаемо: `6 passed`

- [ ] **Step 5: Commit**

```bash
cd E:\petproject\vault-whisperer
git add services/indexer/src/embedder/google.py services/indexer/tests/test_embedder.py
git commit -m "feat(indexer): implement GoogleEmbedder with task_type support"
```

---

### Task 3: Chunker (TDD)

**Files:**
- Create: `services/indexer/tests/test_chunker.py`
- Create: `services/indexer/src/chunker.py`

- [ ] **Step 1: Написать падающий тест**

`services/indexer/tests/test_chunker.py`:
```python
from chunker import chunk_markdown, Chunk


def test_returns_chunk_dataclass():
    content = "# Header\n\nSome content here that is long enough to be a chunk."
    chunks = chunk_markdown(content, source="note.md")
    assert len(chunks) > 0
    assert isinstance(chunks[0], Chunk)


def test_extracts_tags_from_frontmatter():
    content = "---\ntags: [python, tips]\n---\n\n# Note\n\nContent that is long enough."
    chunks = chunk_markdown(content, source="note.md")
    assert chunks[0].tags == ["python", "tips"]


def test_no_frontmatter_returns_empty_tags():
    content = "# Header\n\nContent without frontmatter that is long enough to pass."
    chunks = chunk_markdown(content, source="note.md")
    assert chunks[0].tags == []


def test_source_is_set_on_all_chunks():
    content = "# H1\n\nFirst section with enough content.\n\n## H2\n\nSecond section with enough content."
    chunks = chunk_markdown(content, source="path/to/note.md")
    assert all(c.source == "path/to/note.md" for c in chunks)


def test_chunk_index_is_sequential():
    content = "# H1\n\nFirst section with enough content.\n\n## H2\n\nSecond section with enough content."
    chunks = chunk_markdown(content, source="note.md")
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_short_content_returns_single_chunk():
    content = "# Title\n\nShort."
    chunks = chunk_markdown(content, source="note.md", min_length=1)
    assert len(chunks) >= 1


def test_empty_content_returns_no_chunks():
    chunks = chunk_markdown("", source="note.md")
    assert chunks == []


def test_sections_below_min_length_are_skipped():
    content = "# H1\n\nTiny.\n\n## H2\n\n" + "Long enough content. " * 10
    chunks = chunk_markdown(content, source="note.md", min_length=50)
    assert all(len(c.text) >= 50 for c in chunks)
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd services/indexer
python -m pytest tests/test_chunker.py -v
```
Ожидаемо: `ModuleNotFoundError: No module named 'chunker'`

- [ ] **Step 3: Реализовать chunker.py**

`services/indexer/src/chunker.py`:
```python
import re
from dataclasses import dataclass, field


@dataclass
class Chunk:
    text: str
    source: str
    tags: list[str]
    chunk_index: int


def _parse_frontmatter(content: str) -> tuple[list[str], str]:
    if not content.startswith("---"):
        return [], content
    end = content.find("---", 3)
    if end == -1:
        return [], content
    frontmatter = content[3:end]
    body = content[end + 3 :].lstrip("\n")
    match = re.search(r"tags:\s*\[([^\]]*)\]", frontmatter)
    if match:
        tags = [t.strip().strip("\"'") for t in match.group(1).split(",") if t.strip()]
    else:
        tags = []
    return tags, body


def chunk_markdown(content: str, source: str, min_length: int = 100) -> list[Chunk]:
    if not content.strip():
        return []
    tags, body = _parse_frontmatter(content)
    sections = re.split(r"\n(?=#{1,6} )", body)
    chunks = []
    for section in sections:
        section = section.strip()
        if len(section) >= min_length:
            chunks.append(
                Chunk(text=section, source=source, tags=tags, chunk_index=len(chunks))
            )
    if not chunks and body.strip():
        chunks.append(Chunk(text=body.strip(), source=source, tags=tags, chunk_index=0))
    return chunks
```

- [ ] **Step 4: Запустить тесты**

```bash
python -m pytest tests/test_chunker.py -v
```
Ожидаемо: `8 passed`

- [ ] **Step 5: Commit**

```bash
cd E:\petproject\vault-whisperer
git add services/indexer/src/chunker.py services/indexer/tests/test_chunker.py
git commit -m "feat(indexer): implement markdown chunker with frontmatter tag extraction"
```

---

### Task 4: ChromaWriter (TDD)

**Files:**
- Create: `services/indexer/tests/test_chroma_writer.py`
- Create: `services/indexer/src/chroma_writer.py`

- [ ] **Step 1: Написать падающий тест**

`services/indexer/tests/test_chroma_writer.py`:
```python
import chromadb
import pytest
from chroma_writer import ChromaWriter


@pytest.fixture
def writer():
    client = chromadb.EphemeralClient()
    return ChromaWriter(client)


def test_upsert_adds_chunks(writer):
    writer.upsert_file(
        source="notes/test.md",
        chunks=["chunk one content", "chunk two content"],
        embeddings=[[0.1, 0.2], [0.3, 0.4]],
        tags=["python"],
    )
    results = writer.search([0.1, 0.2], n_results=5)
    assert len(results) == 2


def test_upsert_replaces_existing_chunks(writer):
    writer.upsert_file(
        source="notes/test.md",
        chunks=["old chunk one", "old chunk two", "old chunk three"],
        embeddings=[[0.1, 0.2], [0.3, 0.4], [0.5, 0.6]],
        tags=[],
    )
    writer.upsert_file(
        source="notes/test.md",
        chunks=["new chunk one"],
        embeddings=[[0.1, 0.2]],
        tags=[],
    )
    results = writer.search([0.1, 0.2], n_results=10)
    sources = [r["source"] for r in results]
    assert sources.count("notes/test.md") == 1


def test_search_returns_source_and_tags(writer):
    writer.upsert_file(
        source="notes/python.md",
        chunks=["Python is a programming language"],
        embeddings=[[0.1, 0.2, 0.3]],
        tags=["python", "programming"],
    )
    results = writer.search([0.1, 0.2, 0.3], n_results=1)
    assert results[0]["source"] == "notes/python.md"
    assert "python" in results[0]["tags"]


def test_search_returns_empty_when_no_data(writer):
    results = writer.search([0.1, 0.2], n_results=5)
    assert results == []
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd services/indexer
pip install chromadb
python -m pytest tests/test_chroma_writer.py -v
```
Ожидаемо: `ModuleNotFoundError: No module named 'chroma_writer'`

- [ ] **Step 3: Реализовать ChromaWriter**

`services/indexer/src/chroma_writer.py`:
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
                {"source": source, "tags": ",".join(tags), "chunk_index": i}
                for i in range(len(chunks))
            ],
        )

    def search(self, query_embedding: list[float], n_results: int = 5) -> list[dict]:
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
```

- [ ] **Step 4: Запустить тесты**

```bash
python -m pytest tests/test_chroma_writer.py -v
```
Ожидаемо: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd E:\petproject\vault-whisperer
git add services/indexer/src/chroma_writer.py services/indexer/tests/test_chroma_writer.py
git commit -m "feat(indexer): implement ChromaWriter with upsert and search"
```

---

### Task 5: VaultHandler / watcher (TDD)

**Files:**
- Create: `services/indexer/tests/test_watcher.py`
- Create: `services/indexer/src/watcher.py`

- [ ] **Step 1: Написать падающий тест**

`services/indexer/tests/test_watcher.py`:
```python
import os
from unittest.mock import MagicMock, patch, call
from watchdog.events import FileCreatedEvent, FileModifiedEvent, DirModifiedEvent
from watcher import VaultHandler


@pytest.fixture
def handler():
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1, 0.2]]
    writer = MagicMock()
    return VaultHandler(embedder=embedder, writer=writer, vault_path="/vault")


import pytest


def test_on_created_indexes_md_file(handler, tmp_path):
    md_file = tmp_path / "note.md"
    md_file.write_text("# Title\n\n" + "Content " * 20, encoding="utf-8")
    event = FileCreatedEvent(str(md_file))
    handler.on_created(event)
    handler._writer.upsert_file.assert_called_once()


def test_on_modified_indexes_md_file(handler, tmp_path):
    md_file = tmp_path / "note.md"
    md_file.write_text("# Title\n\n" + "Content " * 20, encoding="utf-8")
    event = FileModifiedEvent(str(md_file))
    handler.on_modified(event)
    handler._writer.upsert_file.assert_called_once()


def test_non_md_files_are_ignored(handler, tmp_path):
    txt_file = tmp_path / "note.txt"
    txt_file.write_text("some text", encoding="utf-8")
    event = FileCreatedEvent(str(txt_file))
    handler.on_created(event)
    handler._writer.upsert_file.assert_not_called()


def test_directory_events_are_ignored(handler):
    event = DirModifiedEvent("/vault/somedir")
    handler.on_modified(event)
    handler._writer.upsert_file.assert_not_called()


def test_upsert_called_with_correct_source(handler, tmp_path):
    vault_path = str(tmp_path)
    handler._vault_path = vault_path
    md_file = tmp_path / "my_note.md"
    md_file.write_text("# Title\n\n" + "Content " * 20, encoding="utf-8")
    event = FileCreatedEvent(str(md_file))
    handler.on_created(event)
    call_kwargs = handler._writer.upsert_file.call_args.kwargs
    assert call_kwargs["source"] == "my_note.md"
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd services/indexer
pip install watchdog
python -m pytest tests/test_watcher.py -v
```
Ожидаемо: `ModuleNotFoundError: No module named 'watcher'`

- [ ] **Step 3: Реализовать watcher.py**

`services/indexer/src/watcher.py`:
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

- [ ] **Step 4: Запустить тесты**

```bash
python -m pytest tests/test_watcher.py -v
```
Ожидаемо: `5 passed`

- [ ] **Step 5: Commit**

```bash
cd E:\petproject\vault-whisperer
git add services/indexer/src/watcher.py services/indexer/tests/test_watcher.py
git commit -m "feat(indexer): implement VaultHandler watchdog with file indexing"
```

---

### Task 6: FastAPI main.py с POST /search (TDD)

**Files:**
- Create: `services/indexer/tests/test_api.py`
- Modify: `services/indexer/src/main.py` (заменить stub)

- [ ] **Step 1: Написать падающий тест**

`services/indexer/tests/test_api.py`:
```python
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from main import app


def test_search_returns_results():
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.1, 0.2, 0.3]]
    mock_writer = MagicMock()
    mock_writer.search.return_value = [
        {"text": "chunk content", "source": "note.md", "tags": ["python"]}
    ]

    with patch("main._embedder", mock_embedder), patch("main._writer", mock_writer):
        client = TestClient(app)
        response = client.post("/search", json={"query": "how does python work?"})

    assert response.status_code == 200
    data = response.json()
    assert len(data["results"]) == 1
    assert data["results"][0]["source"] == "note.md"
    mock_embedder.embed.assert_called_once_with(
        ["how does python work?"], task_type="retrieval_query"
    )


def test_search_returns_empty_list_when_no_results():
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.1, 0.2]]
    mock_writer = MagicMock()
    mock_writer.search.return_value = []

    with patch("main._embedder", mock_embedder), patch("main._writer", mock_writer):
        client = TestClient(app)
        response = client.post("/search", json={"query": "unknown topic"})

    assert response.status_code == 200
    assert response.json() == {"results": []}


def test_search_passes_n_results_to_writer():
    mock_embedder = MagicMock()
    mock_embedder.embed.return_value = [[0.1]]
    mock_writer = MagicMock()
    mock_writer.search.return_value = []

    with patch("main._embedder", mock_embedder), patch("main._writer", mock_writer):
        client = TestClient(app)
        client.post("/search", json={"query": "test", "n_results": 3})

    mock_writer.search.assert_called_once()
    assert mock_writer.search.call_args.kwargs["n_results"] == 3
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd services/indexer
pip install fastapi httpx uvicorn
python -m pytest tests/test_api.py -v
```
Ожидаемо: `ImportError` или тест падает (stub main.py ничего не экспортирует)

- [ ] **Step 3: Реализовать main.py**

`services/indexer/src/main.py`:
```python
import os
from contextlib import asynccontextmanager

import chromadb
from fastapi import FastAPI
from pydantic import BaseModel

from chroma_writer import ChromaWriter
from embedder.google import GoogleEmbedder
from watcher import start_watcher

_VAULT_PATH = os.getenv("VAULT_PATH", "/vault")
_CHROMA_HOST = os.getenv("CHROMA_HOST", "http://chromadb:8000")

_embedder: GoogleEmbedder | None = None
_writer: ChromaWriter | None = None
_observer = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _embedder, _writer, _observer
    h, _, p = _CHROMA_HOST.removeprefix("http://").partition(":")
    client = chromadb.HttpClient(host=h, port=int(p) if p else 8000)
    _embedder = GoogleEmbedder()
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
```

- [ ] **Step 4: Запустить все тесты сервиса**

```bash
cd services/indexer
python -m pytest tests/ -v
```
Ожидаемо: все тесты проходят (3 + 6 + 8 + 4 + 5 + 3 = 29 expected)

- [ ] **Step 5: Commit**

```bash
cd E:\petproject\vault-whisperer
git add services/indexer/src/main.py services/indexer/tests/test_api.py
git commit -m "feat(indexer): add FastAPI POST /search with lifespan watcher startup"
```
