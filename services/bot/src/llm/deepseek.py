import os
from openai import OpenAI

_STRUCTURE_PROMPT = """\
Convert the user's message into a structured Obsidian Markdown note with YAML frontmatter.
Format:
---
title: "Descriptive Title"
date: YYYY-MM-DD
tags: [tag1, tag2]
---

# Title

Well-organized content.

Respond in the same language as the user's message."""

_SYNTHESIS_PROMPT = """\
Answer the question using context from the user's personal notes.
Be concise. Reference source notes by filename when relevant.
If the context is insufficient, say so honestly.
Respond in the same language as the question."""


class DeepSeekClient:
    def __init__(self, api_key: str, base_url: str = "https://api.deepseek.com") -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def structure_note(self, text: str) -> str:
        response = self._client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _STRUCTURE_PROMPT},
                {"role": "user", "content": text},
            ],
        )
        return response.choices[0].message.content

    def synthesize_answer(self, query: str, chunks: list[dict]) -> str:
        context = "\n\n".join(f"[{c['source']}]\n{c['text']}" for c in chunks)
        response = self._client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {"role": "system", "content": _SYNTHESIS_PROMPT},
                {"role": "user", "content": f"Question: {query}\n\nContext:\n{context}"},
            ],
        )
        return response.choices[0].message.content
