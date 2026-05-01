from datetime import datetime
from pydantic import BaseModel


class DocumentOut(BaseModel):
    document_name: str
    document_type: str
    chunk_count: int
    ingested_at: datetime
    status: str
    model_config = {"from_attributes": True}


class IngestResponse(BaseModel):
    ingested: list[str]
    failed: list[str]
    total_chunks: int


class ClassifyRequest(BaseModel):
    description: str


class ClassifyResponse(BaseModel):
    description: str
    category_id: str
    category_name: str
    confidence: float
    method: str  # "embedding_match" | "llm" | "keyword"
