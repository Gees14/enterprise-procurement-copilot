"""
Tests for ClassificationService.
- Keyword tests: pure SQLite, no model loading.
- Embedding tests: embed_query / embed_texts mocked — no sentence_transformers needed.
"""
from unittest.mock import patch

import numpy as np
import pytest

from app.db.models import UnspscCategory
from app.services.classification_service import ClassificationService


# ── Fixtures & helpers ─────────────────────────────────────────────────────────

def make_category(category_id: str, category_name: str, keywords: str | None = None):
    return UnspscCategory(
        category_id=category_id,
        category_name=category_name,
        keywords=keywords,
    )


@pytest.fixture
def seeded_db(db):
    """DB with a small set of UNSPSC categories that cover keyword and embedding tests."""
    db.add(make_category("31161504", "Hydraulic hose assemblies",
                         "hydraulic,hose,assembly,fitting,SAE,hydraulic hose,flexible pipe"))
    db.add(make_category("46181504", "Head protection equipment",
                         "helmet,hard hat,safety helmet,ANSI,head protection"))
    db.add(make_category("32101700", "Circuit boards and assemblies",
                         "pcb,circuit board,assembly,electronic module,control board"))
    db.commit()
    return db


# ── Keyword classification ─────────────────────────────────────────────────────

class TestKeywordClassification:
    def test_exact_keyword_match(self, seeded_db):
        result = ClassificationService(seeded_db).classify("hydraulic hose assembly")
        assert result.category_id == "31161504"
        assert result.method == "keyword"
        assert result.confidence > 0

    def test_partial_keyword_match_returns_best_category(self, seeded_db):
        result = ClassificationService(seeded_db).classify("safety helmet ANSI")
        assert result.category_id == "46181504"
        assert result.method == "keyword"

    def test_multi_keyword_match_wins_over_single(self, seeded_db):
        # "circuit board assembly" hits pcb+assembly+circuit board → 3 hits for 32101700
        # hydraulic categories only match "assembly" → 1 hit
        result = ClassificationService(seeded_db).classify("circuit board assembly")
        assert result.category_id == "32101700"

    @patch("app.rag.embeddings.embed_texts")
    @patch("app.rag.embeddings.embed_query")
    def test_no_keyword_match_returns_unclassified(self, mock_eq, mock_et, seeded_db):
        # keyword score == 0 → embedding fallback triggered; all embedding scores low → unclassified
        mock_eq.return_value = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_et.return_value = np.array([
            [0.10, 0.05, 0.05],
            [0.05, 0.10, 0.05],
            [0.05, 0.05, 0.10],
        ], dtype=np.float32)
        result = ClassificationService(seeded_db).classify("xyz123 completely unrelated item")
        assert result.category_id == "00000000"
        assert result.confidence == 0.0

    def test_empty_db_returns_unclassified(self, db):
        result = ClassificationService(db).classify("hydraulic hose")
        assert result.category_id == "00000000"
        assert result.confidence == 0.0

    def test_confidence_capped_at_one(self, seeded_db):
        # All keywords match → raw_score can exceed 0.5 → confidence capped at 1.0
        result = ClassificationService(seeded_db).classify(
            "hydraulic hose assembly fitting SAE hydraulic hose flexible pipe"
        )
        assert result.confidence <= 1.0

    def test_confidence_is_positive_on_match(self, seeded_db):
        result = ClassificationService(seeded_db).classify("hydraulic hose")
        assert result.confidence > 0.0

    def test_description_echoed_in_response(self, seeded_db):
        description = "safety helmet for construction site"
        result = ClassificationService(seeded_db).classify(description)
        assert result.description == description

    def test_category_name_populated(self, seeded_db):
        result = ClassificationService(seeded_db).classify("hydraulic hose")
        assert result.category_name == "Hydraulic hose assemblies"

    def test_keyword_match_case_insensitive(self, seeded_db):
        result_lower = ClassificationService(seeded_db).classify("hydraulic hose")
        result_upper = ClassificationService(seeded_db).classify("HYDRAULIC HOSE")
        assert result_lower.category_id == result_upper.category_id


