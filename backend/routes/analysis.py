from datetime import datetime
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.connection import get_db
from models.analysis import ApplicationAnalysis, DocumentAnalysis
from models.application import Application
from models.document import Document
from schemas.analysis import ApplicationAnalysisResponse, DocumentAnalysisResponse
from routes.documents import application_or_404, document_or_404
from services.nemotron import NemotronError, analyze_document, configured, summarize_application


router = APIRouter(prefix="/applications", tags=["analysis"])


def document_analysis_or_404(application_id: str, document_id: str, db: Session) -> DocumentAnalysis:
    document_or_404(application_id, document_id, db)
    analysis = db.scalar(select(DocumentAnalysis).where(DocumentAnalysis.document_id == document_id))
    if not analysis:
        raise HTTPException(status_code=404, detail="No analysis exists for this document")
    return analysis


@router.post("/{application_id}/documents/{document_id}/analyze", response_model=DocumentAnalysisResponse)
def analyze_document_route(application_id: str, document_id: str, db: Session = Depends(get_db)) -> DocumentAnalysis:
    document = document_or_404(application_id, document_id, db)
    if document.extraction_status != "Extracted" or not document.extracted_text:
        raise HTTPException(status_code=409, detail="Extract text successfully before running Nemotron analysis.")
    existing = db.scalar(select(DocumentAnalysis).where(DocumentAnalysis.document_id == document_id))
    analysis = existing or DocumentAnalysis(id=str(uuid4()), document_id=document.id, model_name="unconfigured", status="Pending")
    if not configured():
        analysis.status = "Failed"
        analysis.error_category = "not_configured"
        analysis.error_message = "AI not configured. Set NVIDIA_API_KEY, NVIDIA_BASE_URL, and NVIDIA_MODEL."
        db.add(analysis)
        db.commit()
        raise HTTPException(status_code=503, detail=analysis.error_message)
    analysis.model_name = __import__("config").NVIDIA_MODEL
    analysis.status = "Processing"
    analysis.error_category = None
    analysis.error_message = None
    db.add(analysis)
    db.commit()
    try:
        result, truncated, input_characters = analyze_document(document.category, document.extracted_text)
        analysis.status = "Completed"
        analysis.structured_fields = {key: value.model_dump() for key, value in result.fields.items()}
        analysis.summary = result.summary
        analysis.missing_information = result.missing_information
        analysis.review_flags = result.review_flags
        analysis.analyzed_at = datetime.utcnow()
        analysis.input_truncated = truncated
        analysis.input_characters = input_characters
    except NemotronError as exc:
        analysis.status = "Failed"
        analysis.error_category = exc.category
        analysis.error_message = exc.message
        db.commit()
        raise HTTPException(status_code=503 if exc.category == "not_configured" else 502, detail=exc.message)
    except Exception:
        analysis.status = "Failed"
        analysis.error_category = "validation"
        analysis.error_message = "The model response did not match the expected structured format."
        db.commit()
        raise HTTPException(status_code=502, detail=analysis.error_message)
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/{application_id}/documents/{document_id}/analysis", response_model=DocumentAnalysisResponse)
def get_document_analysis(application_id: str, document_id: str, db: Session = Depends(get_db)) -> DocumentAnalysis:
    application_or_404(application_id, db)
    return document_analysis_or_404(application_id, document_id, db)


@router.post("/{application_id}/analyze", response_model=ApplicationAnalysisResponse)
def analyze_application_route(application_id: str, db: Session = Depends(get_db)) -> ApplicationAnalysis:
    application_or_404(application_id, db)
    rows = list(db.execute(select(Document, DocumentAnalysis).join(DocumentAnalysis, DocumentAnalysis.document_id == Document.id).where(Document.application_id == application_id, DocumentAnalysis.status == "Completed")).all())
    if not rows:
        raise HTTPException(status_code=409, detail="Analyze at least one extracted document before creating an application summary.")
    if not configured():
        raise HTTPException(status_code=503, detail="AI not configured. Set NVIDIA_API_KEY, NVIDIA_BASE_URL, and NVIDIA_MODEL.")
    documents = [{"document_id": document.id, "category": document.category, "extracted_text": document.extracted_text or "", "analysis": analysis.structured_fields} for document, analysis in rows]
    existing = db.scalar(select(ApplicationAnalysis).where(ApplicationAnalysis.application_id == application_id))
    summary = existing or ApplicationAnalysis(id=str(uuid4()), application_id=application_id, model_name=__import__("config").NVIDIA_MODEL, status="Pending")
    summary.status = "Processing"
    db.add(summary)
    db.commit()
    try:
        result = summarize_application(documents)
        summary.status = "Completed"
        summary.summary = result.summary
        summary.borrower_details = {key: value.model_dump() for key, value in result.borrower_details.items()}
        summary.income_information = {key: value.model_dump() for key, value in result.income_information.items()}
        summary.document_coverage = result.document_coverage
        summary.missing_information = result.missing_information
        summary.conflicting_values = result.conflicting_values
        summary.review_flags = result.review_flags
        summary.source_document_ids = result.source_document_ids
        summary.analyzed_at = datetime.utcnow()
        summary.error_category = None
        summary.error_message = None
    except NemotronError as exc:
        summary.status = "Failed"
        summary.error_category = exc.category
        summary.error_message = exc.message
        db.commit()
        raise HTTPException(status_code=502, detail=exc.message)
    except Exception:
        summary.status = "Failed"
        summary.error_category = "validation"
        summary.error_message = "The model response did not match the expected summary format."
        db.commit()
        raise HTTPException(status_code=502, detail=summary.error_message)
    db.commit()
    db.refresh(summary)
    return summary


@router.get("/{application_id}/analysis", response_model=ApplicationAnalysisResponse)
def get_application_analysis(application_id: str, db: Session = Depends(get_db)) -> ApplicationAnalysis:
    application_or_404(application_id, db)
    summary = db.scalar(select(ApplicationAnalysis).where(ApplicationAnalysis.application_id == application_id))
    if not summary:
        raise HTTPException(status_code=404, detail="No application analysis exists")
    return summary
