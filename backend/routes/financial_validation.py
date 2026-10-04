from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.analysis import DocumentAnalysis
from models.application import Application
from models.document import Document
from models.financial_validation import FinancialValidation, ValidationIssue
from routes.documents import application_or_404
from schemas.financial_validation import FinancialValidationResponse, ValidationIssueResponse
from services.financial_validation import FinancialValidationError, build_validation_result


router = APIRouter(prefix="/applications", tags=["financial-validation"])


def get_validation(application_id: str, db: Session) -> FinancialValidation:
    validation = db.scalar(select(FinancialValidation).where(FinancialValidation.application_id == application_id))
    if not validation:
        raise HTTPException(status_code=404, detail="No financial validation exists for this application")
    return validation


def save_validation(application_id: str, db: Session) -> FinancialValidation:
    application = application_or_404(application_id, db)
    rows = db.execute(
        select(Document, DocumentAnalysis)
        .join(DocumentAnalysis, DocumentAnalysis.document_id == Document.id)
        .where(Document.application_id == application_id, DocumentAnalysis.status == "Completed")
    ).all()
    analyzed_documents = [
        {"document_id": document.id, "category": document.category, "structured_fields": analysis.structured_fields}
        for document, analysis in rows
    ]
    try:
        result = build_validation_result(application, analyzed_documents)
    except FinancialValidationError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    validation = db.scalar(select(FinancialValidation).where(FinancialValidation.application_id == application_id))
    if validation is None:
        validation = FinancialValidation(id=str(uuid4()), application_id=application_id)
        db.add(validation)
    db.execute(delete(ValidationIssue).where(ValidationIssue.validation_id == validation.id))
    for field, value in result.items():
        if field != "issues":
            setattr(validation, field, value)
    for issue in result["issues"]:
        db.add(
            ValidationIssue(
                id=str(uuid4()),
                validation_id=validation.id,
                issue_type="policy" if issue.status == "Policy Review Required" else "discrepancy",
                field_name=issue.field_name,
                application_value=issue.application_value,
                document_value=issue.document_value,
                difference=issue.difference,
                difference_percentage=issue.difference_percentage,
                severity=issue.status,
                description=issue.description,
                source_document_id=issue.source_document_id,
            )
        )
    db.commit()
    db.refresh(validation)
    return validation


def response_with_issues(validation: FinancialValidation, db: Session) -> FinancialValidationResponse:
    issues = list(db.scalars(select(ValidationIssue).where(ValidationIssue.validation_id == validation.id).order_by(ValidationIssue.created_at)).all())
    return FinancialValidationResponse.model_validate({**validation.__dict__, "issues": issues})


@router.post("/{application_id}/validate", response_model=FinancialValidationResponse)
def validate_application(application_id: str, db: Session = Depends(get_db)) -> FinancialValidationResponse:
    return response_with_issues(save_validation(application_id, db), db)


@router.post("/{application_id}/validation/recalculate", response_model=FinancialValidationResponse)
def recalculate_validation(application_id: str, db: Session = Depends(get_db)) -> FinancialValidationResponse:
    return response_with_issues(save_validation(application_id, db), db)


@router.get("/{application_id}/validation", response_model=FinancialValidationResponse)
def get_application_validation(application_id: str, db: Session = Depends(get_db)) -> FinancialValidationResponse:
    application_or_404(application_id, db)
    return response_with_issues(get_validation(application_id, db), db)


@router.get("/{application_id}/validation/issues", response_model=list[ValidationIssueResponse])
def get_validation_issues(application_id: str, db: Session = Depends(get_db)) -> list[ValidationIssue]:
    application_or_404(application_id, db)
    validation = get_validation(application_id, db)
    return list(db.scalars(select(ValidationIssue).where(ValidationIssue.validation_id == validation.id).order_by(ValidationIssue.created_at)).all())
