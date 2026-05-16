from auth import access_error


def _perform_search(query: str, user_id: str, indexer, deepseek) -> str:
    chunks = indexer.search(query, user_id=user_id)
    if not chunks:
        return "Ничего не найдено."
    return deepseek.synthesize_answer(query, chunks)


async def search_handler(update, context) -> None:
    error = access_error(
        update.effective_chat.type,
        update.effective_user.id,
        context.bot_data["allowed_users"],
    )
    if error:
        await update.message.reply_text(error)
        return
    query = " ".join(context.args) if context.args else ""
    if not query:
        await update.message.reply_text("Использование: /search <запрос>")
        return
    user_id = str(update.effective_user.id)
    answer = _perform_search(
        query,
        user_id=user_id,
        indexer=context.bot_data["indexer"],
        deepseek=context.bot_data["deepseek"],
    )
    await update.message.reply_text(answer)
