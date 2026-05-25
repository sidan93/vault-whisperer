import re
from unittest.mock import MagicMock, patch
from handlers.capture import _filename_from_title, _assemble_note, _capture_and_save

_DATETIME_PREFIX_RE = re.compile(r"^\d{4}-\d{2}-\d{2}-\d{6}-")


def test_filename_starts_with_datetime_prefix():
    filename = _filename_from_title("My Python Note")
    assert _DATETIME_PREFIX_RE.match(filename), f"No datetime prefix: {filename}"


def test_filename_contains_title_slug():
    filename = _filename_from_title("My Python Note")
    assert filename.endswith("-my-python-note.md"), f"Missing slug: {filename}"


def test_filename_strips_special_chars():
    filename = _filename_from_title("Notes: Python & Tips!")
    assert filename.endswith(".md")
    assert ":" not in filename
    assert "&" not in filename


def test_filename_empty_title_has_only_datetime():
    filename = _filename_from_title("")
    assert re.match(r"^\d{4}-\d{2}-\d{2}-\d{6}\.md$", filename), f"Bad format: {filename}"


def test_assemble_note_body_is_raw_text():
    note = _assemble_note("Title", ["tag1"], "original text unchanged")
    assert "original text unchanged" in note


def test_assemble_note_has_correct_frontmatter():
    note = _assemble_note("My Title", ["tag1", "tag2"], "body")
    assert note.startswith("---")
    assert 'title: "My Title"' in note
    assert "tag1" in note
    assert "tag2" in note


def test_assemble_note_with_empty_tags():
    note = _assemble_note("Title", [], "body")
    assert "tags: []" in note


def test_assemble_note_escapes_quotes_in_title():
    note = _assemble_note('Title with "quotes"', [], "body")
    assert 'title: "Title with \\"quotes\\""' in note


def test_capture_and_save_body_equals_raw_input(tmp_path):
    deepseek = MagicMock()
    deepseek.generate_metadata.return_value = {"title": "Test Note", "tags": ["test"]}
    git_sync = MagicMock()

    with patch("handlers.capture.extract_urls", return_value=[]):
        with patch("handlers.capture.fetch_titles", return_value={}):
            filename = _capture_and_save(
                "my raw text", user_id="123",
                deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path),
            )

    content = (tmp_path / "123" / filename).read_text(encoding="utf-8")
    assert "my raw text" in content


def test_capture_and_save_writes_to_user_subfolder(tmp_path):
    deepseek = MagicMock()
    deepseek.generate_metadata.return_value = {"title": "Test", "tags": []}
    git_sync = MagicMock()

    with patch("handlers.capture.extract_urls", return_value=[]):
        with patch("handlers.capture.fetch_titles", return_value={}):
            filename = _capture_and_save(
                "text", user_id="42",
                deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path),
            )

    assert (tmp_path / "42" / filename).exists()


def test_capture_and_save_uses_notes_subdir(tmp_path):
    deepseek = MagicMock()
    deepseek.generate_metadata.return_value = {"title": "Test", "tags": []}
    git_sync = MagicMock()

    with patch("handlers.capture.extract_urls", return_value=[]):
        with patch("handlers.capture.fetch_titles", return_value={}):
            filename = _capture_and_save(
                "text", user_id="42",
                deepseek=deepseek, git_sync=git_sync,
                vault_path=str(tmp_path), notes_subdir="inbox",
            )

    assert (tmp_path / "inbox" / "42" / filename).exists()


def test_capture_and_save_calls_git_sync(tmp_path):
    deepseek = MagicMock()
    deepseek.generate_metadata.return_value = {"title": "Test", "tags": []}
    git_sync = MagicMock()

    with patch("handlers.capture.extract_urls", return_value=[]):
        with patch("handlers.capture.fetch_titles", return_value={}):
            _capture_and_save(
                "text", user_id="42",
                deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path),
            )

    git_sync.sync.assert_called_once()


def test_capture_and_save_passes_url_titles_to_deepseek(tmp_path):
    deepseek = MagicMock()
    deepseek.generate_metadata.return_value = {"title": "Link Note", "tags": ["ссылка"]}
    git_sync = MagicMock()

    with patch("handlers.capture.extract_urls", return_value=["https://example.com"]):
        with patch("handlers.capture.fetch_titles", return_value={"https://example.com": "Example"}):
            _capture_and_save(
                "https://example.com", user_id="42",
                deepseek=deepseek, git_sync=git_sync, vault_path=str(tmp_path),
            )

    deepseek.generate_metadata.assert_called_once_with(
        "https://example.com", {"https://example.com": "Example"}
    )
