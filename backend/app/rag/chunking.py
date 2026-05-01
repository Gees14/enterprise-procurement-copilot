from __future__ import annotations
import re


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """
    Splits text into overlapping chunks of approximately chunk_size characters.
    Prefers splitting on paragraph/sentence boundaries.
    """
    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text.strip())

    paragraphs = text.split("\n\n")
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current) + len(para) < chunk_size:
            current = (current + "\n\n" + para).strip()
        else:
            if current:
                chunks.append(current)
            # Start next chunk with overlap from the previous one
            overlap_text = current[-overlap:] if len(current) > overlap else current
            current = (overlap_text + "\n\n" + para).strip()

    if current:
        chunks.append(current)

    return [c for c in chunks if len(c) > 30]
