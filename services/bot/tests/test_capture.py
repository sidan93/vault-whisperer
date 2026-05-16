from unittest.mock import MagicMock
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


def test_structure_and_save_writes_file(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = '---\ntitle: "Test Note"\n---\n\nContent'
    git_sync = MagicMock()

    filename = _structure_and_save("raw input", deepseek, git_sync, str(tmp_path))

    saved_file = tmp_path / filename
    assert saved_file.exists()
    assert saved_file.read_text(encoding="utf-8") == '---\ntitle: "Test Note"\n---\n\nContent'


def test_structure_and_save_calls_git_sync(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = "# Note\n\nContent"
    git_sync = MagicMock()

    _structure_and_save("raw input", deepseek, git_sync, str(tmp_path))

    git_sync.sync.assert_called_once()


def test_structure_and_save_passes_text_to_deepseek(tmp_path):
    deepseek = MagicMock()
    deepseek.structure_note.return_value = "# Note\n\nContent"
    git_sync = MagicMock()

    _structure_and_save("my raw text", deepseek, git_sync, str(tmp_path))

    deepseek.structure_note.assert_called_once_with("my raw text")
