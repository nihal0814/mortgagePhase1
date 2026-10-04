from datetime import datetime

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from database.connection import Base


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[str] = mapped_column(String(30), primary_key=True, index=True)
    borrower_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str | None] = mapped_column(String(120), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    monthly_income: Mapped[float] = mapped_column(Float, nullable=False)
    monthly_debt: Mapped[float] = mapped_column(Float, nullable=False)
    loan_amount: Mapped[float] = mapped_column(Float, nullable=False)
    property_value: Mapped[float] = mapped_column(Float, nullable=False)
    property_address: Mapped[str | None] = mapped_column(String(250), nullable=True)
    employment_type: Mapped[str | None] = mapped_column(String(40), nullable=True)
    status: Mapped[str] = mapped_column(String(30), nullable=False, default="Draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

