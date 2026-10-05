from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class NoteCreate(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class IssueResolve(BaseModel):
    resolution_note: str = Field(min_length=1, max_length=2000)
    status: str = "RESOLVED"


class DocumentRequestCreate(BaseModel):
    document_type: str = Field(min_length=1, max_length=80)
    description: str = Field(min_length=1, max_length=2000)


class ReviewComplete(BaseModel):
    outcome: str = Field(pattern="^(PENDING_REVIEW|REQUIRES_INFORMATION|REVIEW_COMPLETED|APPROVED_BY_HUMAN|DECLINED_BY_HUMAN|REFER_FOR_FURTHER_REVIEW)$")
    note: str | None = Field(default=None, max_length=2000)


class ReviewIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    application_id: str
    issue_type: str
    description: str
    severity: str
    status: str
    source_document_id: str | None
    created_at: datetime
    resolved_at: datetime | None
    resolved_by_user_id: str | None
    resolution_note: str | None


class ReviewNoteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    application_id: str
    user_id: str
    note: str
    created_at: datetime


class DocumentRequestResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: str
    application_id: str
    requested_by: str
    document_type: str
    description: str
    status: str
    created_at: datetime
    fulfilled_at: datetime | None
