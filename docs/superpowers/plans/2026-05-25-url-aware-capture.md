# URL-aware Capture Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Переделать capture-pipeline бота так, чтобы body заметки всегда был оригинальным текстом пользователя, LLM генерировал только frontmatter (title + tags), а заголовки URL-страниц получались через Python httpx.

**Architecture:** Новый модуль `url_fetcher.py` извлекает URL из текста и делает HTTP-запросы за `<title>`. DeepSeek получает оригинальный текст + fetched titles и возвращает только YAML-фронтматтер (два поля: title, tags). `capture.py` собирает `.md` сам: frontmatter + сырой текст пользователя.

**Tech Stack:** Python 3.13, httpx (уже есть в requirements.txt), PyYAML (добавить), openai SDK (уже есть), pytest.

---

## Карта файлов

| Действие | Файл |
|---|---|
| Создать | `services/bot/src/url_fetcher.py` |
| Создать | `services/bot/tests/test_url_fetcher.py` |
| Изменить | `services/bot/requirements.txt` — добавить PyYAML |
| Изменить | `services/bot/src/llm/deepseek.py` — добавить `generate_metadata`, удалить `structure_note` |
| Заменить | `services/bot/tests/test_deepseek.py` — тесты для `generate_metadata` |
| Заменить | `services/bot/src/handlers/capture.py` — новый pipeline |
| Заменить | `services/bot/tests/test_capture.py` — тесты нового pipeline |

---

## Task 1: url_fetcher — извлечение URL и получение заголовков

**Files:**
- Create: `services/bot/src/url_fetcher.py`
- Create: `services/bot/tests/test_url_fetcher.py`

- [ ] **Step 1: Написать падающие тесты для extract_urls**

Создать `services/bot/tests/test_url_fetcher.py`:

```python
from unittest.mock import patch, MagicMock
import httpx
from url_fetcher import extract_urls, fetch_titles, SKIP_DOMAINS


def test_extract_urls_finds_https_url():
    assert extract_urls("Check this: https://example.com") == ["https://example.com"]


def test_extract_urls_finds_multiple_urls():
    text = "See https://example.com and https://github.com/repo"
    assert extract_urls(text) == ["https://example.com", "https://github.com/repo"]


def test_extract_urls_returns_empty_for_plain_text():
    assert extract_urls("no links here") == []


def test_extract_urls_finds_url_only_message():
    url = "https://x.com/_guillecasaus/status/123"
    assert extract_urls(url) == [url]
```

- [ ] **Step 2: Запустить — убедиться что падают**

```
cd services/bot && python -m pytest tests/test_url_fetcher.py -v
```

Ожидаемо: `ModuleNotFoundError: No module named 'url_fetcher'`

- [ ] **Step 3: Создать `services/bot/src/url_fetcher.py` с extract_urls**

```python
import re
import httpx

_URL_RE = re.compile(r"https?://[^\s<>\"']+")
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)

SKIP_DOMAINS: frozenset[str] = frozenset({
    "twitter.com",
    "x.com",
    "instagram.com",
    "t.me",
    "facebook.com",
})


def extract_urls(text: str) -> list[str]:
    return _URL_RE.findall(text)


def _should_skip(url: str) -> bool:
    return any(domain in url for domain in SKIP_DOMAINS)


def fetch_titles(urls: list[str]) -> dict[str, str | None]:
    result: dict[str, str | None] = {}
    for url in urls:
        if _should_skip(url):
            result[url] = None
            continue
        try:
            response = httpx.get(
                url,
                timeout=5.0,
                follow_redirects=True,
                headers={"User-Agent": "Mozilla/5.0 (compatible; VaultWhisperer/1.0)"},
            )
            match = _TITLE_RE.search(response.text)
            result[url] = match.group(1).strip() if match else None
        except Exception:
            result[url] = None
    return result
```

- [ ] **Step 4: Запустить extract_urls тесты — убедиться что зелёные**

```
cd services/bot && python -m pytest tests/test_url_fetcher.py::test_extract_urls_finds_https_url tests/test_url_fetcher.py::test_extract_urls_finds_multiple_urls tests/test_url_fetcher.py::test_extract_urls_returns_empty_for_plain_text tests/test_url_fetcher.py::test_extract_urls_finds_url_only_message -v
```

Ожидаемо: 4 PASSED

- [ ] **Step 5: Написать падающие тесты для fetch_titles**

Добавить в `services/bot/tests/test_url_fetcher.py`:

