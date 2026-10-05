from datetime import datetime
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import ALLOWED_CATEGORIES
from database.connection import get_db
from models.application import Application
from models.document import Document
from schemas.document import (
    DocumentCategoryUpdate,
    DocumentResponse,
    ExtractedTextResponse,
)
from services.document_storage import (
    application_upload_dir,
    delete_stored_file,
    read_and_validate_upload,
)
from services.text_extraction import extract_document_text, mark_extraction_success
from models.auth import User
from services.auth import get_current_user
from services.application_access import application_for_user
from services.audit import record_audit


router = APIRouter(prefix="/applications/{application_id}/documents", tags=["documents"])


def application_or_404(application_id: str, db: Session) -> Application:
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


def document_or_404(application_id: str, document_id: str, db: Session) -> Document:
    document = db.scalar(
        select(Document).where(
            Document.id == document_id, Document.application_id == application_id
        )
    )
    if not document:
        raise HTTPException(status_code=404, detail="Document not found for this application")
    return document


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    application_id: str,
    file: UploadFile = File(...),
    category: str = Form("Other"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    application_for_user(application_id, user, db)
    if category not in ALLOWED_CATEGORIES:
        raise HTTPException(status_code=422, detail="Invalid document category.")
    content, original_name, content_type = await read_and_validate_upload(file)
    document_id = str(uuid4())
    storage_filename = f"{document_id}{Path(original_name).suffix.lower()}"
    directory = application_upload_dir(application_id)
    (directory / storage_filename).write_bytes(content)
    document = Document(
        id=document_id,
        application_id=application_id,
        original_filename=original_name,
        storage_filename=storage_filename,
        category=category,
        content_type=content_type,
        file_size=len(content),
    )
    try:
        db.add(document)
        record_audit(db, user, "DOCUMENT_UPLOADED", "document", document.id, "Document uploaded.", application_id)
        db.commit()
        db.refresh(document)
    except Exception:
        (directory / storage_filename).unlink(missing_ok=True)
        db.rollback()
        raise HTTPException(status_code=500, detail="Document metadata could not be saved.")
    return document


@router.get("", response_model=list[DocumentResponse])
def list_documents(application_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Document]:
    application_for_user(application_id, user, db)
    return list(
        db.scalars(
            select(Document)
            .where(Document.application_id == application_id)
            .order_by(Document.uploaded_at.desc())
        ).all()
    )


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(application_id: str, document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Document:
    application_for_user(application_id, user, db)
    return document_or_404(application_id, document_id, db)


@router.put("/{document_id}", response_model=DocumentResponse)
def update_document_category(
    application_id: str,
    document_id: str,
    payload: DocumentCategoryUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Document:
    application_for_user(application_id, user, db)
    document = document_or_404(application_id, document_id, db)
    document.category = payload.category
    record_audit(db, user, "DOCUMENT_CATEGORY_CHANGED", "document", document.id, "Document category changed.", application_id)
    db.commit()
    db.refresh(document)
    return document


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(application_id: str, document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> None:
    application_for_user(application_id, user, db)
    document = document_or_404(application_id, document_id, db)
    delete_stored_file(application_id, document.storage_filename)
    record_audit(db, user, "DOCUMENT_DELETED", "document", document.id, "Document deleted.", application_id)
    db.delete(document)
    db.commit()


@router.post("/{document_id}/extract", response_model=DocumentResponse)
def extract_text(application_id: str, document_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> Document:
    application_for_user(application_id, user, db)
    document = document_or_404(application_id, document_id, db)
    path = application_upload_dir(application_id) / document.storage_filename
    if not path.is_file():
        document.extraction_status = "Failed"
        document.extraction_error = "The stored document file is missing."
        db.commit()
        raise HTTPException(status_code=500, detail=document.extraction_error)
    document.extraction_status = "Processing"
    document.extraction_error = None
    db.commit()
    try:
        text = extract_document_text(document, path)
        if not text.strip():
            raise RuntimeError("No readable text was found in the document.")
        mark_extraction_success(document, text)
        record_audit(db, user, "DOCUMENT_TEXT_EXTRACTED", "document", document.id, "Document text extraction completed.", application_id)
    except RuntimeError as exc:
        document.extraction_status = "Failed"
        document.extraction_error = str(exc)
        document.extracted_at = datetime.utcnow()
        db.commit()
        raise HTTPException(status_code=422, detail=str(exc))
    db.commit()
    db.refresh(document)
    return document


@router.get("/{document_id}/text", response_model=ExtractedTextResponse)
def get_document_text(
    application_id: str,
    document_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExtractedTextResponse:
    application_for_user(application_id, user, db)
    document = document_or_404(application_id, document_id, db)
    if document.extraction_status != "Extracted":
        raise HTTPException(status_code=409, detail="Text has not been extracted successfully.")
    return ExtractedTextResponse(
        document_id=document.id,
        extraction_status=document.extraction_status,
        extracted_text=document.extracted_text,
        extracted_at=document.extracted_at,
        extraction_error=document.extraction_error,
    )


@router.get("/{document_id}/file")
def get_document_file(
    application_id: str,
    document_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> FileResponse:
    """Stream a private file only after validating both URL relationships."""
    application_or_404(application_id, db)
    document = document_or_404(application_id, document_id, db)
    path = (application_upload_dir(application_id) / document.storage_filename).resolve()
    root = application_upload_dir(application_id).resolve()
    if root not in path.parents or not path.is_file():
        raise HTTPException(status_code=404, detail="Stored document file not found.")
    return FileResponse(path, media_type=document.content_type, filename=document.original_filename)
