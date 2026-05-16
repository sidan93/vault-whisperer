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
