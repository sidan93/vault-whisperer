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


def _initial_index(handler: VaultHandler, vault_path: str) -> None:
    import logging
    logger = logging.getLogger(__name__)
    for path in Path(vault_path).rglob("*.md"):
        logger.info("Initial index: %s", path)
        handler._handle(str(path))


def start_watcher(embedder: EmbedderBase, writer: ChromaWriter, vault_path: str) -> Observer:
    handler = VaultHandler(embedder=embedder, writer=writer, vault_path=vault_path)
    _initial_index(handler, vault_path)
    observer = Observer()
    observer.schedule(handler, vault_path, recursive=True)
    observer.start()
    return observer