# ── Embedding classification (fallback) ───────────────────────────────────────

class TestEmbeddingClassification:
    """
    The embedding path is only triggered when keyword score == 0.
    We use a description with no matching keywords and mock the embedding functions.
    """

    @patch("app.rag.embeddings.embed_texts")
    @patch("app.rag.embeddings.embed_query")
    def test_selects_highest_cosine_similarity(self, mock_eq, mock_et, seeded_db):
        # 3D mock vectors — no real model needed.
        # desc vector points strongly toward category 0 (hydraulic hoses).
        mock_eq.return_value = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_et.return_value = np.array([
            [0.95, 0.05, 0.00],   # Hydraulic hose assemblies — high sim
            [0.10, 0.95, 0.00],   # Head protection            — low sim
            [0.05, 0.05, 0.95],   # Circuit boards             — low sim
        ], dtype=np.float32)

        result = ClassificationService(seeded_db).classify("flexible fluid transfer tube")

        assert result.category_id == "31161504"
        assert result.method == "embedding"

    @patch("app.rag.embeddings.embed_texts")
    @patch("app.rag.embeddings.embed_query")
    def test_returns_embedding_method_label(self, mock_eq, mock_et, seeded_db):
        mock_eq.return_value = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        mock_et.return_value = np.array([
            [0.10, 0.90, 0.00],
            [0.05, 0.05, 0.90],
            [0.00, 0.10, 0.90],
        ], dtype=np.float32)

        result = ClassificationService(seeded_db).classify("unknown protective gear item")

        assert result.method == "embedding"

    @patch("app.rag.embeddings.embed_texts")
    @patch("app.rag.embeddings.embed_query")
    def test_low_embedding_score_returns_unclassified(self, mock_eq, mock_et, seeded_db):
        # All scores below _EMBEDDING_THRESHOLD (0.30)
        mock_eq.return_value = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_et.return_value = np.array([
            [0.20, 0.10, 0.05],
            [0.10, 0.20, 0.05],
            [0.05, 0.05, 0.20],
        ], dtype=np.float32)

        result = ClassificationService(seeded_db).classify("completely unrecognisable item xyz")

        assert result.category_id == "00000000"
        assert result.confidence == 0.0

    @patch("app.rag.embeddings.embed_texts")
    @patch("app.rag.embeddings.embed_query")
    def test_confidence_is_cosine_score(self, mock_eq, mock_et, seeded_db):
        mock_eq.return_value = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_et.return_value = np.array([
            [0.75, 0.10, 0.00],   # best match, score ≈ 0.75
            [0.10, 0.80, 0.00],
            [0.00, 0.05, 0.95],
        ], dtype=np.float32)

        result = ClassificationService(seeded_db).classify("unrecognised fluid component")

        assert result.confidence == pytest.approx(0.75, abs=0.01)

    @patch("app.rag.embeddings.embed_texts")
    @patch("app.rag.embeddings.embed_query")
    def test_embed_query_called_with_description(self, mock_eq, mock_et, seeded_db):
        mock_eq.return_value = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_et.return_value = np.array([
            [0.80, 0.10, 0.00],
            [0.10, 0.80, 0.00],
            [0.00, 0.05, 0.90],
        ], dtype=np.float32)

        description = "some unknown item description"
        ClassificationService(seeded_db).classify(description)

        mock_eq.assert_called_once_with(description)

    @patch("app.rag.embeddings.embed_texts")
    @patch("app.rag.embeddings.embed_query")
    def test_embed_texts_called_for_each_category(self, mock_eq, mock_et, seeded_db):
        mock_eq.return_value = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        mock_et.return_value = np.array([
            [0.80, 0.10, 0.00],
            [0.10, 0.80, 0.00],
            [0.00, 0.05, 0.90],
        ], dtype=np.float32)

        ClassificationService(seeded_db).classify("unknown flow control device")

        # embed_texts must have been called with exactly 3 category texts
        mock_et.assert_called_once()
        cat_texts_arg = mock_et.call_args[0][0]
        assert len(cat_texts_arg) == 3
