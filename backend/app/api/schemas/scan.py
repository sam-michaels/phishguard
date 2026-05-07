"""Request/response schemas for scan endpoints."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field, HttpUrl


class URLScanRequest(BaseModel):
    url: HttpUrl
    page_title: Optional[str] = None
    form_fields: list[str] = Field(default_factory=list)
    referrer: Optional[str] = None


class SignalResult(BaseModel):
    """Output from a single detection signal."""

    name: str
    triggered: bool
    score_contribution: int = 0
    explanation: str
    metadata: dict = Field(default_factory=dict)
    degraded: bool = False  # True when the signal errored out, not just "not triggered"


class ScanVerdict(BaseModel):
    url: str
    risk_score: int = Field(ge=0, le=100)
    verdict: Literal["safe", "caution", "danger"]
    signals: list[SignalResult]
    cached: bool = False
    scanned_at: datetime
    summary: str
