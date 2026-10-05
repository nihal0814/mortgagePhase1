import pytest

from main import app
from models.auth import User
from services.auth import get_current_user


@pytest.fixture(autouse=True)
def authenticated_test_user():
    """Keep legacy feature tests focused on business behavior after auth was added."""
    user = User(
        id="test-admin",
        full_name="Test Administrator",
        email="test-admin@example.com",
        password_hash="not-used",
        role="ADMIN",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)
