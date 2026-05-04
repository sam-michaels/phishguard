"""Buy-scanner endpoint — scaffolded for Phase 4 activation.

Currently returns 501 Not Implemented. The signature is locked in now so
the extension can be wired against it from day one without future breaking
changes.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, HttpUrl

router = APIRouter()


class MerchantScanRequest(BaseModel):
    url: HttpUrl
    has_checkout_form: bool = False
    payment_processors_detected: list[str] = []


@router.post("/scan")
async def scan_merchant(request: MerchantScanRequest):
    raise HTTPException(
        status_code=501,
        detail="Merchant scanning activates in Phase 4. Endpoint reserved.",
    )
