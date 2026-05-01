from pydantic import BaseModel, Field
from app.core.security import UserRole


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000, description="User question in natural language")
    user_role: UserRole = Field(default=UserRole.ANALYST, description="Role determines data access scope")
    session_id: str | None = Field(default=None, description="Optional session ID for conversation context")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of document chunks to retrieve")


class SourceChunk(BaseModel):
    document_name: str
    chunk_id: str
    excerpt: str
    score: float


class ToolCall(BaseModel):
    name: str
    input: dict
    output_summary: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk] = []
    tools_called: list[ToolCall] = []
    grounding_status: str = Field(
        description="'grounded' | 'partially_grounded' | 'not_grounded' | 'mock'"
    )
    trace: list[str] = []
    latency_ms: int = 0
    model_used: str = ""
