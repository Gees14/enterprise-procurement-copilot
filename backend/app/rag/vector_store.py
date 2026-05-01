from __future__ import annotations
import uuid
from functools import lru_cache

import chromadb
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_client() -> chromadb.HttpClient:
    settings = get_settings()
    return chromadb.HttpClient(host=settings.chroma_host, port=settings.chroma_port)


def get_collection():
    settings = get_settings()
    client = _get_client()
    return client.get_or_create_collection(
        name=settings.chroma_collection,
        metadata={"hnsw:space": "cosine"},
    )


def upsert_chunks(
    chunks: list[str],
    embeddings: list[list[float]],
    document_name: str,
) -> int:
    """Stores chunks and their embeddings in ChromaDB. Returns count inserted."""
    collection = get_collection()
    ids = [str(uuid.uuid4()) for _ in chunks]
    metadatas = [{"document_name": document_name, "chunk_index": i} for i in range(len(chunks))]

    collection.upsert(
        ids=ids,
        embeddings=embeddings,
        documents=chunks,
        metadatas=metadatas,
    )
    logger.info("Upserted %d chunks for '%s'", len(chunks), document_name)
    return len(chunks)


def query_similar(
    query_embedding: list[float],
    top_k: int = 5,
) -> list[dict]:
    """Returns top-k similar chunks with metadata and distance scores."""
    collection = get_collection()
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({
            "chunk_id": str(uuid.uuid4()),  # used for citation traceability
            "document_name": meta.get("document_name", "unknown"),
            "excerpt": doc,
            "score": round(1.0 - dist, 4),  # convert cosine distance → similarity
        })
    return hits
