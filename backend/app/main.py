from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.db.database import create_tables
from app.api.routes_health import router as health_router
from app.api.routes_chat import router as chat_router
from app.api.routes_documents import router as documents_router
from app.api.routes_suppliers import router as suppliers_router
from app.api.routes_purchase_orders import router as po_router

configure_logging()
logger = get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Enterprise Procurement Copilot API (env=%s)", settings.app_env)
    logger.info("LLM provider: %s", "MockProvider" if settings.use_mock_llm else "GeminiProvider")
    create_tables()
    yield
    logger.info("Shutting down.")


app = FastAPI(
    title="Enterprise Procurement Copilot",
    description=(
        "A Generative AI assistant for procurement teams. "
        "Combines RAG over policy documents with structured supplier and PO data."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, tags=["Health"])
app.include_router(chat_router, prefix="/chat", tags=["Copilot"])
app.include_router(documents_router, prefix="/documents", tags=["Documents"])
app.include_router(suppliers_router, prefix="/suppliers", tags=["Suppliers"])
app.include_router(po_router, prefix="/purchase-orders", tags=["Purchase Orders"])
