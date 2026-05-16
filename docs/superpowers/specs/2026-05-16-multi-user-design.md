# Multi-User Mode Design

**Date:** 2026-05-16
**Status:** Approved

## Goal

Добавить сегментацию по пользователям: whitelist разрешённых Telegram user_id, изоляция заметок и RAG-поиска по user_id, только DM-режим.

---

## 1. Auth & Access Control

### Whitelist-файл

`allowed_users.txt` в корне репо, монтируется в bot-контейнер через `docker-compose.yml`.

Формат:
```
# Семья
123456789
987654321
```

- Одна строка = один Telegram `user_id` (integer)
- Строки, начинающиеся с `#`, игнорируются
- Пустые строки игнорируются

Монтируется в контейнер по пути `/allowed_users.txt` (путь хардкодирован в боте).

Загружается при старте бота в `bot_data["allowed_users"]` — `set[int]`.

### Middleware

Функция `check_access(update, context) -> bool` проверяет каждый входящий апдейт:

1. Чат не приватный → отвечает "Бот работает только в личных сообщениях.", возвращает `False`
2. `user_id` не в `allowed_users` → отвечает "У вас нет доступа.", возвращает `False`
3. Иначе → возвращает `True`

Оба хэндлера (`capture_handler`, `search_handler`) вызывают `check_access` первым делом.

### Перезагрузка whitelist

При изменении файла — перезапуск контейнера:
```bash
echo "111222333" >> allowed_users.txt
docker compose restart bot
```

---

## 2. Vault Structure

### Подпапки по user_id

Каждый пользователь получает подпапку в vault:

```
/vault/
  123456789/
    2025-05-16-143022.md
    my-note-title.md
  987654321/
    2025-05-16-150011.md
```

`capture_handler` создаёт подпапку при необходимости (`mkdir exist_ok=True`) и пишет файл в `/vault/{user_id}/{filename}`. Логика формирования имени файла не меняется.

---

## 3. Indexer — user_id в ChromaDB

### Watcher (извлечение user_id)

`source = os.path.relpath(path, vault_path)` → например `123456789/note.md`.

`user_id = Path(source).parts[0]`

Если файл лежит в корне vault (не в подпапке, `len(parts) < 2`) — пропускается, не индексируется.

### ChromaWriter

`upsert_file` добавляет `user_id` в metadata каждого чанка:
```python
{"source": source, "tags": ..., "chunk_index": i, "user_id": user_id}
```

`search` принимает `user_id: str`, передаёт в ChromaDB-запрос:
```python
where={"user_id": user_id}
```

### Indexer API

`SearchRequest` расширяется полем `user_id: str`.

### IndexerClient (в боте)

`search(query, user_id, n_results)` — передаёт `user_id` в POST `/search`.

### search_handler

Берёт `user_id = str(update.effective_user.id)`, передаёт в `IndexerClient.search`.

---

## Изменения по сервисам

| Файл | Изменение |
|---|---|
| `services/bot/src/main.py` | Загрузка whitelist в `bot_data` |
| `services/bot/src/handlers/capture.py` | Подпапка `{user_id}/`, `check_access` |
| `services/bot/src/handlers/search.py` | Передача `user_id` в indexer, `check_access` |
| `services/bot/src/clients/indexer.py` | Добавить `user_id` в запрос |
| `services/bot/src/auth.py` | Новый файл: `load_whitelist()`, `check_access()` |
| `services/indexer/src/main.py` | `SearchRequest` + `user_id` в вызов `search` |
| `services/indexer/src/chroma_writer.py` | `user_id` в metadata и фильтр поиска |
| `services/indexer/src/watcher.py` | Извлечение `user_id` из пути, пропуск корневых файлов |
| `services/bot/.env.example` | Без изменений |
| `docker-compose.yml` | Монтировать `allowed_users.txt` в bot |
| `allowed_users.txt` | Новый файл (добавить в `.gitignore`) |

---

## Ограничения

- Группы не поддерживаются (DM only)
- Существующие заметки в корне vault не индексируются (файлы без подпапки)
- Один ChromaDB-индекс для всех пользователей с фильтрацией по `user_id`
