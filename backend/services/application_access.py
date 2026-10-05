from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from models.application import Application
from models.auth import User


def can_access_application(application: Application, user: User) -> bool:
    """Return whether a user may read or work on an application."""
    if user.role == "ADMIN":
        return True
    return user.id in {application.created_by_user_id, application.assigned_to_user_id}


def application_for_user(application_id: str, user: User, db: Session) -> Application:
    application = db.get(Application, application_id)
    if not application:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Application not found")
    if not can_access_application(application, user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this application.",
        )
    return application
