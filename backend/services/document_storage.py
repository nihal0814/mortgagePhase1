import io
import re
from pathlib import Path

from fastapi import HTTPException, UploadFile, status
from PIL import Image, UnidentifiedImageError

from config import ALLOWED_EXTENSIONS, MAX_UPLOAD_SIZE, UPLOADS_DIR


def safe_original_name(filename: str | None) -> str:
    name = Path(filename or "document").name
    name = re.sub(r"[^A-Za-z0-9._ -]", "_", name).strip(" .")
    return (name or "document")[:255]


async def read_and_validate_upload(upload: UploadFile) -> tuple[bytes, str, str]:
    original_name = safe_original_name(upload.filename)
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=415, detail="Only PDF, PNG, JPG, and JPEG files are supported.")

    content = await upload.read(MAX_UPLOAD_SIZE + 1)
    if len(content) > MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File is too large. Maximum size is {MAX_UPLOAD_SIZE // (1024 * 1024)} MB.",
        )
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    if extension == ".pdf":
        if not content.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail="The file is not a valid PDF.")
        content_type = "application/pdf"
    else:
        try:
            with Image.open(io.BytesIO(content)) as image:
                image.verify()
                if image.width * image.height > 40_000_000:
                    raise HTTPException(status_code=413, detail="Image dimensions are too large.")
        except (UnidentifiedImageError, OSError):
            raise HTTPException(status_code=400, detail="The uploaded image could not be read.")
        content_type = "image/jpeg" if extension in {".jpg", ".jpeg"} else "image/png"

    return content, original_name, content_type


def application_upload_dir(application_id: str) -> Path:
    path = (UPLOADS_DIR / application_id).resolve()
    if UPLOADS_DIR not in path.parents:
        raise HTTPException(status_code=500, detail="Invalid upload storage path.")
    path.mkdir(parents=True, exist_ok=True)
    return path


def delete_stored_file(application_id: str, storage_filename: str) -> None:
    directory = application_upload_dir(application_id)
    path = (directory / storage_filename).resolve()
    if directory not in path.parents:
        raise HTTPException(status_code=500, detail="Invalid stored file path.")
    if path.is_file():
        path.unlink()
