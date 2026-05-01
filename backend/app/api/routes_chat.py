import time
from fastapi import APIRouter, HTTPException
from app.schemas.chat import ChatRequest, ChatResponse
from app.agents.procurement_agent import ProcurementAgent
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)

# Agent is stateless per-request — initialized once at module level
_agent = ProcurementAgent()


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Main copilot endpoint. Accepts a natural language question and returns
    a grounded answer with sources, tool traces, and confidence metadata.
    """
    logger.info(
        "Chat request | role=%s | question=%s",
        request.user_role,
        request.question[:80],
    )

    start = time.monotonic()
    try:
        response = await _agent.run(request)
    except Exception as exc:
        logger.exception("Agent error: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))

    response.latency_ms = int((time.monotonic() - start) * 1000)
    return response
