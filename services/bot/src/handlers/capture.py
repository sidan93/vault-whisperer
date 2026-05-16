import re
import datetime
from pathlib import Path


def _filename_from_content(content: str) -> str:
    match = re.search(r"title:\s*[\"']?([^\"'\n]+)[\"']?", content)
    if match:
        title = match.group(1).strip()
        slug = re.sub(r"[^\w\s-]", "", title.lower())
        slug = re.sub(r"[\s_]+", "-", slug).strip("-")
        if slug:
            return f"{slug}.md"
    return f"{datetime.datetime.now().strftime('%Y-%m-%d-%H%M%S')}.md"


def _structure_and_save(text: str, deepseek, git_sync, vault_path: str) -> str:
    structured = deepseek.structure_note(text)
    filename = _filename_from_content(structured)
    Path(vault_path, filename).write_text(structured, encoding="utf-8")
    git_sync.sync()
    return filename


async def capture_handler(update, context) -> None:
    filename = _structure_and_save(
        update.message.text,
        context.bot_data["deepseek"],
        context.bot_data["git_sync"],
        context.bot_data["vault_path"],
    )
    await update.message.reply_text(f"Заметка сохранена: {filename}")
