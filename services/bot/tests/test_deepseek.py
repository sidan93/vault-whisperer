from unittest.mock import MagicMock, patch
from llm.deepseek import DeepSeekClient


# --- generate_metadata ---

@patch("llm.deepseek.OpenAI")
def test_generate_metadata_returns_title_and_tags(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        'title: "My Note"\ntags:\n  - python\n  - dev'
    )
    client = DeepSeekClient(api_key="test")
    result = client.generate_metadata("some text about python")
    assert result["title"] == "My Note"
    assert result["tags"] == ["python", "dev"]


@patch("llm.deepseek.OpenAI")
def test_generate_metadata_uses_temperature_zero(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        'title: "T"\ntags: []'
    )
    client = DeepSeekClient(api_key="test")
    client.generate_metadata("text")
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["temperature"] == 0


@patch("llm.deepseek.OpenAI")
def test_generate_metadata_includes_url_titles_in_prompt(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        'title: "T"\ntags:\n  - ссылка'
    )
    client = DeepSeekClient(api_key="test")
    client.generate_metadata(
        "https://example.com",
        {"https://example.com": "Example Page"},
    )
    user_msg = mock_client.chat.completions.create.call_args.kwargs["messages"][-1]["content"]
    assert "Example Page" in user_msg
    assert "https://example.com" in user_msg


@patch("llm.deepseek.OpenAI")
def test_generate_metadata_omits_url_section_when_no_urls(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        'title: "T"\ntags: []'
    )
    client = DeepSeekClient(api_key="test")
    client.generate_metadata("plain text", {})
    user_msg = mock_client.chat.completions.create.call_args.kwargs["messages"][-1]["content"]
    assert "Fetched page titles" not in user_msg


@patch("llm.deepseek.OpenAI")
def test_generate_metadata_strips_frontmatter_markers(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        '---\ntitle: "Wrapped"\ntags:\n  - test\n---'
    )
    client = DeepSeekClient(api_key="test")
    result = client.generate_metadata("text")
    assert result["title"] == "Wrapped"
    assert result["tags"] == ["test"]


@patch("llm.deepseek.OpenAI")
def test_generate_metadata_fallback_on_invalid_yaml(mock_openai):
    mock_client = MagicMock()
    mock_openai.return_value = mock_client
    mock_client.chat.completions.create.return_value.choices[0].message.content = (
        "not yaml at all!!!"
    )
    client = DeepSeekClient(api_key="test")
    result = client.generate_metadata("some text")
    assert "title" in result
    assert isinstance(result["tags"], list)


# --- synthesize_answer (unchanged) ---

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
