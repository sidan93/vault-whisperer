# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Working Rules

- **Superpowers обязательны:** перед любой задачей проверять и использовать подходящий skill через инструмент `Skill`.
- **ADR для архитектурных решений:** любое нетривиальное решение (выбор технологии, изменение архитектуры, новый паттерн) оформлять как ADR в `docs/adr/YYYY-MM-DD-<title>.md`.
- **Коммиты без соавторства LLM:** не добавлять `Co-Authored-By: Claude` и аналогичные строки в сообщения коммитов.

---

## Project Overview

vault-whisperer — Telegram-бот для захвата заметок и RAG-поиска по Obsidian vault. Работает на удалённом VPS через `docker-compose`. Vault хранится в отдельном приватном Git-репозитории (`../obsidian-vault/` рядом с этим репо).

## Architecture

Четыре Docker-сервиса с жёстким разделением прав доступа:

| Сервис | Доступен извне | Роль |
|---|---|---|
| `bot` | Да (Telegram) | Приём сообщений, DeepSeek LLM, запись `.md`, вызов git-sync и indexer |
| `git-sync` | Нет | `POST /sync` → git commit + push в GitHub |
| `indexer` | Нет | watchdog на vault, Google embeddings, ChromaDB, `POST /search` |
| `chromadb` | Нет | официальный образ, векторный индекс |

Из интернета торчит **только `bot`**. `git-sync` закрыт на входящие, но сам ходит на `github.com`.

### Пайплайн записи заметки
```
Telegram → bot → DeepSeek (структуризация в .md) → vault/ → POST git-sync/sync → GitHub
```

### Пайплайн индексации (автоматический)
```
watchdog → изменение .md → chunker → embedder (Google) → ChromaDB
```

### Пайплайн поиска (RAG)
```
Telegram → bot → POST indexer/search → (Google embeddings + ChromaDB) → DeepSeek (синтез) → ответ
```

## Tech Stack

- **Python 3.13** во всех сервисах
- **LLM:** DeepSeek API через `openai` SDK (OpenAI-совместимый)
- **Embeddings:** Google `text-embedding-004` (Gemini API) — обёрнут в абстракцию
- **Vector DB:** ChromaDB (официальный Docker-образ)
- **Telegram:** `python-telegram-bot`
- **git-sync и indexer API:** FastAPI
- **File watcher:** `watchdog`

## Key Architectural Decisions

**Embedder abstraction** (`services/indexer/src/embedder/`): `base.py` определяет интерфейс `EmbedderBase.embed(texts: list[str]) -> list[list[float]]`. Текущая реализация — `google.py`. Смена провайдера = новый файл реализации + одна строка в конфиге.

**Secrets isolation:** У каждого сервиса свой `.env` — сервис видит только нужные ему секреты. `bot` не знает про GitHub SSH-ключ. `git-sync` не знает про Telegram token.

**Vault как отдельный репо:** `../obsidian-vault/` монтируется как bind volume в `bot`, `git-sync`, `indexer`. В этом репо vault-файлов нет.

**bot не ходит в ChromaDB напрямую:** поиск идёт через `POST indexer/search` — бот не знает про embeddings и Chroma.

## Server Layout

```
~/
├── vault-whisperer/   # этот репо
└── obsidian-vault/    # отдельный приватный репо, vault Obsidian
```

## Running Services

```bash
# поднять все сервисы
docker compose up -d

# логи конкретного сервиса
docker compose logs -f bot

# перезапустить один сервис после изменений
docker compose up -d --build bot
```

Каждый сервис имеет свой `.env` (см. `.env.example` в папке сервиса). Перед запуском скопировать и заполнить.
