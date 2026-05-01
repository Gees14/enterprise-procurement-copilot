from __future__ import annotations
from app.rag.embeddings import embed_query
from app.rag.vector_store import query_similar
from app.schemas.chat import SourceChunk


def retrieve(query: str, top_k: int = 5, min_score: float = 0.35) -> list[SourceChunk]:
    """
    Retrieves the most relevant policy document chunks for a query.
    Filters out low-confidence results below min_score.
    """
    embedding = embed_query(query).tolist()
    hits = query_similar(embedding, top_k=top_k)

    return [
        SourceChunk(
            document_name=h["document_name"],
            chunk_id=h["chunk_id"],
            excerpt=h["excerpt"][:400],  # truncate for API response
            score=h["score"],
        )
        for h in hits
        if h["score"] >= min_score
    ]
