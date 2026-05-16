# Architecture Design: vault-whisperer

**Date:** 2026-05-16  
**Status:** Approved

---

## Overview

Telegram-бот для захвата заметок и RAG-поиска по Obsidian vault. Работает на удалённом VPS (1 vCPU/1GB RAM или 2 vCPU/2GB RAM). Все компоненты поднимаются через `docker-compose`.

---

## Сервисы

Четыре Docker-контейнера с чётким разделением ответственности и прав доступа.

| Сервис | Внешний доступ | Ответственность |
|---|---|---|
| `bot` | Да (Telegram polling/webhook) | Приём сообщений, вызов DeepSeek API, запись `.md` в vault, вызов git-sync и indexer |
| `git-sync` | Нет (только внутренняя сеть) | `POST /sync` → git commit + push в GitHub |
| `indexer` | Нет (только внутренняя сеть) | Watchdog на vault, OpenAI embeddings, запись/чтение ChromaDB, `POST /search` для бота |
| `chromadb` | Нет (только внутренняя сеть) | Официальный образ, хранение векторного индекса |

### Сетевая модель

```
Интернет → [bot]
               bot      → [git-sync]  → github.com
               bot      → [indexer]
               indexer  → [chromadb]
               indexer  → generativelanguage.googleapis.com
               bot      → api.deepseek.com
```

Из интернета доступен только `bot`. `git-sync` закрыт на входящие соединения, но сам инициирует исходящие соединения на `github.com`.

---

## Технологический стек

- **Runtime:** Python 3.13
- **Telegram:** `python-telegram-bot`
- **LLM (структуризация + синтез ответов):** DeepSeek API (OpenAI-совместимый, `openai` SDK)
- **Embeddings:** Google `text-embedding-004` (Gemini API)
- **Vector DB:** ChromaDB (официальный Docker-образ)
- **File watcher:** `watchdog`
- **git-sync API:** FastAPI
- **Индексация:** по событию (изменение/добавление `.md` файла)

---

## Пайплайны

### Запись заметки

```
Пользователь (Telegram) → bot
    → DeepSeek API (структуризация в Markdown + frontmatter)
    → запись .md в ../obsidian-vault/
    → POST git-sync/sync
        → git commit + git push → GitHub
```

### Индексация (автоматическая)

```
watchdog (indexer) → обнаружил изменение .md
    → chunker (разбивка на смысловые чанки)
    → OpenAI embeddings API
    → ChromaDB (сохранение векторов с метаданными)
```

### Поиск (RAG)

```
Пользователь (Telegram) → bot
    → POST indexer/search (текст запроса)
        → OpenAI embeddings (векторизация запроса)
        → ChromaDB (retrieval: top-K релевантных чанков)
        ← возврат чанков с метаданными
    → DeepSeek API (синтез ответа с контекстом и ссылками на источники)
    → ответ пользователю
```

---

## Структура репозитория

```
vault-whisperer/
├── docker-compose.yml
├── .gitignore
│
├── services/
│   ├── bot/
│   │   ├── .env.example        # TELEGRAM_TOKEN, DEEPSEEK_API_KEY, GIT_SYNC_HOST, INDEXER_HOST
│   │   ├── Dockerfile
│   │   └── src/
│   │       ├── main.py
│   │       ├── handlers/
│   │       │   ├── capture.py      # приём сообщения → LLM → .md
│   │       │   └── search.py       # RAG-поиск
│   │       ├── llm/
│   │       │   └── deepseek.py     # DeepSeek client
│   │       └── clients/
│   │           ├── git_sync.py     # HTTP client → git-sync
│   │           └── indexer.py      # HTTP client → indexer (POST /search)
│   │
│   ├── git-sync/
│   │   ├── .env.example        # GIT_REPO_PATH, GIT_USER, GIT_EMAIL
│   │   ├── Dockerfile
│   │   └── src/
│   │       ├── main.py             # FastAPI, POST /sync
│   │       └── git_ops.py          # commit + push логика
│   │
│   ├── indexer/
│   │   ├── .env.example        # GOOGLE_API_KEY, VAULT_PATH, CHROMA_HOST
│   │   ├── Dockerfile
│   │   └── src/
│   │       ├── main.py             # FastAPI: POST /search
│   │       ├── watcher.py          # watchdog на vault/
│   │       ├── chunker.py          # разбивка .md на чанки
│   │       ├── embedder/
│   │       │   ├── base.py         # абстрактный интерфейс EmbedderBase
│   │       │   └── google.py       # реализация через Google text-embedding-004
│   │       └── chroma_writer.py    # запись/чтение ChromaDB
│   │
│   └── chromadb/
│       └── .gitkeep
│
└── docs/
    └── superpowers/
        └── specs/
            └── 2026-05-16-architecture-design.md
```

---

## Структура на сервере

```
~/
├── vault-whisperer/        # этот репо
└── obsidian-vault/         # отдельный приватный репо
                            # монтируется как volume в bot, git-sync, indexer
```

Vault монтируется через bind mount в `docker-compose.yml`:

```yaml
volumes:
  vault:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ../obsidian-vault
```

---

## Архитектурные решения

**Embedder abstraction:** `embedder/base.py` определяет интерфейс `EmbedderBase` с одним методом `embed(texts: list[str]) -> list[list[float]]`. Текущая реализация — `google.py`. Смена провайдера = новый файл + изменение одной строки в конфиге, без изменений в `watcher.py`, `chroma_writer.py` и `main.py`.

---

## Секреты и изоляция

Каждый сервис имеет собственный `.env` — видит только нужные ему секреты:

| Сервис | Секреты |
|---|---|
| `bot` | Telegram token, DeepSeek API key, адреса git-sync и indexer |
| `git-sync` | SSH-ключ GitHub, git user/email |
| `indexer` | Google API key (Gemini) |
| `chromadb` | — |
