from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


DocumentCategory = Literal[
    "Salary Slip",
    "Bank Statement",
    "Income Tax Return",
    "Identity Proof",
    "Property Document",
    "Other",
]
ExtractionStatus = Literal["Uploaded", "Processing", "Extracted", "Failed"]


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    original_filename: str
    category: DocumentCategory
    content_type: str
    file_size: int
    uploaded_at: datetime
    extraction_status: ExtractionStatus
    extracted_text: str | None
    extracted_at: datetime | None
    extraction_error: str | None


class DocumentCategoryUpdate(BaseModel):
    category: DocumentCategory = Field(...)


class ExtractedTextResponse(BaseModel):
    document_id: str
    extraction_status: ExtractionStatus
    extracted_text: str | None
    extracted_at: datetime | None
    extraction_error: str | None
