from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class FinancialValidation(Base):
    __tablename__ = "financial_validations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    application_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    monthly_income: Mapped[float | None] = mapped_column(Float, nullable=True)
    monthly_debt: Mapped[float | None] = mapped_column(Float, nullable=True)
    loan_amount: Mapped[float | None] = mapped_column(Float, nullable=True)
    property_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    dti: Mapped[float | None] = mapped_column(Float, nullable=True)
    ltv: Mapped[float | None] = mapped_column(Float, nullable=True)
    credit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    validation_status: Mapped[str] = mapped_column(String(40), nullable=False)
    income_consistency: Mapped[str] = mapped_column(String(30), nullable=False)
    document_consistency: Mapped[str] = mapped_column(String(30), nullable=False)
    missing_information: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    calculated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class ValidationIssue(Base):
    __tablename__ = "validation_issues"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    validation_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("financial_validations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    issue_type: Mapped[str] = mapped_column(String(50), nullable=False)
    field_name: Mapped[str] = mapped_column(String(80), nullable=False)
    application_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    document_value: Mapped[str | None] = mapped_column(String(255), nullable=True)
    difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    difference_percentage: Mapped[float | None] = mapped_column(Float, nullable=True)
    severity: Mapped[str] = mapped_column(String(30), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
