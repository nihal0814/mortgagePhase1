from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.auth import User
from schemas.auth import UserCreate, UserResponse, UserUpdate
from services.audit import record_audit
from services.auth import require_roles, user_from_registration

router = APIRouter(prefix="/users", tags=["users"])
admin = require_roles("ADMIN")


@router.get("", response_model=list[UserResponse])
def list_users(_: User = Depends(admin), db: Session = Depends(get_db)) -> list[User]:
    return list(db.scalars(select(User).order_by(User.created_at.desc())).all())


@router.post("", response_model=UserResponse, status_code=201)
def create_user(payload: UserCreate, user: User = Depends(admin), db: Session = Depends(get_db)) -> User:
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    created = user_from_registration(payload.full_name, payload.email, payload.password, payload.role)
    db.add(created)
    record_audit(db, user, "USER_CREATED", "user", created.id, "Admin created a user account.")
    db.commit()
    db.refresh(created)
    return created


@router.patch("/{user_id}", response_model=UserResponse)
def update_user(user_id: str, payload: UserUpdate, user: User = Depends(admin), db: Session = Depends(get_db)) -> User:
    target = db.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    for key, value in payload.model_dump(exclude_unset=True).items():
        if key == "role":
            record_audit(db, user, "USER_ROLE_CHANGED", "user", target.id, "Admin changed user role.")
        setattr(target, key, value)
    db.commit()
    db.refresh(target)
    return target
