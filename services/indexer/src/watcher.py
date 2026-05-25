import os
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from chunker import chunk_markdown
from chroma_writer import ChromaWriter
from embedder.base import EmbedderBase


class VaultHandler(FileSystemEventHandler):
    def __init__(self, embedder: EmbedderBase, writer: ChromaWriter, vault_path: str, notes_subdir: str = "") -> None:
        self._embedder = embedder
        self._writer = writer
        self._vault_path = vault_path
        self._notes_subdir = notes_subdir

    def _handle(self, path: str) -> None:
        if not path.endswith(".md"):
            return
        source = os.path.relpath(path, self._vault_path)
        parts = Path(source).parts
        # Если файл лежит в notes_subdir (inbox/<user_id>/...), user_id — второй уровень
        if self._notes_subdir and parts[0] == self._notes_subdir:
            if len(parts) < 3:
                return
            user_id = parts[1]
        else:
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
    files = list(Path(vault_path).rglob("*.md"))
    print(f"[initial_index] found {len(files)} .md files in {vault_path}", flush=True)
    for path in files:
        print(f"[initial_index] indexing {path}", flush=True)
        try:
            handler._handle(str(path))
        except Exception as e:
            print(f"[initial_index] ERROR {path}: {e}", flush=True)


def start_watcher(embedder: EmbedderBase, writer: ChromaWriter, vault_path: str, notes_subdir: str = "") -> Observer:
    handler = VaultHandler(embedder=embedder, writer=writer, vault_path=vault_path, notes_subdir=notes_subdir)
    _initial_index(handler, vault_path)
    observer = Observer()
    observer.schedule(handler, vault_path, recursive=True)
    observer.start()
    return observer
