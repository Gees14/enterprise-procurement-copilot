from __future__ import annotations
import os
from pathlib import Path
from app.rag.chunking import chunk_text
from app.rag.embeddings import embed_texts
from app.rag.vector_store import upsert_chunks
from app.schemas.documents import IngestResponse
from app.db.database import SessionLocal
from app.db.models import DocumentRecord
from app.core.logging import get_logger

logger = get_logger(__name__)

_data_dir = Path(os.getenv("DATA_DIR", str(Path(__file__).parent.parent.parent.parent / "data")))
POLICY_DOCS_DIR = _data_dir / "policy_documents"


class DocumentIngestionService:
    async def ingest_upload(
        self, filename: str, content: bytes, suffix: str
    ) -> IngestResponse:
        text = self._decode(content, suffix)
        if not text:
            return IngestResponse(ingested=[], failed=[filename], total_chunks=0)

        chunks = chunk_text(text)
        embeddings = embed_texts(chunks).tolist()
        upsert_chunks(chunks, embeddings, filename)
        self._record_document(filename, "upload", len(chunks))

        return IngestResponse(ingested=[filename], failed=[], total_chunks=len(chunks))

    async def ingest_sample_documents(self) -> IngestResponse:
        ingested, failed, total = [], [], 0

        if not POLICY_DOCS_DIR.exists():
            logger.warning("Policy documents directory not found: %s", POLICY_DOCS_DIR)
            return IngestResponse(ingested=[], failed=[], total_chunks=0)

        for path in POLICY_DOCS_DIR.glob("*"):
            if path.suffix not in {".md", ".txt", ".pdf"}:
                continue
            try:
                text = self._decode(path.read_bytes(), path.suffix)
                chunks = chunk_text(text)
                embeddings = embed_texts(chunks).tolist()
                upsert_chunks(chunks, embeddings, path.name)
                self._record_document(path.name, "policy", len(chunks))
                ingested.append(path.name)
                total += len(chunks)
                logger.info("Ingested '%s' → %d chunks", path.name, len(chunks))
            except Exception as exc:
                logger.error("Failed to ingest '%s': %s", path.name, exc)
                failed.append(path.name)

        return IngestResponse(ingested=ingested, failed=failed, total_chunks=total)

    def _decode(self, content: bytes, suffix: str) -> str:
        if suffix in {".md", ".txt"}:
            return content.decode("utf-8", errors="replace")
        if suffix == ".pdf":
            # PDF support via pypdf — structured so other parsers can be swapped in
            try:
                import io
                from pypdf import PdfReader
                reader = PdfReader(io.BytesIO(content))
                return "\n\n".join(page.extract_text() or "" for page in reader.pages)
            except Exception as exc:
                logger.error("PDF extraction failed: %s", exc)
                return ""
        return content.decode("utf-8", errors="replace")

    def _record_document(self, name: str, doc_type: str, chunk_count: int) -> None:
        db = SessionLocal()
        try:
            existing = db.query(DocumentRecord).filter(DocumentRecord.document_name == name).first()
            if existing:
                existing.chunk_count = chunk_count
                existing.status = "ingested"
            else:
                db.add(DocumentRecord(
                    document_name=name,
                    document_type=doc_type,
                    chunk_count=chunk_count,
                    status="ingested",
                ))
            db.commit()
        finally:
            db.close()
