from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class UnderwritingIssue(BaseModel):
    type: str
    severity: str
    description: str
    source_document_id: str | None = None


class UnderwritingPolicyFinding(BaseModel):
    title: str
    status: str
    source: str
    version: str | None = None
    page: int | None = None
    section: str | None = None
    text: str


class UnderwritingReport(BaseModel):
    application_id: str
    status: Literal["Valid", "Needs Review", "Needs Attention"]
    summary: str
    financial_metrics: dict[str, float | None]
    issues: list[UnderwritingIssue] = Field(default_factory=list)
    policy_findings: list[UnderwritingPolicyFinding] = Field(default_factory=list)
    missing_information: list[str] = Field(default_factory=list)
    documents_processed: int = 0
    human_review_required: bool = True
    warning: str = "AI-assisted underwriting review — human decision required."


class UnderwritingRunResponse(BaseModel):
    run_id: str
    application_id: str
    status: str
    state: str
    started_at: datetime
    completed_at: datetime | None
    error_message: str | None


class UnderwritingEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    run_id: str
    application_id: str
    event_type: str
    tool_name: str | None
    status: str
    short_result: str
    source_document_id: str | None
    timestamp: datetime
