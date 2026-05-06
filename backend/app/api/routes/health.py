"""Health check endpoint."""
from fastapi import APIRouter

from app.config import settings
from app.core.cache import cache
from app.services.threat_intel import rag_retriever

router = APIRouter()


async def _llm_reachable() -> bool:
    if not settings.llm_enabled:
        return False
    try:
        from app.services.content_analysis.llm_providers.factory import get_provider
        return await get_provider().is_reachable()
    except Exception:
        return False


def _rag_ready() -> bool:
    """Whether the RAG collection has been initialized successfully."""
    if not settings.rag_enabled:
        return False
    rag_retriever._initialize()
    return rag_retriever._collection is not None


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "redis": await cache.ping(),
        "llm": await _llm_reachable(),
        "rag": _rag_ready(),
    }
