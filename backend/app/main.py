"""FastAPI application entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import health, merchant, scan
from app.config import settings
from app.core.cache import cache


@asynccontextmanager
async def lifespan(app: FastAPI):
    await cache.connect()
    yield
    await cache.disconnect()


app = FastAPI(
    title="PhishGuard API",
    description="Real-time URL and merchant trust verification",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router, tags=["health"])
app.include_router(scan.router, prefix="/api/v1/scan", tags=["scan"])
app.include_router(merchant.router, prefix="/api/v1/merchant", tags=["merchant"])


@app.get("/", tags=["root"])
async def root() -> dict:
    """Friendly landing response — points users to interactive docs."""
    return {
        "service": "PhishGuard API",
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "health": "/health",
        "scan_endpoint": "POST /api/v1/scan/url",
        "example": {
            "url": "POST http://localhost:8000/api/v1/scan/url",
            "body": {"url": "https://paypa1.com/login"},
        },
    }