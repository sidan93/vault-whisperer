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