```python
def test_fetch_titles_skips_twitter():
    result = fetch_titles(["https://twitter.com/user/status/123"])
    assert result == {"https://twitter.com/user/status/123": None}


def test_fetch_titles_skips_x_com():
    result = fetch_titles(["https://x.com/user/status/123"])
    assert result == {"https://x.com/user/status/123": None}


def test_fetch_titles_skips_instagram():
    result = fetch_titles(["https://instagram.com/p/abc"])
    assert result == {"https://instagram.com/p/abc": None}


def test_fetch_titles_returns_none_on_timeout():
    with patch("url_fetcher.httpx.get", side_effect=httpx.TimeoutException("timeout")):
        result = fetch_titles(["https://example.com"])
    assert result == {"https://example.com": None}


def test_fetch_titles_returns_page_title():
    mock_response = MagicMock()
    mock_response.text = "<html><head><title>Hello World</title></head></html>"
    with patch("url_fetcher.httpx.get", return_value=mock_response):
        result = fetch_titles(["https://example.com"])
    assert result == {"https://example.com": "Hello World"}


def test_fetch_titles_returns_none_when_no_title_tag():
    mock_response = MagicMock()
    mock_response.text = "<html><body>No title here</body></html>"
    with patch("url_fetcher.httpx.get", return_value=mock_response):
        result = fetch_titles(["https://example.com"])
    assert result == {"https://example.com": None}


def test_fetch_titles_handles_empty_list():
    assert fetch_titles([]) == {}
```

- [ ] **Step 6: Запустить тесты fetch_titles — убедиться что зелёные**

```
cd services/bot && python -m pytest tests/test_url_fetcher.py -v
```

Ожидаемо: все 11 PASSED

- [ ] **Step 7: Коммит**

```
cd services/bot && git add src/url_fetcher.py tests/test_url_fetcher.py
git commit -m "feat(bot): add url_fetcher module for URL extraction and title fetching"
```

---

## Task 2: deepseek.generate_metadata

**Files:**
- Modify: `services/bot/requirements.txt`
- Modify: `services/bot/src/llm/deepseek.py`
- Replace: `services/bot/tests/test_deepseek.py`

- [ ] **Step 1: Добавить PyYAML в requirements.txt**

В `services/bot/requirements.txt` добавить строку:

```
PyYAML==6.0.2
```

Итоговый файл:
```
python-telegram-bot==21.6
openai==1.51.0
httpx==0.27.2
PyYAML==6.0.2
```

- [ ] **Step 2: Установить PyYAML локально**

```
cd services/bot && pip install PyYAML==6.0.2
```

- [ ] **Step 3: Написать падающие тесты для generate_metadata**

Полностью заменить `services/bot/tests/test_deepseek.py`:

```python
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
```

- [ ] **Step 4: Запустить тесты — убедиться что generate_metadata тесты падают**

```
cd services/bot && python -m pytest tests/test_deepseek.py -v
```

Ожидаемо: `AttributeError: 'DeepSeekClient' object has no attribute 'generate_metadata'`

- [ ] **Step 5: Обновить `services/bot/src/llm/deepseek.py`**

Полностью заменить файл:

```python
import re
import yaml
from openai import OpenAI

_METADATA_PROMPT = """\
Extract a title and tags from the user's message.
Return ONLY valid YAML frontmatter with two fields: title and tags.
Do not add any other content or explanation.

Rules:
- title: concise, descriptive, in the same language as the message
- tags: relevant keywords; if the message contains URLs, always include "ссылка"
- Do not rewrite or summarize the message body"""

_SYNTHESIS_PROMPT = """\
Answer the question using context from the user's personal notes.
Be concise. Reference source notes by filename when relevant.
If the context is insufficient, say so honestly.
Respond in the same language as the question."""


def _parse_metadata(response: str) -> dict[str, str | list]:
    text = response.strip()
    match = re.search(r"---\s*\n(.*?)(?:\n---|\Z)", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            title = str(data.get("title", "")).strip()
            tags = [str(t).strip() for t in (data.get("tags") or []) if t]
            if title:
                return {"title": title, "tags": tags}
    except Exception:
        pass
    return {"title": response.strip()[:60], "tags": []}


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com") -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def generate_metadata(
        self,
        text: str,
        url_titles: dict[str, str | None] | None = None,
    ) -> dict[str, str | list]:
        user_content = f"Message: {text}"
        if url_titles:
            lines = ["\n\nFetched page titles:"]
            for url, title in url_titles.items():
                t = f'"{title}"' if title else "(недоступно)"
                lines.append(f"- {url} → {t}")
            user_content += "\n".join(lines)

        response = self._client.chat.completions.create(
            model="deepseek-chat",
            temperature=0,
            messages=[
                {"role": "system", "content": _METADATA_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("DeepSeek returned no content")
        return _parse_metadata(content)

    def synthesize_answer(self, query: str, chunks: list[dict]) -> str:
        context = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)
        response = self._client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYNTHESIS_PROMPT},
                {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("DeepSeek returned no content")
        return content
```

