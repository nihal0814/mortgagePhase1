from fastapi import APIRouter

from config import NVIDIA_BASE_URL, NVIDIA_MODEL, NVIDIA_USE_JSON_MODE
from services.nemotron import configured


router = APIRouter(prefix="/ai", tags=["ai"])


@router.get("/status")
def ai_status() -> dict[str, str | bool]:
    return {
        "configured": configured(),
        "provider": "NVIDIA NIM hosted API",
        "base_url": NVIDIA_BASE_URL,
        "model": NVIDIA_MODEL or "not set",
        "json_mode": NVIDIA_USE_JSON_MODE,
    }


@router.post("/connectivity")
def ai_connectivity() -> dict[str, str | bool]:
    if not configured():
        return {"ok": False, "category": "not_configured", "message": "Set NVIDIA_API_KEY, NVIDIA_BASE_URL, and NVIDIA_MODEL."}
    from services.nemotron import NemotronError, _post

    try:
        result = _post([
            {"role": "system", "content": "Return only this JSON object: {\"ok\":true}"},
            {"role": "user", "content": "Connectivity check. Do not include any other text."},
        ])
        return {"ok": result.get("ok") is True, "category": "success", "message": "NVIDIA NIM returned a valid JSON response."}
    except NemotronError as exc:
        return {"ok": False, "category": exc.category, "message": exc.message}
