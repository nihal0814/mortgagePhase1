from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


ValidationStatus = Literal["Valid", "Needs Review", "Missing Information", "Policy Review Required"]


class ValidationIssueResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    validation_id: str
    issue_type: str
    field_name: str
    application_value: str | None
    document_value: str | None
    difference: float | None
    difference_percentage: float | None
    severity: str
    description: str
    source_document_id: str | None
    created_at: datetime


class FinancialValidationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    application_id: str
    monthly_income: float | None
    monthly_debt: float | None
    loan_amount: float | None
    property_value: float | None
    dti: float | None
    ltv: float | None
    credit_score: int | None
    validation_status: ValidationStatus
    income_consistency: str
    document_consistency: str
    missing_information: list[str]
    calculated_at: datetime
    error_message: str | None
    issues: list[ValidationIssueResponse] = Field(default_factory=list)
