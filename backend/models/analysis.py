from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class DocumentAnalysis(Base):
    __tablename__ = "document_analyses"
    __table_args__ = (UniqueConstraint("document_id", name="uq_document_analysis_document"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    structured_fields: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    missing_information: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    review_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
    input_truncated: Mapped[bool] = mapped_column(default=False, nullable=False)
    input_characters: Mapped[int] = mapped_column(Integer, default=0, nullable=False)


class ApplicationAnalysis(Base):
    __tablename__ = "application_analyses"
    __table_args__ = (UniqueConstraint("application_id", name="uq_application_analysis_application"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    application_id: Mapped[str] = mapped_column(
        String(30), ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True
    )
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="Pending")
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    borrower_details: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    income_information: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    document_coverage: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    missing_information: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    conflicting_values: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    review_flags: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    source_document_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    analyzed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    error_category: Mapped[str | None] = mapped_column(String(50), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(500), nullable=True)
