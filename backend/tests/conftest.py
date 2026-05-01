"""
Shared pytest fixtures and session-level stubs.

Heavy optional dependencies (sentence_transformers, chromadb, google.generativeai)
are not installed in local dev — they live in Docker. We inject MagicMock stubs via
sys.modules so any test file can import RAG / LLM modules without hitting ImportError.
setdefault() is a no-op when the real library is already present.
"""
import sys
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base

# ── Stub out optional heavy deps ───────────────────────────────────────────────
for _dep in ["sentence_transformers", "chromadb", "google.generativeai"]:
    sys.modules.setdefault(_dep, MagicMock())


# ── Shared DB fixture ──────────────────────────────────────────────────────────

@pytest.fixture
def db():
    """In-memory SQLite session with all tables created. No PostgreSQL needed."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
