"""
Tests for the RAG retrieval layer.
ChromaDB and sentence_transformers are mocked — no Docker required.
"""
from unittest.mock import patch

import numpy as np

from app.rag.retrieval import retrieve
from app.schemas.chat import SourceChunk

# ── Helpers ────────────────────────────────────────────────────────────────────

_DUMMY_VEC = np.zeros(384, dtype=np.float32)


def _hit(score: float, excerpt: str = "Sample policy text.", doc: str = "policy.md") -> dict:
    return {"chunk_id": "abc-123", "document_name": doc, "excerpt": excerpt, "score": score}


# ── Tests ──────────────────────────────────────────────────────────────────────

class TestRetrieve:
    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_returns_source_chunk_objects(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = [_hit(0.85)]

        result = retrieve("what documents are required for supplier approval?")

        assert len(result) == 1
        assert isinstance(result[0], SourceChunk)
        assert result[0].score == 0.85
        assert result[0].document_name == "policy.md"

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_filters_results_below_min_score(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = [
            _hit(0.20),   # below default 0.35 threshold
            _hit(0.72),   # above threshold
            _hit(0.34),   # just below threshold
        ]

        result = retrieve("approval requirements")

        assert len(result) == 1
        assert result[0].score == 0.72

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_custom_min_score_respected(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = [_hit(0.50), _hit(0.80)]

        result = retrieve("query", min_score=0.60)

        assert len(result) == 1
        assert result[0].score == 0.80

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_passes_top_k_to_vector_store(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = []

        retrieve("some query", top_k=7)

        mock_query.assert_called_once_with(_DUMMY_VEC.tolist(), top_k=7)

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_embed_query_called_with_question(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = []

        retrieve("purchase order requirements")

        mock_embed.assert_called_once_with("purchase order requirements")

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_empty_vector_store_returns_empty_list(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = []

        result = retrieve("any question")

        assert result == []

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_excerpt_truncated_to_400_chars(self, mock_embed, mock_query):
        long_text = "x" * 600
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = [_hit(0.80, excerpt=long_text)]

        result = retrieve("query")

        assert len(result[0].excerpt) == 400

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_short_excerpt_not_padded(self, mock_embed, mock_query):
        short_text = "Short policy sentence."
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = [_hit(0.80, excerpt=short_text)]

        result = retrieve("query")

        assert result[0].excerpt == short_text

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_source_chunk_fields_are_populated(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = [_hit(0.91, doc="data_governance_policy.md")]

        result = retrieve("data retention policy")

        chunk = result[0]
        assert chunk.document_name == "data_governance_policy.md"
        assert chunk.chunk_id  # non-empty string
        assert 0 <= chunk.score <= 1.0

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_all_above_threshold_all_returned(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = [_hit(0.60), _hit(0.75), _hit(0.90)]

        result = retrieve("policy question", min_score=0.35)

        assert len(result) == 3

    @patch("app.rag.retrieval.query_similar")
    @patch("app.rag.retrieval.embed_query")
    def test_all_below_threshold_returns_empty(self, mock_embed, mock_query):
        mock_embed.return_value = _DUMMY_VEC
        mock_query.return_value = [_hit(0.10), _hit(0.20), _hit(0.30)]

        result = retrieve("policy question", min_score=0.35)

        assert result == []
