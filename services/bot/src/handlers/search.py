def _perform_search(query: str, indexer, deepseek) -> str:
    chunks = indexer.search(query)
    if not chunks:
        return "Ничего не найдено."
    return deepseek.synthesize_answer(query, chunks)


async def search_handler(update, context) -> None:
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Использование: /search <запрос>")
        return
    answer = _perform_search(
        query,
        context.bot_data["indexer"],
        context.bot_data["deepseek"],
    )
    await update.message.reply_text(answer)
