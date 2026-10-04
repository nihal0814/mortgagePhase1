import hashlib
import io
from pathlib import Path

import fitz
from fastapi import HTTPException, UploadFile

from config import MAX_POLICY_UPLOAD_SIZE, POLICY_UPLOADS_DIR
from services.document_storage import safe_original_name


async def read_policy_upload(upload: UploadFile) -> tuple[bytes, str, str]:
    name = safe_original_name(upload.filename)
    extension = Path(name).suffix.lower()
    if extension not in {".pdf", ".txt"}:
        raise HTTPException(status_code=415, detail="Policy files must be PDF or TXT.")
    content = await upload.read(MAX_POLICY_UPLOAD_SIZE + 1)
    if len(content) > MAX_POLICY_UPLOAD_SIZE:
        raise HTTPException(status_code=413, detail="Policy file exceeds the configured size limit.")
    if not content:
        raise HTTPException(status_code=400, detail="The policy file is empty.")
    if extension == ".pdf" and not content.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="The policy file is not a valid PDF.")
    return content, name, extension


def policy_upload_path(filename: str) -> Path:
    path = (POLICY_UPLOADS_DIR / filename).resolve()
    if POLICY_UPLOADS_DIR not in path.parents:
        raise HTTPException(status_code=500, detail="Invalid policy storage path.")
    POLICY_UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
    return path


def extract_policy_pages(content: bytes, extension: str) -> list[tuple[int | None, str]]:
    if extension == ".txt":
        return [(None, content.decode("utf-8", errors="replace"))]
    try:
        document = fitz.open(stream=io.BytesIO(content), filetype="pdf")
        pages = [(index + 1, page.get_text("text")) for index, page in enumerate(document)]
        document.close()
        return pages
    except (fitz.FileDataError, RuntimeError) as exc:
        raise HTTPException(status_code=422, detail="The policy PDF could not be read.") from exc


def policy_hash(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()
