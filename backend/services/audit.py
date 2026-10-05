from uuid import uuid4

from sqlalchemy.orm import Session

from models.auth import User
from models.review import AuditLog


def record_audit(db: Session, user: User | None, action: str, resource_type: str, resource_id: str | None, description: str, application_id: str | None = None, status: str = "SUCCESS") -> None:
    db.add(AuditLog(id=str(uuid4()), user_id=user.id if user else None, application_id=application_id, action=action, resource_type=resource_type, resource_id=resource_id, status=status, short_description=description[:500]))
