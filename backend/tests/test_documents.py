import io
from pathlib import Path

import fitz
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base, get_db
from main import app
from services import document_storage


@pytest.fixture()
def client(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    upload_dir = tmp_path / "uploads"
    monkeypatch.setattr(document_storage, "UPLOADS_DIR", upload_dir)

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


def create_application(client: TestClient) -> str:
    response = client.post(
        "/applications",
        json={
            "borrower_name": "Document Test",
            "monthly_income": 5000,
            "monthly_debt": 1000,
            "loan_amount": 200000,
            "property_value": 300000,
        },
    )
    assert response.status_code == 201
    return response.json()["id"]


def sample_pdf() -> bytes:
    pdf = fitz.open()
    page = pdf.new_page()
    page.insert_text((72, 72), "Monthly income: 5000")
    content = pdf.tobytes()
    pdf.close()
    return content


def test_missing_application_and_unsupported_file(client):
    response = client.get("/applications/not-real/documents")
    assert response.status_code == 404

    application_id = create_application(client)
    response = client.post(
        f"/applications/{application_id}/documents",
        files={"file": ("notes.txt", b"not supported", "text/plain")},
        data={"category": "Other"},
    )
    assert response.status_code == 415


def test_upload_list_and_extract_text_pdf(client):
    application_id = create_application(client)
    response = client.post(
        f"/applications/{application_id}/documents",
        files={"file": ("income.pdf", io.BytesIO(sample_pdf()), "application/pdf")},
        data={"category": "Salary Slip"},
    )
    assert response.status_code == 201
    document = response.json()
    assert document["category"] == "Salary Slip"

    listed = client.get(f"/applications/{application_id}/documents")
    assert listed.status_code == 200
    assert len(listed.json()) == 1

    extracted = client.post(f"/applications/{application_id}/documents/{document['id']}/extract")
    assert extracted.status_code == 200
    assert "Monthly income: 5000" in extracted.json()["extracted_text"]

    text = client.get(f"/applications/{application_id}/documents/{document['id']}/text")
    assert text.status_code == 200
    assert "Page 1" in text.json()["extracted_text"]


def test_corrupt_pdf_is_rejected(client):
    application_id = create_application(client)
    response = client.post(
        f"/applications/{application_id}/documents",
        files={"file": ("broken.pdf", b"%PDF-not-a-real-document", "application/pdf")},
        data={"category": "Other"},
    )
    assert response.status_code == 201
    document_id = response.json()["id"]
    extracted = client.post(f"/applications/{application_id}/documents/{document_id}/extract")
    assert extracted.status_code == 422
    assert extracted.json()["detail"]
