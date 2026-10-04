import io

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base, get_db
from main import app
from schemas.analysis import NemotronDocumentResult
from services import underwriting_agent


@pytest.fixture()
def client(tmp_path):
    test_engine = create_engine(f"sqlite:///{tmp_path / 'underwriting.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(test_engine)
    session_factory = sessionmaker(bind=test_engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def pdf_bytes() -> bytes:
    document = fitz.open()
    page = document.new_page()
    page.insert_text((72, 72), "Gross monthly salary: 100000")
    content = document.tobytes()
    document.close()
    return content


def create_application(client: TestClient) -> str:
    response = client.post(
        "/applications",
        json={"borrower_name": "Agent Test", "monthly_income": 100000, "monthly_debt": 45000, "loan_amount": 4000000, "property_value": 5000000},
    )
    return response.json()["id"]


def test_missing_application_is_rejected(client):
    response = client.post("/applications/missing/underwriting/run")
    assert response.status_code == 404


def test_underwriting_run_records_events_and_human_review(client, monkeypatch):
    application_id = create_application(client)
    uploaded = client.post(
        f"/applications/{application_id}/documents",
        files={"file": ("salary.pdf", io.BytesIO(pdf_bytes()), "application/pdf")},
        data={"category": "Salary Slip"},
    ).json()

    monkeypatch.setattr(
        underwriting_agent,
        "analyze_document",
        lambda _category, _text: (
            NemotronDocumentResult.model_validate(
                {"summary": "Income found.", "fields": {"gross_monthly_salary": {"value": 100000}}},
            ),
            False,
            30,
        ),
    )
    monkeypatch.setattr(underwriting_agent, "retrieve_policy", lambda *_args, **_kwargs: [])

    response = client.post(f"/applications/{application_id}/underwriting/run")
    assert response.status_code == 200
    assert response.json()["status"] == "COMPLETED"

    events = client.get(f"/applications/{application_id}/underwriting/events")
    assert events.status_code == 200
    event_types = [event["event_type"] for event in events.json()]
    assert "DOCUMENT_CHECK_COMPLETED" in event_types
    assert "FINANCIAL_VALIDATION_COMPLETED" in event_types
    report = client.get(f"/applications/{application_id}/underwriting/report")
    assert report.status_code == 200
    assert report.json()["status"] == "Needs Attention"
    assert report.json()["human_review_required"] is True
