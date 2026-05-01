from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models import UnspscCategory
from app.schemas.documents import ClassifyResponse
from app.core.logging import get_logger

logger = get_logger(__name__)

_EMBEDDING_THRESHOLD = 0.30   # min cosine similarity to accept an embedding match
_KEYWORD_MIN_SCORE = 0.05     # raw keyword score below which we fall back to embedding


class ClassificationService:
    def __init__(self, db: Session):
        self.db = db

    def classify(self, description: str) -> ClassifyResponse:
        """
        1. Keyword matching — fast and deterministic.
        2. Embedding similarity fallback — triggered when keyword score is 0.
        """
        result = self._classify_by_keyword(description)
        if result.confidence > 0.0:
            return result
        return self._classify_by_embedding(description)

    # ── Keyword matching ───────────────────────────────────────────────────────

    def _classify_by_keyword(self, description: str) -> ClassifyResponse:
        description_lower = description.lower()
        categories = self.db.query(UnspscCategory).all()

        best_match: UnspscCategory | None = None
        best_score = 0.0

        for cat in categories:
            keywords = (cat.keywords or "").lower().split(",")
            hits = sum(1 for kw in keywords if kw.strip() and kw.strip() in description_lower)
            score = hits / max(len(keywords), 1)
            if score > best_score:
                best_score = score
                best_match = cat

        if not best_match or best_score < _KEYWORD_MIN_SCORE:
            return ClassifyResponse(
                description=description,
                category_id="00000000",
                category_name="Unclassified",
                confidence=0.0,
                method="keyword",
            )

        return ClassifyResponse(
            description=description,
            category_id=best_match.category_id,
            category_name=best_match.category_name,
            confidence=round(min(best_score * 2, 1.0), 3),
            method="keyword",
        )

    # ── Embedding fallback ─────────────────────────────────────────────────────

    def _classify_by_embedding(self, description: str) -> ClassifyResponse:
        """
        Encodes description + all category texts with sentence-transformers and
        selects the highest cosine-similarity category.
        Lazy import keeps keyword-only paths free of the heavy model load.
        """
        try:
            from app.rag.embeddings import embed_query, embed_texts
            import numpy as np
        except ImportError:
            logger.warning("sentence_transformers unavailable — embedding classification skipped")
            return ClassifyResponse(
                description=description,
                category_id="00000000",
                category_name="Unclassified",
                confidence=0.0,
                method="keyword",
            )

        categories = self.db.query(UnspscCategory).all()
        if not categories:
            return ClassifyResponse(
                description=description,
                category_id="00000000",
                category_name="Unclassified",
                confidence=0.0,
                method="embedding",
            )

        desc_vec = embed_query(description)                              # (D,)
        cat_texts = [
            f"{cat.category_name} {cat.keywords or ''}".strip()
            for cat in categories
        ]
        cat_vecs = embed_texts(cat_texts)                                # (N, D) normalised

        scores = cat_vecs @ desc_vec                                     # (N,) cosine similarities
        best_idx = int(np.argmax(scores))
        best_score = float(scores[best_idx])

        if best_score < _EMBEDDING_THRESHOLD:
            return ClassifyResponse(
                description=description,
                category_id="00000000",
                category_name="Unclassified",
                confidence=0.0,
                method="embedding",
            )

        best_cat = categories[best_idx]
        return ClassifyResponse(
            description=description,
            category_id=best_cat.category_id,
            category_name=best_cat.category_name,
            confidence=round(min(best_score, 1.0), 3),
            method="embedding",
        )
