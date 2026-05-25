import re
import datetime
from pathlib import Path

from auth import access_error
from url_fetcher import extract_urls, fetch_titles


def _filename_from_title(title: str) -> str:
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d-%H%M%S")
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    if slug:
        return f"{timestamp}-{slug}.md"
    return f"{timestamp}.md"


def _assemble_note(title: str, tags: list[str], raw_text: str) -> str:
    date = datetime.date.today().isoformat()
    if tags:
        tags_block = "tags:\n" + "\n".join(f"  - {t}" for t in tags)
    else:
        tags_block = "tags: []"
    frontmatter = f'---\ntitle: "{title}"\ndate: {date}\n{tags_block}\n---'
    return f"{frontmatter}\n\n{raw_text}"


def _capture_and_save(
    text: str,
    user_id: str,
    deepseek,
    git_sync,
    vault_path: str,
    notes_subdir: str = "",
) -> str:
    urls = extract_urls(text)
    url_titles = fetch_titles(urls)
    metadata = deepseek.generate_metadata(text, url_titles)
    title = metadata["title"]
    tags = metadata["tags"]
    note = _assemble_note(title, tags, text)
    filename = _filename_from_title(title)
    base = Path(vault_path, notes_subdir) if notes_subdir else Path(vault_path)
    user_dir = base / user_id
    user_dir.mkdir(parents=True, exist_ok=True)
    (user_dir / filename).write_text(note, encoding="utf-8")
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
    filename = _capture_and_save(
        update.message.text,
        user_id=str(update.effective_user.id),
        deepseek=context.bot_data["deepseek"],
        git_sync=context.bot_data["git_sync"],
        vault_path=context.bot_data["vault_path"],
        notes_subdir=context.bot_data.get("notes_subdir", ""),
    )
    await update.message.reply_text(f"Заметка сохранена: {filename}")