- [ ] **Step 6: Запустить все тесты deepseek — убедиться что зелёные**

```
cd services/bot && python -m pytest tests/test_deepseek.py -v
```

Ожидаемо: 8 PASSED

- [ ] **Step 7: Коммит**

```
cd services/bot && git add requirements.txt src/llm/deepseek.py tests/test_deepseek.py
git commit -m "feat(bot): replace structure_note with generate_metadata (LLM metadata-only, temperature=0)"
```

---

## Task 3: capture handler — новый pipeline

**Files:**
- Replace: `services/bot/src/handlers/capture.py`
- Replace: `services/bot/tests/test_capture.py`

- [ ] **Step 1: Написать новые тесты для capture**

Полностью заменить `services/bot/tests/test_capture.py`:

```python
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
```

- [ ] **Step 2: Запустить — убедиться что тесты падают**

```
cd services/bot && python -m pytest tests/test_capture.py -v
```

Ожидаемо: `ImportError: cannot import name '_filename_from_title' from 'handlers.capture'`

- [ ] **Step 3: Заменить `services/bot/src/handlers/capture.py`**

```python
import re
import datetime
from pathlib import Path

from auth import access_error
from url_fetcher import extract_urls, fetch_titles


def _filename_from_title(title: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    if slug:
        return f"{timestamp}-{slug}.md"
    return f"{timestamp}.md"


def _assemble_note(title: str, tags: list[str], raw_text: str) -> str:
    date = datetime.date.today().isoformat()
    if tags:
        tags_block = "tags:\n" + "\n".join(f"  - {t}" for t in tags)
    else:
        tags_block = "tags: []"
    frontmatter = f'---\ntitle: "{title}"\ndate: {date}\n{tags_block}\n---'
    return f"{frontmatter}\n\n{raw_text}"


def _capture_and_save(
    text: str,
    user_id: str,
    deepseek,
    git_sync,
    vault_path: str,
    notes_subdir: str = "",
) -> str:
    urls = extract_urls(text)
    url_titles = fetch_titles(urls)
    metadata = deepseek.generate_metadata(text, url_titles)
    title = metadata["title"]
    tags = metadata["tags"]
    note = _assemble_note(title, tags, text)
    filename = _filename_from_title(title)
    base = Path(vault_path, notes_subdir) if notes_subdir else Path(vault_path)
    user_dir = base / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / filename).write_text(note, encoding="utf-8")
    git_sync.sync()
    return filename


async def capture_handler(update, context) -> None:
    error = access_error(
        update.effective_chat.type,
        update.effective_user.id,
        context.bot_data["allowed_users"],
    )
    if error:
        await update.message.reply_text(error)
        return
    filename = _capture_and_save(
        update.message.text,
        user_id=str(update.effective_user.id),
        deepseek=context.bot_data["deepseek"],
        git_sync=context.bot_data["git_sync"],
        vault_path=context.bot_data["vault_path"],
        notes_subdir=context.bot_data.get("notes_subdir", ""),
    )
    await update.message.reply_text(f"Заметка сохранена: {filename}")
```

- [ ] **Step 4: Запустить тесты capture — убедиться что зелёные**

```
cd services/bot && python -m pytest tests/test_capture.py -v
```

Ожидаемо: 12 PASSED

- [ ] **Step 5: Запустить весь тест-сьют — убедиться что ничего не сломалось**

```
cd services/bot && python -m pytest tests/ -v
```

Ожидаемо: все тесты PASSED (test_auth, test_clients, test_search, test_deepseek, test_url_fetcher, test_capture)

- [ ] **Step 6: Коммит**

```
cd services/bot && git add src/handlers/capture.py tests/test_capture.py
git commit -m "feat(bot): refactor capture pipeline — raw body, LLM metadata-only, python URL fetch"
```

- [ ] **Step 7: Пуш**

```
git push origin main
```
