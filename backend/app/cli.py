import getpass

from database.connection import Base, SessionLocal, engine
from models.auth import User
from services.auth import user_from_registration

# Importing the model modules ensures all tables are registered for a fresh database.
from models.application import Application  # noqa: F401
from models.document import Document  # noqa: F401
from models.analysis import ApplicationAnalysis, DocumentAnalysis  # noqa: F401
from models.financial_validation import FinancialValidation, ValidationIssue  # noqa: F401
from models.policy import Policy, PolicyChunk  # noqa: F401
from models.underwriting import UnderwritingEvent, UnderwritingRun  # noqa: F401
from models.review import AuditLog, DocumentRequest, ReviewIssue, ReviewNote  # noqa: F401


def create_admin() -> None:
    email = input("Admin email: ").strip().lower()
    full_name = input("Admin full name: ").strip()
    password = getpass.getpass("Admin password (hidden): ")
    if len(password) < 8:
        raise SystemExit("Password must contain at least 8 characters.")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).filter(User.email == email).first():
            raise SystemExit("A user with that email already exists.")
        db.add(user_from_registration(full_name, email, password, "ADMIN"))
        db.commit()
        print("Admin account created.")
    finally:
        db.close()


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 2 and sys.argv[1] == "create-admin":
        create_admin()
    else:
        raise SystemExit("Usage: python -m app.cli create-admin")
