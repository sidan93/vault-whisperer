from chunker import chunk_markdown, Chunk


def test_returns_chunk_dataclass():
    content = "# Header\n\nSome content here that is long enough to be a chunk."
    chunks = chunk_markdown(content, source="note.md")
    assert len(chunks) > 0
    assert isinstance(chunks[0], Chunk)


def test_extracts_tags_from_frontmatter():
    content = "---\ntags: [python, tips]\n---\n\n# Note\n\nContent that is long enough."
    chunks = chunk_markdown(content, source="note.md")
    assert chunks[0].tags == ["python", "tips"]


def test_no_frontmatter_returns_empty_tags():
    content = "# Header\n\nContent without frontmatter that is long enough to pass."
    chunks = chunk_markdown(content, source="note.md")
    assert chunks[0].tags == []


def test_source_is_set_on_all_chunks():
    content = "# H1\n\nFirst section with enough content.\n\n## H2\n\nSecond section with enough content."
    chunks = chunk_markdown(content, source="path/to/note.md")
    assert all(c.source == "path/to/note.md" for c in chunks)


def test_chunk_index_is_sequential():
    content = "# H1\n\nFirst section with enough content.\n\n## H2\n\nSecond section with enough content."
    chunks = chunk_markdown(content, source="note.md")
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_short_content_returns_single_chunk():
    content = "# Title\n\nShort."
    chunks = chunk_markdown(content, source="note.md", min_length=1)
    assert len(chunks) >= 1


def test_empty_content_returns_no_chunks():
    chunks = chunk_markdown("", source="note.md")
    assert chunks == []


def test_sections_below_min_length_are_skipped():
    content = "# H1\n\nTiny.\n\n## H2\n\n" + "Long enough content. " * 10
    chunks = chunk_markdown(content, source="note.md", min_length=50)
    assert all(len(c.text) >= 50 for c in chunks)
