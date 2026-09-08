"""Shared fixtures: an authenticated TestClient with a stub workspace."""
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.core.auth import User, get_current_user
from app.core.deps import require_workspace

TEST_USER_ID = "user-123"
TEST_WORKSPACE = {
    "id": "ws-1",
    "user_id": TEST_USER_ID,
    "name": "Test Workspace",
    "created_at": None,
}


@pytest.fixture
def user_id():
    return TEST_USER_ID


@pytest.fixture
def workspace():
    return dict(TEST_WORKSPACE)


@pytest.fixture
def client():
    """TestClient with auth + workspace ownership stubbed out."""
    app.dependency_overrides[get_current_user] = lambda: User(id=TEST_USER_ID, email="t@example.com")
    app.dependency_overrides[require_workspace] = lambda: dict(TEST_WORKSPACE)
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client():
    """TestClient with NO overrides (auth active) for testing rejection."""
    return TestClient(app)
