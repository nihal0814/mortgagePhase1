from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


AnalysisStatus = Literal["Pending", "Processing", "Completed", "Failed"]


class SourceReference(BaseModel):
    document_id: str | None = None
    page: int | None = Field(default=None, ge=1)
    snippet: str | None = Field(default=None, max_length=500)


class StructuredField(BaseModel):
    value: Any = None
    source: SourceReference | None = None
    note: str | None = Field(default=None, max_length=500)


class NemotronDocumentResult(BaseModel):
    summary: str = Field(default="", max_length=5000)
    fields: dict[str, StructuredField] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list, max_length=50)
    review_flags: list[str] = Field(default_factory=list, max_length=50)


class ApplicationIntakeResult(BaseModel):
    summary: str = Field(default="", max_length=5000)
    fields: dict[str, StructuredField] = Field(default_factory=dict)
    missing_information: list[str] = Field(default_factory=list, max_length=50)
    uncertain_information: list[str] = Field(default_factory=list, max_length=50)
    conflicting_information: list[str] = Field(default_factory=list, max_length=50)


class DocumentAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    document_id: str
    model_name: str
    status: AnalysisStatus
    structured_fields: dict[str, StructuredField]
    summary: str | None
    missing_information: list[str]
    review_flags: list[str]
    analyzed_at: datetime | None
    error_category: str | None
    error_message: str | None
    input_truncated: bool
    input_characters: int


class ApplicationSummaryResult(BaseModel):
    summary: str = Field(default="", max_length=5000)
    borrower_details: dict[str, StructuredField] = Field(default_factory=dict)
    income_information: dict[str, StructuredField] = Field(default_factory=dict)
    document_coverage: list[str] = Field(default_factory=list, max_length=50)
    missing_information: list[str] = Field(default_factory=list, max_length=50)
    conflicting_values: list[str] = Field(default_factory=list, max_length=50)
    review_flags: list[str] = Field(default_factory=list, max_length=50)
    source_document_ids: list[str] = Field(default_factory=list, max_length=50)


class ApplicationAnalysisResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    model_name: str
    status: AnalysisStatus
    summary: str | None
    borrower_details: dict[str, StructuredField]
    income_information: dict[str, StructuredField]
    document_coverage: list[str]
    missing_information: list[str]
    conflicting_values: list[str]
    review_flags: list[str]
    source_document_ids: list[str]
    analyzed_at: datetime | None
    error_category: str | None
    error_message: str | None
