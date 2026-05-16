import os
import subprocess


def _git(args: list[str], env: dict, check: bool = False) -> subprocess.CompletedProcess:
    result = subprocess.run(args, env=env, capture_output=True, text=True)
    if check and result.returncode != 0:
        raise RuntimeError(f"git {args[2]} failed: {result.stderr.strip()}")
    return result


def sync_vault(repo_path: str, user_name: str, user_email: str) -> None:
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": user_name,
        "GIT_AUTHOR_EMAIL": user_email,
        "GIT_COMMITTER_NAME": user_name,
        "GIT_COMMITTER_EMAIL": user_email,
    }

    _git(["git", "-C", repo_path, "add", "-A"], env=env, check=True)

    result = _git(["git", "-C", repo_path, "diff", "--cached", "--quiet"], env=env)
    if result.returncode == 0:
        return  # нечего коммитить

    _git(["git", "-C", repo_path, "commit", "-m", "vault: auto-sync"], env=env, check=True)
    _git(["git", "-C", repo_path, "push"], env=env, check=True)
