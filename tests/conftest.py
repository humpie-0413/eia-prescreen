"""Shared fixtures for the test suite."""

import sys
from pathlib import Path

import pytest

# Ensure the project root is on sys.path so `backend.app.*` imports resolve.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@pytest.fixture(autouse=True)
def _override_auth():
    """Override JWT auth dependency globally so tests run without a real token."""
    from backend.app.main import app
    from backend.app.core.auth import get_auth_user

    app.dependency_overrides[get_auth_user] = lambda: {
        "user_id": "test-user-00000000",
        "role": "analyst",
    }
    yield
    app.dependency_overrides.pop(get_auth_user, None)


@pytest.fixture()
def auth_header() -> dict[str, str]:
    """Return a valid Bearer token header for direct HTTP testing."""
    from backend.app.core.auth import create_access_token

    token = create_access_token("test-user-00000000", "analyst")
    return {"Authorization": f"Bearer {token}"}
