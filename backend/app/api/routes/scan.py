"""URL scanning endpoint — Phase 1 core."""
from fastapi import APIRouter, HTTPException

from app.api.schemas.scan import ScanVerdict, URLScanRequest
from app.services.url_analysis.orchestrator import scan_url

router = APIRouter()


@router.post("/url", response_model=ScanVerdict)
async def scan_url_endpoint(request: URLScanRequest) -> ScanVerdict:
    """Run the full URL analysis pipeline and return a verdict."""
    try:
        return await scan_url(str(request.url))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Scan failed: {e}") from e
