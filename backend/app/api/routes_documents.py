from fastapi import APIRouter, UploadFile, File, HTTPException
from app.schemas.documents import DocumentOut, IngestResponse, ClassifyRequest, ClassifyResponse
from app.services.classification_service import ClassificationService
from app.rag.ingestion import DocumentIngestionService
from app.db.database import SessionLocal
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.get("", response_model=list[DocumentOut])
def list_documents():
    """List all ingested documents."""
    db = SessionLocal()
    try:
        from app.db.models import DocumentRecord
        records = db.query(DocumentRecord).order_by(DocumentRecord.ingested_at.desc()).all()
        return records
    finally:
        db.close()


@router.post("/upload", response_model=IngestResponse)
async def upload_document(file: UploadFile = File(...)):
    """Upload and ingest a document (markdown, txt, or pdf)."""
    allowed = {".md", ".txt", ".pdf"}
    suffix = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if suffix not in allowed:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    content = await file.read()
    service = DocumentIngestionService()
    result = await service.ingest_upload(file.filename or "upload", content, suffix)
    return result


@router.post("/ingest-sample", response_model=IngestResponse)
async def ingest_sample_documents():
    """Ingest all policy documents from the data/policy_documents folder."""
    service = DocumentIngestionService()
    result = await service.ingest_sample_documents()
    return result


@router.post("/classify", response_model=ClassifyResponse)
def classify_item(request: ClassifyRequest):
    """Classify an item description into a UNSPSC-style category."""
    db = SessionLocal()
    try:
        service = ClassificationService(db)
        return service.classify(request.description)
    finally:
        db.close()
