# vault-whisperer

Telegram-бот для захвата заметок и RAG-поиска по [Obsidian](https://obsidian.md/) vault. Отправляешь сообщение в Telegram — бот структурирует его в `.md`-файл, сохраняет в vault и пушит в Git. Задаёшь вопрос — бот ищет по векторному индексу и отвечает с контекстом из твоих заметок.

## Architecture

```
Telegram
   │
   ▼
┌─────────────────────────────────────────────────────┐
│  bot                                                │
│  python-telegram-bot · DeepSeek LLM                │
│  записывает .md · вызывает git-sync и indexer       │
└──────────┬──────────────────────┬───────────────────┘
           │                      │
           ▼                      ▼
  ┌─────────────────┐    ┌─────────────────────────────┐
  │   git-sync      │    │  indexer                    │
  │  POST /sync     │    │  watchdog · Google Embeddings│
  │  git commit     │    │  POST /search               │
  │  git push       │    └──────────────┬──────────────┘
  └─────────────────┘                   │
                                        ▼
                               ┌─────────────────┐
                               │    chromadb     │
                               │  векторный индекс│
                               └─────────────────┘
```

Из интернета доступен **только `bot`**. Остальные сервисы изолированы во внутренней Docker-сети.

**Пайплайн записи заметки:**
```
Telegram → bot → DeepSeek (структуризация в .md) → vault/ → git-sync → GitHub
```

**Пайплайн поиска (RAG):**
```
Telegram → bot → indexer/search → (embeddings + ChromaDB) → DeepSeek (синтез) → ответ
```

## Requirements

- Docker + Docker Compose
- [Telegram Bot Token](https://core.telegram.org/bots#botfather)
- [DeepSeek API Key](https://platform.deepseek.com/)
- [Google Gemini API Key](https://aistudio.google.com/app/apikey) — для embeddings
- Отдельный Git-репозиторий для vault + SSH-ключ с доступом на запись

## Quick Start

**1. Клонировать репозиторий и создать vault-репо рядом:**
```bash
git clone https://github.com/your-username/vault-whisperer.git
cd vault-whisperer

# vault должен лежать рядом с репо
git clone git@github.com:your-username/obsidian-vault.git ../obsidian-vault
```

**2. Заполнить `.env` для каждого сервиса:**
```bash
cp services/bot/.env.example        services/bot/.env
cp services/git-sync/.env.example   services/git-sync/.env
cp services/indexer/.env.example    services/indexer/.env
```

| Файл | Ключи |
|---|---|
| `services/bot/.env` | `TELEGRAM_TOKEN`, `DEEPSEEK_API_KEY` |
| `services/indexer/.env` | `GOOGLE_API_KEY` |
| `services/git-sync/.env` | имя и email для git-коммитов |

**3. Указать путь к SSH-ключу:**
```bash
export SSH_KEY_PATH=~/.ssh  # или прописать в .env
```

**4. Добавить разрешённых пользователей:**
```bash
# Telegram user_id, по одному на строку
echo "123456789" > allowed_users.txt
```

**5. Запустить:**
```bash
docker compose up -d
```

Проверить логи:
```bash
docker compose logs -f bot
```

## Project Structure

```
vault-whisperer/
├── services/
│   ├── bot/          # Telegram-бот, DeepSeek LLM, запись заметок
│   ├── git-sync/     # FastAPI-сервис, git commit + push
│   ├── indexer/      # FastAPI-сервис, watchdog, embeddings, ChromaDB
│   └── chromadb/     # официальный образ chromadb/chroma
├── docs/
│   └── infrastructure.md
└── docker-compose.yml
```

Vault Obsidian хранится в **отдельном приватном репозитории** рядом (`../obsidian-vault/`) и монтируется как bind volume.

## Extensibility

Проект намеренно не залочен на конкретный стек.

**Embeddings** — текущая реализация использует Google `text-embedding-004`, но через абстракцию `EmbedderBase` (`services/indexer/src/embedder/`). Добавить нового провайдера = новый файл + одна строка в конфиге. Планируется поддержка OpenAI, Ollama и локальных моделей.

**LLM** — бот использует DeepSeek через OpenAI-совместимый API. Планируется вынести провайдера в конфиг, чтобы можно было переключиться на OpenAI, Anthropic или локальную модель без изменений в коде.

## Useful Links

**Telegram**
- Создать бота и получить токен → [@BotFather](https://t.me/BotFather): `/newbot`
- Узнать свой Telegram user ID → [@userinfobot](https://t.me/userinfobot): просто напиши ему любое сообщение

**API Keys**
- DeepSeek API → [platform.deepseek.com](https://platform.deepseek.com/)
- Google Gemini API (для embeddings) → [aistudio.google.com](https://aistudio.google.com/app/apikey)

## License

MIT
