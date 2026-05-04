"""Health check endpoint."""
from fastapi import APIRouter

from app.core.cache import cache

router = APIRouter()


@router.get("/health")
async def health() -> dict:
    return {
        "status": "ok",
        "redis": await cache.ping(),
    }
