import shutil
from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.application import Application
from schemas.application import (
    ApplicationCreate,
    ApplicationResponse,
    ApplicationUpdate,
    StatusUpdate,
    AssignmentUpdate,
)
from models.auth import User
from services.auth import get_current_user, require_roles
from services.application_access import can_access_application, application_for_user
from services.audit import record_audit
from services.application_intake import consume_intake, discard_intake
from models.document import Document
from models.analysis import DocumentAnalysis
from services.document_storage import application_upload_dir


router = APIRouter(prefix="/applications", tags=["applications"])


def get_application_or_404(application_id: str, db: Session) -> Application:
    application = db.get(Application, application_id)
    if application is None:
        raise HTTPException(status_code=404, detail="Application not found")
    return application


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    search: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[Application]:
    query = select(Application).order_by(Application.created_at.desc())
    if user.role != "ADMIN":
        query = query.where(
            (Application.created_by_user_id == user.id)
            | (Application.assigned_to_user_id == user.id)
        )
    if search:
        query = query.where(
            (Application.borrower_name.ilike(f"%{search}%"))
            | (Application.id.ilike(f"%{search}%"))
        )
    if status_filter:
        query = query.where(Application.status == status_filter)
    return list(db.scalars(query).all())


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(
    payload: ApplicationCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    values = payload.model_dump()
    intake_id = values.pop("intake_id", None)
    application = Application(
        id=f"APP-{datetime.utcnow():%Y%m%d}-{uuid4().hex[:6].upper()}",
        created_by_user_id=user.id,
        **values,
    )
    db.add(application)
    record_audit(db, user, "APPLICATION_CREATED", "application", application.id, "Application created.", application.id)
    if intake_id:
        metadata, intake_path = consume_intake(intake_id, user.id)
        document_id = str(uuid4())
        storage_filename = f"{document_id}{metadata['suffix']}"
        directory = application_upload_dir(application.id)
        destination = directory / storage_filename
        shutil.move(str(intake_path), destination)
        db.add(Document(id=document_id, application_id=application.id, original_filename=metadata["original_filename"], storage_filename=storage_filename, category="Other", content_type=metadata["content_type"], file_size=metadata["file_size"], extraction_status="Extracted", extracted_text=metadata["extracted_text"], extracted_at=datetime.utcnow()))
        db.add(DocumentAnalysis(id=str(uuid4()), document_id=document_id, model_name="Nemotron", status="Completed", structured_fields=metadata["fields"], summary=metadata["summary"], missing_information=metadata["missing_information"], review_flags=metadata["uncertain_information"] + metadata["conflicting_information"], analyzed_at=datetime.utcnow()))
        discard_intake(intake_id, metadata["suffix"])
        record_audit(db, user, "DOCUMENT_UPLOADED", "document", document_id, "Application document attached during creation.", application.id)
    db.commit()
    db.refresh(application)
    return application


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    return application_for_user(application_id, user, db)


@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    application = application_for_user(application_id, user, db)
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(application, field, value)
    record_audit(db, user, "APPLICATION_UPDATED", "application", application.id, "Application details updated.", application.id)
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: str,
    payload: StatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Application:
    application = application_for_user(application_id, user, db)
    application.status = payload.status
    record_audit(db, user, "APPLICATION_STATUS_CHANGED", "application", application.id, "Application status changed.", application.id)
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{application_id}/assignment", response_model=ApplicationResponse)
def assign_application(
    application_id: str,
    payload: AssignmentUpdate,
    user: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> Application:
    application = get_application_or_404(application_id, db)
    if payload.assigned_to_user_id:
        assignee = db.get(User, payload.assigned_to_user_id)
        if not assignee or not assignee.is_active or assignee.role not in {"LOAN_OFFICER", "UNDERWRITER"}:
            raise HTTPException(status_code=422, detail="Assignment must target an active loan officer or underwriter.")
    application.assigned_to_user_id = payload.assigned_to_user_id
    application.assigned_at = datetime.utcnow() if payload.assigned_to_user_id else None
    record_audit(db, user, "APPLICATION_ASSIGNED", "application", application.id, "Administrator changed application assignment.", application.id)
    db.commit()
    db.refresh(application)
    return application
