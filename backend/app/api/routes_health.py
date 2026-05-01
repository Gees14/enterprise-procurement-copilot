from fastapi import APIRouter
from app.core.config import get_settings

router = APIRouter()
settings = get_settings()


@router.get("/health")
def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "env": settings.app_env,
        "llm_provider": "mock" if settings.use_mock_llm else "gemini",
    }
