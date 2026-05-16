def load_whitelist(path: str) -> set[int]:
    result = set()
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                result.add(int(line))
    return result


def access_error(chat_type: str, user_id: int, allowed_users: set[int]) -> str | None:
    if chat_type != "private":
        return "Бот работает только в личных сообщениях."
    if user_id not in allowed_users:
        return "У вас нет доступа."
    return None
