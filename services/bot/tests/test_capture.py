import re
from unittest.mock import MagicMock, patch
from pathlib import Path
from handlers.capture import _filename_from_content, _structure_and_save

_DATETIME_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{6}-")


def test_filename_starts_with_datetime_prefix():
    """Имя файла всегда начинается с YYYY-MM-DD-HHMMSS-"""
    content = '---\ntitle: "My Python Note"\n---\n\nContent here'
    filename = _filename_from_content(content)
    assert _DATETIME_PREFIX_RE.match(filename), f"Нет datetime-префикса: {filename}"


def test_filename_contains_title_slug():
    """После datetime-префикса идёт slug из заголовка"""
    content = '---\ntitle: "My Python Note"\n---\n\nContent here'
    filename = _filename_from_content(content)
    assert filename.endswith("-my-python-note.md"), f"Нет slug заголовка: {filename}"


def test_filename_strips_special_chars():
    content = '---\ntitle: "Notes: Python & Tips!"\n---\n\nContent'
    filename = _filename_from_content(content)
    assert filename.endswith(".md")
    assert ":" not in filename
    assert "&" not in filename


def test_filename_without_title_has_only_datetime():
    """Без title — только datetime, без лишних дефисов"""
    content = "# Header\n\nNo frontmatter here"
    filename = _filename_from_content(content)
    # формат: YYYY-MM-DD-HHMMSS.md (без trailing dash перед .md)
    assert re.match(r"^\d{4}-\d{2}-\d{2}-\d{6}\.md$", filename), (
        f"Неверный формат без заголовка: {filename}"
    )


def test_structure_and_save_writes_to_user_subfolder(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = '---\ntitle: "Test Note"\n---\n\nContent'
    git_sync = MagicMock()

    filename = _structure_and_save("raw input", user_id="123", deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path))

    saved_file = tmp_path / "123" / filename
    assert saved_file.exists()
    assert saved_file.read_text(encoding="utf-8") == '---\ntitle: "Test Note"\n---\n\nContent'


def test_structure_and_save_creates_user_dir_if_missing(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = "# Note\n\nContent"
    git_sync = MagicMock()

    _structure_and_save("raw input", user_id="987", deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path))

    assert (tmp_path / "987").is_dir()


def test_structure_and_save_uses_notes_subdir(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = '---\ntitle: "Test Note"\n---\n\nContent'
    git_sync = MagicMock()

    filename = _structure_and_save(
        "raw input", user_id="123", deepseek=deepseek, git_sync=git_sync,
        vault_path=str(tmp_path), notes_subdir="inbox"
    )

    saved_file = tmp_path / "inbox" / "123" / filename
    assert saved_file.exists()


def test_structure_and_save_without_notes_subdir_keeps_root_behavior(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = '---\ntitle: "Test Note"\n---\n\nContent'
    git_sync = MagicMock()

    filename = _structure_and_save(
        "raw input", user_id="123", deepseek=deepseek, git_sync=git_sync,
        vault_path=str(tmp_path)
    )

    saved_file = tmp_path / "123" / filename
    assert saved_file.exists()


def test_structure_and_save_calls_git_sync(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = "# Note\n\nContent"
    git_sync = MagicMock()

    _structure_and_save("raw input", user_id="123", deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path))

    git_sync.sync.assert_called_once()


def test_structure_and_save_passes_text_to_deepseek(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = "# Note\n\nContent"
    git_sync = MagicMock()

    _structure_and_save("my raw text", user_id="123", deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path))

    deepseek.structure_note.assert_called_once_with("my raw text")
