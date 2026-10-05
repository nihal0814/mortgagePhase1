from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.auth import User
from models.review import AuditLog
from services.auth import require_roles


router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("/logs", response_model=None)
def list_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    _: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> list[AuditLog]:
    return list(
        db.scalars(
            select(AuditLog).order_by(AuditLog.timestamp.desc()).limit(limit)
        ).all()
    )
