"""Redis-backed verdict cache with hashed keys and verdict-aware TTLs."""
import hashlib
from typing import Optional

import redis.asyncio as redis

from app.api.schemas.scan import ScanVerdict
from app.config import settings


def _key(url: str) -> str:
    h = hashlib.sha256(url.encode()).hexdigest()
    return f"verdict:{h}"


def _ttl_for_verdict(verdict_label: str) -> int:
    return {
        "safe": settings.cache_ttl_safe,
        "caution": settings.cache_ttl_caution,
        "danger": settings.cache_ttl_danger,
    }.get(verdict_label, settings.cache_ttl_safe)


class VerdictCache:
    def __init__(self):
        self._client: Optional[redis.Redis] = None

    async def connect(self) -> None:
        self._client = redis.from_url(settings.redis_url, decode_responses=True)

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()

    async def ping(self) -> bool:
        if not self._client:
            return False
        try:
            return await self._client.ping()
        except Exception:
            return False

    async def get_verdict(self, url: str) -> Optional[ScanVerdict]:
        if not self._client:
            return None
        try:
            raw = await self._client.get(_key(url))
            if raw:
                return ScanVerdict.model_validate_json(raw)
        except Exception:
            pass
        return None

    async def set_verdict(self, url: str, verdict: ScanVerdict) -> None:
        if not self._client:
            return
        try:
            await self._client.set(
                _key(url),
                verdict.model_dump_json(),
                ex=_ttl_for_verdict(verdict.verdict),
            )
        except Exception:
            # Cache failures must never break a scan
            pass


cache = VerdictCache()
