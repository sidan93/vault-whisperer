# Infrastructure & git-sync Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Создать структуру проекта, docker-compose конфигурацию и реализовать сервис git-sync.

**Architecture:** Четыре Docker-сервиса за одной bridge-сетью. git-sync — минимальный FastAPI-сервис с одним эндпоинтом `POST /sync`, который делает `git add -A && git commit && git push` в примонтированный vault. Бот не знает про git — он просто дёргает этот эндпоинт после записи заметки.

**Tech Stack:** Python 3.13, FastAPI, uvicorn, pytest, httpx (test client)

---

## File Map

```
vault-whisperer/
├── docker-compose.yml
├── .gitignore
├── services/
│   ├── bot/
│   │   ├── Dockerfile
│   │   ├── requirements.txt          (stub)
│   │   ├── .env.example
│   │   └── src/
│   │       └── main.py               (stub)
│   ├── git-sync/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── .env.example
│   │   └── src/
│   │       ├── main.py               (FastAPI, POST /sync)
│   │       └── git_ops.py            (commit + push логика)
│   │   └── tests/
│   │       ├── conftest.py
│   │       ├── test_git_ops.py
│   │       └── test_api.py
│   ├── indexer/
│   │   ├── Dockerfile
│   │   ├── requirements.txt          (stub)
│   │   ├── .env.example
│   │   └── src/
│   │       └── main.py               (stub)
│   └── chromadb/
│       └── .gitkeep
```

---

### Task 1: Directory scaffold

**Files:**
- Create: `services/chromadb/.gitkeep`
- Create: `services/bot/src/main.py`
- Create: `services/indexer/src/main.py`

- [ ] **Step 1: Создать структуру папок**

```bash
mkdir -p services/bot/src/handlers services/bot/src/llm services/bot/src/clients
mkdir -p services/git-sync/src services/git-sync/tests
mkdir -p services/indexer/src/embedder services/indexer/tests
mkdir -p services/chromadb
touch services/chromadb/.gitkeep
```

- [ ] **Step 2: Создать stub main.py для bot и indexer**

`services/bot/src/main.py`:
```python
# placeholder — реализуется в Plan 3
```

`services/indexer/src/main.py`:
```python
# placeholder — реализуется в Plan 2
```

- [ ] **Step 3: Создать .gitignore**

`vault-whisperer/.gitignore`:
```
.env
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
.venv/
chroma_data/
```

- [ ] **Step 4: Commit**

```bash
git add .
git commit -m "chore: scaffold project directory structure"
```

---

### Task 2: docker-compose.yml

**Files:**
- Create: `docker-compose.yml`
- Create: `services/bot/.env.example`
- Create: `services/git-sync/.env.example`
- Create: `services/indexer/.env.example`

- [ ] **Step 1: Написать docker-compose.yml**

`vault-whisperer/docker-compose.yml`:
```yaml
version: "3.9"

services:
  bot:
    build: ./services/bot
    env_file: ./services/bot/.env
    volumes:
      - vault:/vault
    networks:
      - internal
    depends_on:
      - git-sync
      - indexer
    restart: unless-stopped

  git-sync:
    build: ./services/git-sync
    env_file: ./services/git-sync/.env
    volumes:
      - vault:/vault
      - ${SSH_KEY_PATH:-~/.ssh}:/root/.ssh:ro
    networks:
      - internal
    restart: unless-stopped

  indexer:
    build: ./services/indexer
    env_file: ./services/indexer/.env
    volumes:
      - vault:/vault
    networks:
      - internal
    depends_on:
      - chromadb
    restart: unless-stopped

  chromadb:
    image: chromadb/chroma:latest
    environment:
      - IS_PERSISTENT=1
    volumes:
      - chroma_data:/chroma
    networks:
      - internal
    restart: unless-stopped

networks:
  internal:
    driver: bridge

volumes:
  vault:
    driver: local
    driver_opts:
      type: none
      o: bind
      device: ../obsidian-vault   # папка должна существовать до docker compose up
  chroma_data:
```

- [ ] **Step 2: Создать .env.example для каждого сервиса**

`services/bot/.env.example`:
```
TELEGRAM_TOKEN=
DEEPSEEK_API_KEY=
GIT_SYNC_HOST=http://git-sync:8000
INDEXER_HOST=http://indexer:8000
```

