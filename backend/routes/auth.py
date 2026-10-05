from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.auth import User
from schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserCreate, UserResponse, UserUpdate
from services.audit import record_audit
from services.auth import create_access_token, get_current_user, hash_password, user_from_registration, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    if db.scalar(select(User).where(User.email == payload.email.lower())):
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = user_from_registration(payload.full_name, payload.email, payload.password)
    db.add(user)
    record_audit(db, user, "USER_CREATED", "user", user.id, "User account registered.")
    db.commit()
    db.refresh(user)
    return TokenResponse(access_token=create_access_token(user), user=user)


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    user = db.scalar(select(User).where(User.email == payload.email.lower()))
    if not user or not verify_password(payload.password, user.password_hash) or not user.is_active:
        raise HTTPException(status_code=401, detail="Invalid email or password.", headers={"WWW-Authenticate": "Bearer"})
    user.last_login_at = datetime.utcnow()
    record_audit(db, user, "LOGIN", "user", user.id, "User logged in.")
    db.commit()
    return TokenResponse(access_token=create_access_token(user), user=user)


@router.get("/me", response_model=UserResponse)
def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/logout")
def logout(user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict[str, str]:
    record_audit(db, user, "LOGOUT", "user", user.id, "User logged out.")
    db.commit()
    return {"message": "Logged out. Remove the token from the client."}
