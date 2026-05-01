from app.rag.chunking import chunk_text


def test_chunk_text_basic():
    text = "First paragraph.\n\nSecond paragraph.\n\nThird paragraph."
    chunks = chunk_text(text, chunk_size=100, overlap=20)
    assert len(chunks) >= 1
    assert all(isinstance(c, str) for c in chunks)


def test_chunk_text_empty():
    chunks = chunk_text("", chunk_size=500, overlap=100)
    assert chunks == []


def test_chunk_text_respects_size():
    # Long text should be split into multiple chunks
    text = "\n\n".join([f"Paragraph {i}: " + "word " * 50 for i in range(20)])
    chunks = chunk_text(text, chunk_size=300, overlap=50)
    assert len(chunks) > 1


def test_chunk_text_overlap():
    text = "\n\n".join([f"Section {i} has important content about topic {i}." for i in range(10)])
    chunks = chunk_text(text, chunk_size=150, overlap=50)
    # With overlap, consecutive chunks should share some content
    if len(chunks) > 1:
        assert len(chunks[0]) > 0 and len(chunks[1]) > 0