`services/git-sync/.env.example`:
```
GIT_REPO_PATH=/vault
GIT_USER_NAME=vault-whisperer
GIT_USER_EMAIL=bot@vault-whisperer
```

Также создать корневой `.env.example` для compose-level переменных:

`vault-whisperer/.env.example`:
```
# Путь к SSH-ключам на хосте, монтируется в git-sync
SSH_KEY_PATH=~/.ssh
```

`services/indexer/.env.example`:
```
GOOGLE_API_KEY=
VAULT_PATH=/vault
CHROMA_HOST=http://chromadb:8000
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml services/bot/.env.example services/git-sync/.env.example services/indexer/.env.example
git commit -m "chore: add docker-compose and .env.example files"
```

---

### Task 3: Dockerfiles и requirements

**Files:**
- Create: `services/bot/Dockerfile`
- Create: `services/bot/requirements.txt`
- Create: `services/git-sync/Dockerfile`
- Create: `services/git-sync/requirements.txt`
- Create: `services/indexer/Dockerfile`
- Create: `services/indexer/requirements.txt`

- [ ] **Step 1: Dockerfiles**

`services/bot/Dockerfile`:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .
CMD ["python", "main.py"]
```

`services/git-sync/Dockerfile`:
```dockerfile
FROM python:3.13-slim
RUN apt-get update && apt-get install -y git openssh-client && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

`services/indexer/Dockerfile`:
```dockerfile
FROM python:3.13-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

- [ ] **Step 2: requirements.txt**

`services/bot/requirements.txt`:
```
python-telegram-bot==21.6
openai==1.51.0
httpx==0.27.2
```

`services/git-sync/requirements.txt`:
```
fastapi==0.115.4
uvicorn[standard]==0.32.0
pytest==8.3.3
httpx==0.27.2
```

`services/indexer/requirements.txt`:
```
fastapi==0.115.4
uvicorn[standard]==0.32.0
google-generativeai==0.8.3
chromadb==0.5.18
watchdog==5.0.3
pytest==8.3.3
httpx==0.27.2
```

- [ ] **Step 3: Commit**

```bash
git add services/bot/Dockerfile services/bot/requirements.txt \
        services/git-sync/Dockerfile services/git-sync/requirements.txt \
        services/indexer/Dockerfile services/indexer/requirements.txt
git commit -m "chore: add Dockerfiles and requirements for all services"
```

---

### Task 4: git-sync — git_ops.py (TDD)

**Files:**
- Create: `services/git-sync/tests/conftest.py`
- Create: `services/git-sync/tests/__init__.py`
- Create: `services/git-sync/tests/test_git_ops.py`
- Create: `services/git-sync/src/git_ops.py`

- [ ] **Step 1: Написать падающий тест**

`services/git-sync/tests/__init__.py`: (пустой файл)

`services/git-sync/tests/conftest.py`:
```python
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
```

`services/git-sync/tests/test_git_ops.py`:
```python
from unittest.mock import patch, MagicMock
from git_ops import sync_vault


def _run(returncode=0):
    m = MagicMock()
    m.returncode = returncode
    return m


@patch("git_ops.subprocess.run")
def test_commits_and_pushes_when_changes_exist(mock_run):
    mock_run.side_effect = [
        _run(),    # git add -A
        _run(1),   # diff --cached --quiet → 1 = есть изменения
        _run(),    # git commit
        _run(),    # git push
    ]
    sync_vault("/vault", "Bot", "bot@example.com")
    assert mock_run.call_count == 4


@patch("git_ops.subprocess.run")
def test_skips_commit_when_nothing_to_commit(mock_run):
    mock_run.side_effect = [
        _run(),    # git add -A
        _run(0),   # diff --cached --quiet → 0 = нет изменений
    ]
    sync_vault("/vault", "Bot", "bot@example.com")
    assert mock_run.call_count == 2
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd services/git-sync
pip install pytest
python -m pytest tests/test_git_ops.py -v
```
Ожидаемо: `ModuleNotFoundError: No module named 'git_ops'`

- [ ] **Step 3: Реализовать git_ops.py**

`services/git-sync/src/git_ops.py`:
```python
import os
import subprocess


