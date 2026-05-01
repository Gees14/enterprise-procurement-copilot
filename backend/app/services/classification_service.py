from __future__ import annotations
from sqlalchemy.orm import Session
from app.db.models import UnspscCategory
from app.schemas.documents import ClassifyResponse
from app.core.logging import get_logger

logger = get_logger(__name__)


class ClassificationService:
    def __init__(self, db: Session):
        self.db = db

    def classify(self, description: str) -> ClassifyResponse:
        """
        Classify an item description against UNSPSC categories.
        Phase 1: keyword matching. Phase 3+ will add embedding-based similarity.
        """
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

        if not best_match or best_score < 0.05:
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
