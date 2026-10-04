from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.connection import Base, get_db
from main import app
from services.financial_validation import (
    FinancialValidationError,
    build_validation_result,
    calculate_dti,
    calculate_ltv,
    compare_value,
)


@pytest.fixture()
def client(tmp_path):
    test_engine = create_engine(
        f"sqlite:///{tmp_path / 'validation.db'}",
        connect_args={"check_same_thread": False},
    )
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


def application(**overrides):
    values = {
        "monthly_income": 100000,
        "monthly_debt": 20000,
        "loan_amount": 4000000,
        "property_value": 5000000,
        "borrower_name": "Rahul Sharma",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_dti_and_ltv_use_decimal_rounding():
    assert calculate_dti(20000, 100000) == 20
    assert calculate_ltv(4000000, 5000000) == 80


@pytest.mark.parametrize(
    ("function", "args"),
    [
        (calculate_dti, (1, 0)),
        (calculate_ltv, (1, 0)),
        (calculate_dti, (-1, 100)),
        (calculate_ltv, (-1, 100)),
    ],
)
def test_invalid_financial_values_raise(function, args):
    with pytest.raises(FinancialValidationError):
        function(*args)


def test_matching_and_tolerated_income_comparisons():
    assert compare_value("Monthly Income", 100000, 100000).status == "Verified Match"
    minor = compare_value("Monthly Income", 100000, 98000)
    assert minor.status == "Verified Match" or minor.status == "Minor Difference"
    assert minor.difference_percentage == 2.0


def test_validation_detects_discrepancy_and_loan_over_property():
    result = build_validation_result(
        application(),
        [
            {
                "structured_fields": {
                    "gross_monthly_salary": {"value": 90000, "source": {"document_id": "doc-1", "page": 1}},
                    "employee_name": {"value": "Rahul Sharma", "source": {"document_id": "doc-1", "page": 1}},
                }
            }
        ],
    )
    assert result["dti"] == 20.0
    assert result["ltv"] == 80.0
    assert result["validation_status"] == "Needs Review"
    assert any(issue.field_name == "Monthly Income" for issue in result["issues"])

    over_property = build_validation_result(application(loan_amount=6000000), [])
    assert any(issue.field_name == "Loan Amount" for issue in over_property["issues"])


def test_missing_credit_score_is_reported_without_inventing_one():
    result = build_validation_result(application(), [])
    assert result["credit_score"] is None
    assert "Credit score (not found in analyzed documents)" in result["missing_information"]


def test_validation_endpoint_persists_required_fields(client):
    created = client.post(
        "/applications",
        json={
            "borrower_name": "Route Test",
            "monthly_income": 100000,
            "monthly_debt": 20000,
            "loan_amount": 4000000,
            "property_value": 5000000,
        },
    )
    application_id = created.json()["id"]
    response = client.post(f"/applications/{application_id}/validate")
    assert response.status_code == 200
    body = response.json()
    assert body["validation_status"] == "Missing Information"
    assert body["income_consistency"] == "Unable to Compare"
