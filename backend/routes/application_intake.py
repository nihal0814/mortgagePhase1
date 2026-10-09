from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from database.connection import get_db
from models.auth import User
from services.application_intake import create_intake
from services.auth import get_current_user
from services.nemotron import NemotronError


router = APIRouter(prefix="/application-intake", tags=["application intake"])


@router.post("")
async def intake_application(file: UploadFile = File(...), user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> dict:
    try:
        return await create_intake(file, user.id)
    except NemotronError as exc:
        raise HTTPException(status_code=503, detail=exc.message) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc