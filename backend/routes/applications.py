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
)


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
    db: Session = Depends(get_db),
) -> list[Application]:
    query = select(Application).order_by(Application.created_at.desc())
    if search:
        query = query.where(
            (Application.borrower_name.ilike(f"%{search}%"))
            | (Application.id.ilike(f"%{search}%"))
        )
    if status_filter:
        query = query.where(Application.status == status_filter)
    return list(db.scalars(query).all())


@router.post("", response_model=ApplicationResponse, status_code=status.HTTP_201_CREATED)
def create_application(payload: ApplicationCreate, db: Session = Depends(get_db)) -> Application:
    application = Application(
        id=f"APP-{datetime.utcnow():%Y%m%d}-{uuid4().hex[:6].upper()}",
        **payload.model_dump(),
    )
    db.add(application)
    db.commit()
    db.refresh(application)
    return application


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(application_id: str, db: Session = Depends(get_db)) -> Application:
    return get_application_or_404(application_id, db)


@router.put("/{application_id}", response_model=ApplicationResponse)
def update_application(
    application_id: str,
    payload: ApplicationUpdate,
    db: Session = Depends(get_db),
) -> Application:
    application = get_application_or_404(application_id, db)
    values = payload.model_dump(exclude_unset=True)
    for field, value in values.items():
        setattr(application, field, value)
    db.commit()
    db.refresh(application)
    return application


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
def update_application_status(
    application_id: str,
    payload: StatusUpdate,
    db: Session = Depends(get_db),
) -> Application:
    application = get_application_or_404(application_id, db)
    application.status = payload.status
    db.commit()
    db.refresh(application)
    return application

