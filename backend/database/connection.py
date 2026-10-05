import os
from collections.abc import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./mortgage.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def migrate_legacy_schema() -> None:
    """Add Phase 7 nullable columns without replacing an existing SQLite database."""
    if not DATABASE_URL.startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "applications" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("applications")}
    additions = {
        "created_by_user_id": "VARCHAR(36)",
        "assigned_to_user_id": "VARCHAR(36)",
        "assigned_at": "DATETIME",
        "review_status": "VARCHAR(30) DEFAULT 'PENDING_REVIEW'",
        "review_completed_by": "VARCHAR(36)",
        "review_completed_at": "DATETIME",
    }
    with engine.begin() as connection:
        for name, definition in additions.items():
            if name not in existing:
                connection.execute(text(f"ALTER TABLE applications ADD COLUMN {name} {definition}"))
