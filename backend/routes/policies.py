from datetime import date
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from config import POLICY_TOP_K
from database.connection import get_db
from models.application import Application
from models.financial_validation import FinancialValidation
from models.policy import Policy, PolicyChunk
from models.auth import User
from schemas.policy import PolicyAnalysisResponse, PolicyChunkResponse, PolicyResponse, PolicySearchRequest, PolicySearchResponse
from services.chunking import chunk_policy_pages
from services.nemotron import NemotronError
from services.policy_storage import extract_policy_pages, policy_hash, policy_upload_path, read_policy_upload
from services.rag import analyze_policy
from services.retrieval import retrieve_policy
from services.vector_store import add_chunks, delete_policy
from services.auth import get_current_user, require_roles
from services.application_access import application_for_user


router = APIRouter(tags=["policies"])


def _chunk_response(item: dict, db: Session) -> PolicyChunkResponse:
    policy = db.get(Policy, item["policy_id"])
    return PolicyChunkResponse(
        id=item.get("id", item["chunk_id"]),
        policy_id=item["policy_id"],
        chunk_id=item["chunk_id"],
        page_number=item.get("page_number"),
        section=item.get("section"),
        text=item["text"],
        similarity=item.get("similarity"),
    )


@router.post("/policies", response_model=PolicyResponse, status_code=201)
async def upload_policy(
    file: UploadFile = File(...),
    title: str = Form(...),
    category: str = Form("General"),
    version: str = Form(...),
    effective_date: str | None = Form(None),
    _: User = Depends(require_roles("ADMIN")),
    db: Session = Depends(get_db),
) -> Policy:
    content, original_name, extension = await read_policy_upload(file)
    digest = policy_hash(content)
    existing = db.scalar(select(Policy).where(Policy.content_hash == digest, Policy.title == title.strip(), Policy.version == version.strip()))
    if existing:
        raise HTTPException(status_code=409, detail="This policy file is already indexed.")
    try:
        parsed_date = date.fromisoformat(effective_date) if effective_date else None
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="effective_date must use YYYY-MM-DD format.") from exc
    policy_id = str(uuid4())
    storage_name = f"{policy_id}{Path(original_name).suffix.lower()}"
    policy_upload_path(storage_name).write_bytes(content)
    policy = Policy(id=policy_id, title=title.strip(), category=category.strip(), version=version.strip(), effective_date=parsed_date, original_filename=original_name, storage_filename=storage_name, content_hash=digest, status="Active")
    db.add(policy)
    db.flush()
    chunks = chunk_policy_pages(extract_policy_pages(content, extension))
    if not chunks:
        db.rollback()
        policy_upload_path(storage_name).unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="No readable policy text was found.")
    db.query(Policy).filter(Policy.title == policy.title, Policy.id != policy.id, Policy.status == "Active").update({"status": "Archived"})
    indexed = []
    for index, chunk in enumerate(chunks, start=1):
        chunk_id = f"{policy_id}_chunk_{index:04d}"
        db.add(PolicyChunk(id=str(uuid4()), policy_id=policy.id, chunk_id=chunk_id, page_number=chunk.page_number, section=chunk.section, text=chunk.text, vector_reference=chunk_id))
        indexed.append({"chunk_id": chunk_id, "policy_id": policy.id, "document_name": original_name, "page_number": chunk.page_number, "section": chunk.section, "text": chunk.text})
    add_chunks(indexed)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/policies", response_model=list[PolicyResponse])
def list_policies(_: User = Depends(get_current_user), db: Session = Depends(get_db)) -> list[Policy]:
    return list(db.scalars(select(Policy).order_by(Policy.created_at.desc())).all())


@router.delete("/policies/{policy_id}", status_code=204)
def remove_policy(policy_id: str, _: User = Depends(require_roles("ADMIN")), db: Session = Depends(get_db)) -> None:
    policy = db.get(Policy, policy_id)
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    delete_policy(policy.id)
    policy_upload_path(policy.storage_filename).unlink(missing_ok=True)
    db.delete(policy)
    db.commit()


@router.post("/policies/search", response_model=PolicySearchResponse)
def search_policies(payload: PolicySearchRequest, _: User = Depends(get_current_user), db: Session = Depends(get_db)) -> PolicySearchResponse:
    results = retrieve_policy(payload.query, db, payload.top_k or POLICY_TOP_K)
    return PolicySearchResponse(query=payload.query, results=[_chunk_response(item, db) for item in results])


@router.post("/applications/{application_id}/policy-analysis", response_model=PolicyAnalysisResponse)
def application_policy_analysis(application_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)) -> PolicyAnalysisResponse:
    application = application_for_user(application_id, user, db)
    validation = db.scalar(select(FinancialValidation).where(FinancialValidation.application_id == application_id))
    if not validation:
        raise HTTPException(status_code=409, detail="Run financial validation before policy analysis.")
    calculations = {"dti": validation.dti, "ltv": validation.ltv}
    query = f"DTI {validation.dti}% LTV {validation.ltv}% mortgage review requirements"
    retrieved = retrieve_policy(query, db, POLICY_TOP_K)
    try:
        result = analyze_policy(application_id, calculations, retrieved)
    except NemotronError as exc:
        raise HTTPException(status_code=502, detail=exc.message) from exc
    citations = [_chunk_response(item, db) for item in retrieved if item["chunk_id"] in result["citation_chunk_ids"]]
    return PolicyAnalysisResponse(**{**result, "citations": citations})
