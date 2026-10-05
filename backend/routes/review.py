from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.application import Application
from models.auth import User
from models.review import AuditLog, DocumentRequest, ReviewIssue, ReviewNote
from schemas.review import (
    DocumentRequestCreate, DocumentRequestResponse, IssueResolve, NoteCreate,
    ReviewComplete, ReviewIssueResponse, ReviewNoteResponse,
)
from services.audit import record_audit
from services.auth import get_current_user, require_roles

router = APIRouter(prefix="/applications", tags=["human review"])
reviewer = require_roles("ADMIN", "UNDERWRITER")


def get_application(application_id: str, db: Session, user: User) -> Application:
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found.")
    if user.role != "ADMIN" and application.assigned_to_user_id != user.id:
        raise HTTPException(status_code=403, detail="This application is not assigned to you.")
    return application


@router.get("/review-queue", response_model=None)
def review_queue(user: User = Depends(reviewer), db: Session = Depends(get_db)) -> list[Application]:
    query = select(Application).where(Application.status == "Needs Review")
    if user.role != "ADMIN":
        query = query.where(Application.assigned_to_user_id == user.id)
    return list(db.scalars(query.order_by(Application.created_at.desc())).all())


@router.get("/{application_id}/review")
def review_detail(application_id: str, user: User = Depends(reviewer), db: Session = Depends(get_db)) -> dict:
    get_application(application_id, db, user)
    return {
        "issues": list(db.scalars(select(ReviewIssue).where(ReviewIssue.application_id == application_id).order_by(ReviewIssue.created_at.desc())).all()),
        "notes": list(db.scalars(select(ReviewNote).where(ReviewNote.application_id == application_id).order_by(ReviewNote.created_at.desc())).all()),
        "document_requests": list(db.scalars(select(DocumentRequest).where(DocumentRequest.application_id == application_id).order_by(DocumentRequest.created_at.desc())).all()),
    }


@router.post("/{application_id}/review/notes", response_model=ReviewNoteResponse, status_code=201)
def add_note(application_id: str, payload: NoteCreate, user: User = Depends(reviewer), db: Session = Depends(get_db)) -> ReviewNote:
    get_application(application_id, db, user)
    note = ReviewNote(id=str(uuid4()), application_id=application_id, user_id=user.id, note=payload.note)
    db.add(note)
    record_audit(db, user, "REVIEW_NOTE_ADDED", "application", application_id, "Reviewer added a note.", application_id)
    db.commit()
    db.refresh(note)
    return note


@router.post("/{application_id}/review/issues/{issue_id}/resolve", response_model=ReviewIssueResponse)
def resolve_issue(application_id: str, issue_id: str, payload: IssueResolve, user: User = Depends(reviewer), db: Session = Depends(get_db)) -> ReviewIssue:
    get_application(application_id, db, user)
    issue = db.scalar(select(ReviewIssue).where(ReviewIssue.id == issue_id, ReviewIssue.application_id == application_id))
    if not issue:
        raise HTTPException(status_code=404, detail="Review issue not found.")
    issue.status = payload.status
    issue.resolution_note = payload.resolution_note
    issue.resolved_by_user_id = user.id
    issue.resolved_at = datetime.utcnow()
    record_audit(db, user, "REVIEW_ISSUE_RESOLVED", "review_issue", issue.id, "Reviewer resolved an issue.", application_id)
    db.commit()
    db.refresh(issue)
    return issue


@router.post("/{application_id}/review/document-requests", response_model=DocumentRequestResponse, status_code=201)
def request_document(application_id: str, payload: DocumentRequestCreate, user: User = Depends(reviewer), db: Session = Depends(get_db)) -> DocumentRequest:
    get_application(application_id, db, user)
    request = DocumentRequest(id=str(uuid4()), application_id=application_id, requested_by=user.id, document_type=payload.document_type, description=payload.description)
    db.add(request)
    record_audit(db, user, "DOCUMENT_REQUESTED", "application", application_id, "Reviewer requested a document.", application_id)
    db.commit()
    db.refresh(request)
    return request


@router.post("/{application_id}/review/complete")
def complete_review(application_id: str, payload: ReviewComplete, user: User = Depends(reviewer), db: Session = Depends(get_db)) -> dict:
    application = get_application(application_id, db, user)
    application.review_status = payload.outcome
    application.review_completed_by = user.id
    application.review_completed_at = datetime.utcnow()
    if payload.note:
        db.add(ReviewNote(id=str(uuid4()), application_id=application_id, user_id=user.id, note=payload.note))
    record_audit(db, user, "REVIEW_COMPLETED", "application", application_id, "Human review outcome recorded.", application_id)
    db.commit()
    return {"application_id": application_id, "review_status": application.review_status, "human_review_required": False}
