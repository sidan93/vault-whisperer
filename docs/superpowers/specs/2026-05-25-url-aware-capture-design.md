# URL-aware Capture: дизайн

**Дата:** 2026-05-25  
**Статус:** на ревью

---

## Проблема

Текущий capture-pipeline передаёт весь текст пользователя в DeepSeek, который:
- Переписывает содержимое (body) по своему усмотрению → галлюцинации
- При получении ссылки может выдумать содержимое страницы (подтверждено: твит про premortem → превратился в заметку про Баффета)
- Тело заметки не соответствует тому, что написал пользователь

---

## Принципы нового дизайна

1. **Vault хранит оригинал.** Body заметки — всегда дословный текст пользователя, без переработки.
2. **LLM генерирует только метаданные.** Title и tags — единственное, что LLM создаёт.
3. **URL-fetch в Python, не в LLM.** Заголовки страниц получаем сами, передаём LLM как контекст.
4. **Один поток обработки.** URL — не особый случай, а часть общего сообщения.

---

## Архитектура

### Поток данных

```
Telegram message
    │
    ▼
[Python] extract_urls(text) → список URL
    │
    ▼
[Python] fetch_titles(urls) → {url: title | None}
    │  (HTTP GET с timeout=5s, User-Agent браузера)
    │  (пропуск: twitter.com, x.com, instagram.com, t.me и др.)
    │
    ▼
[LLM] generate_metadata(text, url_titles) → {title, tags}
    │  (только frontmatter, тело не трогает)
    │
    ▼
[Python] assemble_note(metadata, raw_text) → .md файл
    │
    ▼
[Python] save → git-sync
```

### Формат заметки на выходе

```markdown
---
title: "Заголовок от LLM"
date: 2026-05-25
tags:
  - тег1
  - тег2
---

Оригинальный текст пользователя как есть.
Ссылки остаются ссылками: https://example.com
```

---

## Компоненты

### `url_fetcher.py` (новый модуль)

Отвечает за:
- Поиск URL в тексте (regex)
- HTTP GET с `timeout=5s`, заголовок `User-Agent` браузера
- Извлечение `<title>` из HTML
- Возврат `dict[str, str | None]` — url → title или None при ошибке/таймауте

Пропускаемые домены (не делаем запрос):
- `twitter.com`, `x.com`
- `instagram.com`
- `t.me`
- Расширяемый список — константа `SKIP_DOMAINS` в модуле

### `llm/deepseek.py` — метод `generate_metadata`

Новый метод вместо `structure_note`. Вызывается с `temperature=0` для детерминированного вывода.

Промт:

```
Extract a title and tags from the user's message.
Return ONLY valid YAML frontmatter with two fields: title and tags.
Do not add any other content or explanation.

Rules:
- title: concise, descriptive, in the same language as the message
- tags: relevant keywords; if the message contains URLs, always include "ссылка"
- Do not rewrite or summarize the message body
```

Входные данные (секция "Fetched page titles" добавляется только если в тексте есть URL):
```
Message: <оригинальный текст>

Fetched page titles:
- https://example.com → "Example Domain"
- https://twitter.com/... → (недоступно)
```

Выходные данные (только frontmatter):
```yaml
title: "..."
tags:
  - ...
  - ссылка
```

### `handlers/capture.py` — рефактор

`_structure_and_save` → `_capture_and_save`:
1. `url_fetcher.extract_and_fetch(text)` → `url_titles`
2. `deepseek.generate_metadata(text, url_titles)` → frontmatter
3. Сборка `.md`: frontmatter + `\n\n` + `text`
4. Сохранение и git-sync

---

## Обработка ошибок

| Ситуация | Поведение |
|---|---|
| HTTP timeout при fetch title | `title = None`, продолжаем без него |
| LLM вернул невалидный YAML | Fallback: `title = text[:60]`, `tags = []` |
| LLM вернул лишний контент (не только frontmatter) | Вырезаем блок между `---` |
| Пропускаемый домен | Не делаем запрос, `title = None` |

---

## Что не меняется

- Пайплайн поиска (`/search`) — без изменений
- `git-sync`, `indexer`, `chromadb` — без изменений
- Аутентификация, whitelist — без изменений
- Формат `.md` файлов в vault — совместимый (frontmatter сохраняется)

---

## Зависимости

Новая зависимость в `services/bot`: `httpx` (уже возможно есть, иначе добавить в `requirements.txt`).

---

## Тесты

- `test_url_fetcher.py`: extract_urls, fetch_titles (mock HTTP), пропуск доменов, timeout
- `test_capture.py`: сборка заметки — body = оригинал, frontmatter от LLM
- `test_deepseek.py`: generate_metadata возвращает валидный YAML, fallback при ошибке