def sync_vault(repo_path: str, user_name: str, user_email: str) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": user_name,
        "GIT_AUTHOR_EMAIL": user_email,
        "GIT_COMMITTER_NAME": user_name,
        "GIT_COMMITTER_EMAIL": user_email,
    }

    subprocess.run(["git", "-C", repo_path, "add", "-A"], check=True, env=env)

    result = subprocess.run(
        ["git", "-C", repo_path, "diff", "--cached", "--quiet"], env=env
    )
    if result.returncode == 0:
        return  # нечего коммитить

    subprocess.run(
        ["git", "-C", repo_path, "commit", "-m", "vault: auto-sync"],
        check=True,
        env=env,
    )
    subprocess.run(["git", "-C", repo_path, "push"], check=True, env=env)
```

- [ ] **Step 4: Запустить тесты — убедиться что проходят**

```bash
python -m pytest tests/test_git_ops.py -v
```
Ожидаемо: `2 passed`

- [ ] **Step 5: Commit**

```bash
cd ../..
git add services/git-sync/src/git_ops.py services/git-sync/tests/
git commit -m "feat(git-sync): implement sync_vault with no-op on empty diff"
```

---

### Task 5: git-sync — FastAPI endpoint (TDD)

**Files:**
- Create: `services/git-sync/src/main.py`
- Create: `services/git-sync/tests/test_api.py`

- [ ] **Step 1: Написать падающий тест**

`services/git-sync/tests/test_api.py`:
```python
from unittest.mock import patch
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)


@patch("main.sync_vault")
def test_post_sync_returns_ok(mock_sync):
    response = client.post("/sync")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    mock_sync.assert_called_once()


@patch("main.sync_vault", side_effect=Exception("git push failed"))
def test_post_sync_returns_500_on_error(mock_sync):
    response = client.post("/sync")
    assert response.status_code == 500
    assert "git push failed" in response.json()["detail"]
```

- [ ] **Step 2: Запустить тест — убедиться что падает**

```bash
cd services/git-sync
pip install fastapi httpx uvicorn
python -m pytest tests/test_api.py -v
```
Ожидаемо: `ModuleNotFoundError: No module named 'main'`

- [ ] **Step 3: Реализовать main.py**

`services/git-sync/src/main.py`:
```python
import os
from fastapi import FastAPI, HTTPException
from git_ops import sync_vault

app = FastAPI()

_REPO_PATH = os.getenv("GIT_REPO_PATH", "/vault")
_USER_NAME = os.getenv("GIT_USER_NAME", "vault-whisperer")
_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "bot@vault-whisperer")


@app.post("/sync")
async def sync():
    try:
        sync_vault(_REPO_PATH, _USER_NAME, _USER_EMAIL)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

- [ ] **Step 4: Запустить все тесты сервиса**

```bash
cd services/git-sync
python -m pytest tests/ -v
```
Ожидаемо: `4 passed`

- [ ] **Step 5: Commit**

```bash
cd ../..
git add services/git-sync/src/main.py services/git-sync/tests/test_api.py
git commit -m "feat(git-sync): add FastAPI POST /sync endpoint"
```

---

### Task 6: Проверка docker-compose build

- [ ] **Step 1: Создать ../obsidian-vault если не существует**

```bash
cd ..
git clone <your-private-vault-repo> obsidian-vault
cd vault-whisperer
```
Или для локальной проверки без реального репо:
```bash
mkdir -p ../obsidian-vault
```

- [ ] **Step 2: Собрать все сервисы**

```bash
docker compose build
```
Ожидаемо: все 4 сервиса собираются без ошибок

- [ ] **Step 3: Запустить chromadb, убедиться что стартует**

```bash
docker compose up chromadb -d
docker compose logs chromadb
```
Ожидаемо: в логах `Application startup complete`

- [ ] **Step 4: Остановить**

```bash
docker compose down
```

- [ ] **Step 5: Commit (если были правки)**

```bash
git add -A
git commit -m "chore: fix docker-compose build issues"
```

---

## Что дальше

- **Plan 2** — indexer service: EmbedderBase abstraction, Google embeddings, chunker, ChromaDB writer, watchdog, `POST /search`
- **Plan 3** — bot service: DeepSeek client, capture handler, search handler, Telegram bot setup
