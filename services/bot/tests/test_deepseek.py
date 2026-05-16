from unittest.mock import MagicMock, patch
from llm.deepseek import DeepSeekClient


@patch("llm.deepseek.OpenAI")
def test_structure_note_returns_content(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = "# Note\n\nContent"

    client = DeepSeekClient(api_key="test")
    result = client.structure_note("raw text")

    assert result == "# Note\n\nContent"


@patch("llm.deepseek.OpenAI")
def test_structure_note_calls_deepseek_chat_model(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = "result"

    client = DeepSeekClient(api_key="test")
    client.structure_note("some text")

    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["model"] == "deepseek-chat"


@patch("llm.deepseek.OpenAI")
def test_synthesize_answer_includes_query_and_chunks(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = "answer"

    client = DeepSeekClient(api_key="test")
    chunks = [{"source": "note.md", "text": "relevant content", "tags": []}]
    result = client.synthesize_answer("what is python?", chunks)

    assert result == "answer"
    user_message = mock_client.chat.completions.create.call_args.kwargs["messages"][-1]["content"]
    assert "what is python?" in user_message
    assert "relevant content" in user_message


@patch("llm.deepseek.OpenAI")
def test_synthesize_answer_works_with_empty_chunks(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = "no context"

    client = DeepSeekClient(api_key="test")
    result = client.synthesize_answer("what?", [])

    assert result == "no context"
