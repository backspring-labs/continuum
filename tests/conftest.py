"""
Shared pytest fixtures for Continuum tests.
"""

import pytest
from fastapi.testclient import TestClient

from continuum.main import app
from continuum.domain.auth import UserContext
from continuum.adapters.web import api


@pytest.fixture
def client():
    """Create test client with lifespan context manager."""
    with TestClient(app) as client:
        yield client


@pytest.fixture
def limited_user():
    """Create a user with limited capabilities (no deploy.production)."""
    return UserContext(
        user_id="limited_user",
        username="Limited User",
        roles=("viewer",),
        capabilities=("view.metrics", "execute.safe"),  # No deploy.production
    )


@pytest.fixture
def client_with_limited_user(limited_user):
    """
    Create test client with a limited-capability user.

    This overrides the get_current_user dependency to return
    a user without wildcard capabilities, enabling authorization
    denial testing.
    """
    def get_limited_user():
        return limited_user

    # Override the dependency
    app.dependency_overrides[api.get_current_user] = get_limited_user

    with TestClient(app) as client:
        yield client

    # Clean up the override
    app.dependency_overrides.clear()


# Playwright fixtures for E2E tests
# These require both backend (port 4040) and frontend (port 5173) to be running

@pytest.fixture(scope="session")
def browser_context_args():
    """Configure browser context for E2E tests."""
    return {
        "viewport": {"width": 1280, "height": 720},
        "ignore_https_errors": True,
    }


@pytest.fixture
def e2e_page(page):
    """
    Playwright page fixture for E2E tests.

    Requires servers to be running:
    - Backend: continuum serve (port 4040)
    - Frontend: cd web && npm run dev (port 5173)

    Usage in tests:
        def test_something(e2e_page):
            e2e_page.goto("http://localhost:5173")
            ...
    """
    # Set a reasonable timeout for E2E operations
    page.set_default_timeout(10000)  # 10 seconds
    yield page
