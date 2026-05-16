import os
from fastapi import FastAPI, HTTPException
from git_ops import sync_vault

app = FastAPI()

_REPO_PATH = os.getenv("GIT_REPO_PATH", "/vault")
_USER_NAME = os.getenv("GIT_USER_NAME", "vault-whisperer")
_USER_EMAIL = os.getenv("GIT_USER_EMAIL", "bot@vault-whisperer")


@app.post("/sync")
def sync():
    try:
        sync_vault(_REPO_PATH, _USER_NAME, _USER_EMAIL)
        return {"status": "ok"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
