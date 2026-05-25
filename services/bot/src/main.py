import logging
import os
import sys

from telegram.ext import Application, CommandHandler, MessageHandler, filters

from auth import load_whitelist
from clients.git_sync import GitSyncClient
from clients.indexer import IndexerClient
from handlers.capture import capture_handler
from handlers.search import search_handler
from llm.deepseek import DeepSeekClient

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)


def main() -> None:
    app = Application.builder().token(os.environ["TELEGRAM_TOKEN"]).build()

    app.bot_data["deepseek"] = DeepSeekClient(api_key=os.environ["DEEPSEEK_API_KEY"])
    app.bot_data["git_sync"] = GitSyncClient(os.getenv("GIT_SYNC_HOST", "http://git-sync:8000"))
    app.bot_data["indexer"] = IndexerClient(os.getenv("INDEXER_HOST", "http://indexer:8000"))
    app.bot_data["vault_path"] = os.getenv("VAULT_PATH", "/vault")
    app.bot_data["notes_subdir"] = os.getenv("NOTES_SUBDIR", "inbox")
    try:
        app.bot_data["allowed_users"] = load_whitelist("/allowed_users.txt")
    except FileNotFoundError:
        sys.exit("ERROR: /allowed_users.txt not found. Mount the file into the container.")

    app.add_handler(CommandHandler("search", search_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, capture_handler))

    app.run_polling()


if __name__ == "__main__":
    main()
