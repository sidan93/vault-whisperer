import re
from dataclasses import dataclass


@dataclass
class Chunk:
    text: str
    source: str
    tags: list[str]
    chunk_index: int


def _parse_frontmatter(content: str) -> tuple[list[str], str]:
    if not content.startswith("---"):
        return [], content
    end = content.find("---", 3)
    if end == -1:
        return [], content
    frontmatter = content[3:end]
    body = content[end + 3 :].lstrip("\n")
    match = re.search(r"tags:\s*\[([^\]]*)\]", frontmatter)
    if match:
        tags = [t.strip().strip("\"'") for t in match.group(1).split(",") if t.strip()]
    else:
        tags = []
    return tags, body


def chunk_markdown(content: str, source: str, min_length: int = 100) -> list[Chunk]:
    if not content.strip():
        return []
    tags, body = _parse_frontmatter(content)
    sections = re.split(r"\n(?=#{1,6} )", body)
    chunks = []
    for section in sections:
        section = section.strip()
        if len(section) >= min_length:
            chunks.append(
                Chunk(text=section, source=source, tags=tags, chunk_index=len(chunks))
            )
    if not chunks and body.strip():
        chunks.append(Chunk(text=body.strip(), source=source, tags=tags, chunk_index=0))
    return chunks
