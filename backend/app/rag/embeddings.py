from __future__ import annotations
from functools import lru_cache
import numpy as np
from sentence_transformers import SentenceTransformer
from app.core.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_model() -> SentenceTransformer:
    settings = get_settings()
    logger.info("Loading embedding model: %s", settings.embedding_model)
    return SentenceTransformer(settings.embedding_model)


def embed_texts(texts: list[str]) -> np.ndarray:
    """Returns a (N, D) float32 array of embeddings."""
    if not texts:
        return np.empty((0, 384), dtype=np.float32)
    model = _load_model()
    return model.encode(texts, show_progress_bar=False, normalize_embeddings=True)


def embed_query(query: str) -> np.ndarray:
    """Returns a (D,) float32 array for a single query."""
    return embed_texts([query])[0]
