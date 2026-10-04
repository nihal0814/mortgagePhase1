from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


PolicyStatus = Literal["Active", "Archived", "Processing", "Failed"]


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    category: str
    version: str
    effective_date: date | None
    original_filename: str
    status: PolicyStatus
    created_at: datetime


class PolicyChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    policy_id: str
    chunk_id: str
    page_number: int | None
    section: str | None
    text: str
    similarity: float | None = None


class PolicySearchRequest(BaseModel):
    query: str = Field(min_length=3, max_length=1000)
    top_k: int = Field(default=5, ge=1, le=10)


class PolicySearchResponse(BaseModel):
    query: str
    results: list[PolicyChunkResponse]


class PolicyAnalysisResponse(BaseModel):
    application_id: str
    status: Literal["Completed", "Unavailable", "Failed"]
    explanation: str
    policy_findings: list[str]
    calculations: dict[str, float | None]
    citations: list[PolicyChunkResponse]
    warning: str
