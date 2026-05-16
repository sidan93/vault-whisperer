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
