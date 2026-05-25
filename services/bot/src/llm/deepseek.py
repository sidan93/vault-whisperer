import re
import yaml
from openai import OpenAI

_METADATA_PROMPT = """\
Extract a title and tags from the user's message.
Return ONLY valid YAML frontmatter with two fields: title and tags.
Do not add any other content or explanation.

Rules:
- title: concise, descriptive, in the same language as the message
- tags: relevant keywords; if the message contains URLs, always include "ссылка"
- Do not rewrite or summarize the message body"""

_SYNTHESIS_PROMPT = """\
Answer the question using context from the user's personal notes.
Be concise. Reference source notes by filename when relevant.
If the context is insufficient, say so honestly.
Respond in the same language as the question."""


def _parse_metadata(response: str) -> dict[str, str | list]:
    text = response.strip()
    match = re.search(r"---\s*\n(.*?)(?:\n---|\Z)", text, re.DOTALL)
    if match:
        text = match.group(1).strip()
    try:
        data = yaml.safe_load(text)
        if isinstance(data, dict):
            title = str(data.get("title", "")).strip()
            tags = [str(t).strip() for t in (data.get("tags") or []) if t]
            if title:
                return {"title": title, "tags": tags}
    except Exception:
        pass
    return {"title": response.strip()[:60], "tags": []}


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com") -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def generate_metadata(
        self,
        text: str,
        url_titles: dict[str, str | None] | None = None,
    ) -> dict[str, str | list]:
        user_content = f"Message: {text}"
        if url_titles:
            lines = ["\n\nFetched page titles:"]
            for url, title in url_titles.items():
                t = f'"{title}"' if title else "(недоступно)"
                lines.append(f"- {url} → {t}")
            user_content += "\n".join(lines)

        response = self._client.chat.completions.create(
            model="deepseek-chat",
            temperature=0,
            messages=[
                {"role": "system", "content": _METADATA_PROMPT},
                {"role": "user", "content": user_content},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("DeepSeek returned no content")
        return _parse_metadata(content)

    def synthesize_answer(self, query: str, chunks: list[dict]) -> str:
        context = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)
        response = self._client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYNTHESIS_PROMPT},
                {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
            ],
        )
        content = response.choices[0].message.content
        if content is None:
            raise ValueError("DeepSeek returned no content")
        return content
