import os
import pytest
from unittest.mock import MagicMock, patch, call
from watchdog.events import FileCreatedEvent, FileModifiedEvent, DirModifiedEvent
from watcher import VaultHandler


@pytest.fixture
def handler():
    embedder = MagicMock()
    embedder.embed.return_value = [[0.1, 0.2]]
    writer = MagicMock()
    return VaultHandler(embedder=embedder, writer=writer, vault_path="/vault")


def test_on_created_indexes_md_file(handler, tmp_path):
    handler._vault_path = str(tmp_path)
    md_file = tmp_path / "note.md"
    md_file.write_text("# Title\n\n" + "Content " * 20, encoding="utf-8")
    event = FileCreatedEvent(str(md_file))
    handler.on_created(event)
    handler._writer.upsert_file.assert_called_once()


def test_on_modified_indexes_md_file(handler, tmp_path):
    handler._vault_path = str(tmp_path)
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
