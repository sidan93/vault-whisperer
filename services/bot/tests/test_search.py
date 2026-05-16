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
