from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


Status = Literal["Draft", "Processing", "Needs Review", "Completed"]
EmploymentType = Literal["Salaried", "Self-employed", "Other"]


class ApplicationBase(BaseModel):
    borrower_name: str = Field(min_length=1, max_length=120)
    email: str | None = Field(default=None, max_length=120)
    phone: str | None = Field(default=None, max_length=40)
    monthly_income: float = Field(gt=0)
    monthly_debt: float = Field(ge=0)
    loan_amount: float = Field(ge=0)
    property_value: float = Field(gt=0)
    property_address: str | None = Field(default=None, max_length=250)
    employment_type: EmploymentType | None = None


class ApplicationCreate(ApplicationBase):
    pass


class ApplicationUpdate(ApplicationBase):
    status: Status | None = None


class StatusUpdate(BaseModel):
    status: Status


class ApplicationResponse(ApplicationBase):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: Status
    created_at: datetime

