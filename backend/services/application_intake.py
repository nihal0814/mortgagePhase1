import json
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

from fastapi import HTTPException

from config import UPLOADS_DIR
from services.document_storage import read_and_validate_upload
from services.nemotron import analyze_application_intake
from services.text_extraction import extract_document_text


INTAKE_DIR = UPLOADS_DIR / "_application_intake"


async def create_intake(upload, user_id: str):
    content, original_name, content_type = await read_and_validate_upload(upload)
    intake_id = str(uuid4())
    INTAKE_DIR.mkdir(parents=True, exist_ok=True)
    suffix = Path(original_name).suffix.lower()
    file_path = INTAKE_DIR / f"{intake_id}{suffix}"
    metadata_path = INTAKE_DIR / f"{intake_id}.json"
    file_path.write_bytes(content)
    try:
        document = SimpleNamespace(content_type=content_type)
        extracted_text = extract_document_text(document, file_path)
        if not extracted_text.strip():
            raise RuntimeError("No readable text was found in the document.")
        analysis = analyze_application_intake(extracted_text)
        metadata_path.write_text(json.dumps({
            "user_id": user_id,
            "original_filename": original_name,
            "content_type": content_type,
            "file_size": len(content),
            "suffix": suffix,
            "fields": {key: value.model_dump() for key, value in analysis.fields.items()},
            "summary": analysis.summary,
            "missing_information": analysis.missing_information,
            "uncertain_information": analysis.uncertain_information,
            "conflicting_information": analysis.conflicting_information,
            "extracted_text": extracted_text,
        }))
    except Exception:
        file_path.unlink(missing_ok=True)
        metadata_path.unlink(missing_ok=True)
        raise
    return {"intake_id": intake_id, "original_filename": original_name, "content_type": content_type,
            "file_size": len(content), "fields": analysis.fields, "summary": analysis.summary,
            "missing_information": analysis.missing_information,
            "uncertain_information": analysis.uncertain_information,
            "conflicting_information": analysis.conflicting_information}


def consume_intake(intake_id: str, user_id: str) -> tuple[dict, Path]:
    if Path(intake_id).name != intake_id:
        raise HTTPException(status_code=422, detail="Invalid intake ID.")
    metadata_path = INTAKE_DIR / f"{intake_id}.json"
    metadata = None
    if metadata_path.is_file():
        metadata = json.loads(metadata_path.read_text())
    if not metadata:
        raise HTTPException(status_code=404, detail="The uploaded application document has expired or was not found.")
    if metadata.get("user_id") != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this uploaded application document.")
    file_path = INTAKE_DIR / f"{intake_id}{metadata['suffix']}"
    if not file_path.is_file():
        raise HTTPException(status_code=404, detail="The uploaded application document was not found.")
    return metadata, file_path


def discard_intake(intake_id: str, suffix: str) -> None:
    (INTAKE_DIR / f"{intake_id}.json").unlink(missing_ok=True)
    (INTAKE_DIR / f"{intake_id}{suffix}").unlink(missing_ok=True)