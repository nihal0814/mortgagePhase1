from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class UnderwritingRun(Base):
    __tablename__ = "underwriting_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    application_id: Mapped[str] = mapped_column(String(30), ForeignKey("applications.id", ondelete="CASCADE"), index=True, nullable=False)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="RUNNING")
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="DOCUMENT_CHECK")
    report: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class UnderwritingEvent(Base):
    __tablename__ = "underwriting_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("underwriting_runs.id", ondelete="CASCADE"), index=True, nullable=False)
    application_id: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    tool_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    short_result: Mapped[str] = mapped_column(String(500), nullable=False)
    source_document_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
