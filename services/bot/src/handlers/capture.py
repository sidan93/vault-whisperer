import re
import datetime
from pathlib import Path

from auth import access_error


def _filename_from_content(content: str) -> str:
    match = re.search(r"title:\s*[\"']?([^\"'\n]+)[\"']?", content)
    if match:
        title = match.group(1).strip()
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        if slug:
            return f"{slug}.md"
    return f"{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"


def _structure_and_save(text: str, user_id: str, deepseek, git_sync, vault_path: str, notes_subdir: str = "") -> str:
    structured = deepseek.structure_note(text)
    filename = _filename_from_content(structured)
    base = Path(vault_path, notes_subdir) if notes_subdir else Path(vault_path)
    user_dir = base / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / filename).write_text(structured, encoding="utf-8")
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
    filename = _structure_and_save(
        update.message.text,
        user_id=str(update.effective_user.id),
        deepseek=context.bot_data["deepseek"],
        git_sync=context.bot_data["git_sync"],
        vault_path=context.bot_data["vault_path"],
        notes_subdir=context.bot_data.get("notes_subdir", ""),
    )
    await update.message.reply_text(f"Заметка сохранена: {filename}")
