import io

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base, get_db
from main import app
from services import nemotron


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'analysis.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)

    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    monkeypatch.setattr(nemotron, "NVIDIA_API_KEY", "test-key")
    monkeypatch.setattr(nemotron, "NVIDIA_BASE_URL", "https://nim.test/v1")
    monkeypatch.setattr(nemotron, "NVIDIA_MODEL", "test-nemotron")
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def pdf_bytes() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Employee: Alex Example\nGross monthly salary: 5000 USD")
    data = pdf.tobytes()
    pdf.close()
    return data


def application_id(client: TestClient) -> str:
    response = client.post(
        "/applications",
        json={"borrower_name": "Alex Example", "monthly_income": 5000, "monthly_debt": 500, "loan_amount": 200000, "property_value": 300000},
    )
    return response.json()["id"]


def extracted_document(client: TestClient, app_id: str) -> str:
    uploaded = client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("salary.pdf", io.BytesIO(pdf_bytes()), "application/pdf")},
        data={"category": "Salary Slip"},
    ).json()
    response = client.post(f"/applications/{app_id}/documents/{uploaded['id']}/extract")
    assert response.status_code == 200
    return uploaded["id"]


def test_analysis_requires_existing_extraction(client):
    app_id = application_id(client)
    response = client.post(f"/applications/{app_id}/documents/missing/analyze")
    assert response.status_code == 404

    uploaded = client.post(
        f"/applications/{app_id}/documents",
        files={"file": ("broken.pdf", b"%PDF-broken", "application/pdf")},
        data={"category": "Salary Slip"},
    ).json()
    document_id = uploaded["id"]
    extraction = client.post(f"/applications/{app_id}/documents/{document_id}/extract")
    assert extraction.status_code == 422
    response = client.post(f"/applications/{app_id}/documents/{document_id}/analyze")
    assert response.status_code == 409


def test_mocked_nim_document_and_application_analysis(client, monkeypatch):
    app_id = application_id(client)
    document_id = extracted_document(client, app_id)
    second_document_id = extracted_document(client, app_id)

    def fake_post(messages):
        if "cross-document" in messages[0]["content"]:
            return {
                "summary": "Documents support the stated income.",
                "borrower_details": {},
                "income_information": {"gross_monthly_salary": {"value": 5000, "source": {"document_id": document_id, "page": 1}}},
                "document_coverage": ["Salary Slip"],
                "missing_information": ["Pay period"],
                "conflicting_values": [],
                "review_flags": ["Verify against original"],
                "source_document_ids": [document_id, second_document_id],
            }
        return {
            "summary": "Salary slip identifies gross salary.",
            "fields": {"employee_name": {"value": "Alex Example", "source": {"document_id": document_id, "page": 1}}},
            "missing_information": ["Pay period"],
            "review_flags": [],
        }

    monkeypatch.setattr(nemotron, "_post", fake_post)
    analyzed = client.post(f"/applications/{app_id}/documents/{document_id}/analyze")
    assert analyzed.status_code == 200
    assert analyzed.json()["status"] == "Completed"
    assert analyzed.json()["structured_fields"]["employee_name"]["value"] == "Alex Example"

    second_analyzed = client.post(f"/applications/{app_id}/documents/{second_document_id}/analyze")
    assert second_analyzed.status_code == 200
    summary = client.post(f"/applications/{app_id}/analyze")
    assert summary.status_code == 200
    assert summary.json()["summary"] == "Documents support the stated income."

    fetched = client.get(f"/applications/{app_id}/analysis")
    assert fetched.status_code == 200
    assert fetched.json()["source_document_ids"] == [document_id, second_document_id]


def test_structured_output_validation_rejects_invalid_field_source():
    from pydantic import ValidationError
    from schemas.analysis import NemotronDocumentResult

    with pytest.raises(ValidationError):
        NemotronDocumentResult.model_validate({"summary": "bad", "fields": {"name": {"source": {"page": 0}}}})


def test_nim_timeout_is_returned_as_safe_error(client, monkeypatch):
    app_id = application_id(client)
    document_id = extracted_document(client, app_id)

    def timeout(_messages):
        raise nemotron.NemotronError("timeout", "NVIDIA NIM request timed out.")

    monkeypatch.setattr(nemotron, "_post", timeout)
    response = client.post(f"/applications/{app_id}/documents/{document_id}/analyze")
    assert response.status_code == 502
    assert response.json()["detail"] == "NVIDIA NIM request timed out."
