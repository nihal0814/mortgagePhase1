from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.underwriting import UnderwritingEvent, UnderwritingRun
from schemas.underwriting import UnderwritingEventResponse, UnderwritingReport, UnderwritingRunResponse
from services.underwriting_agent import run_underwriting

router = APIRouter(prefix="/applications/{application_id}/underwriting", tags=["underwriting"])


def run_response(run: UnderwritingRun) -> dict:
    return {
        "run_id": run.id,
        "application_id": run.application_id,
        "status": run.status,
        "state": run.state,
        "started_at": run.started_at,
        "completed_at": run.completed_at,
        "error_message": run.error_message,
    }


def get_run(application_id: str, run_id: str | None, db: Session) -> UnderwritingRun:
    query = select(UnderwritingRun).where(UnderwritingRun.application_id == application_id)
    if run_id:
        query = query.where(UnderwritingRun.id == run_id)
    run = db.scalar(query.order_by(UnderwritingRun.started_at.desc()))
    if not run:
        raise HTTPException(status_code=404, detail="No underwriting run exists for this application.")
    return run


@router.post("/run", response_model=UnderwritingRunResponse)
def start_underwriting(application_id: str, db: Session = Depends(get_db)) -> dict:
    try:
       return run_response(run_underwriting(application_id, db))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/status", response_model=UnderwritingRunResponse)
def underwriting_status(application_id: str, db: Session = Depends(get_db)) -> dict:
    return run_response(get_run(application_id, None, db))


@router.get("/events", response_model=list[UnderwritingEventResponse])
def underwriting_events(application_id: str, db: Session = Depends(get_db)) -> list[UnderwritingEvent]:
    run = get_run(application_id, None, db)
    return list(db.scalars(select(UnderwritingEvent).where(UnderwritingEvent.run_id == run.id).order_by(UnderwritingEvent.timestamp)).all())


@router.get("/report", response_model=UnderwritingReport)
def underwriting_report(application_id: str, db: Session = Depends(get_db)) -> dict:
    run = get_run(application_id, None, db)
    return run.report
