import pytest
from fastapi.testclient import TestClient

from main import app
from services.auth import get_current_user


def test_business_routes_require_authentication():
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        response = client.get("/applications")
    assert response.status_code == 401


def test_invalid_bearer_token_is_rejected():
    app.dependency_overrides.pop(get_current_user, None)
    with TestClient(app) as client:
        response = client.get("/applications", headers={"Authorization": "Bearer invalid"})
    assert response.status_code == 401
