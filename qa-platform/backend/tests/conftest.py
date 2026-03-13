"""
Shared pytest fixtures for the qa-platform backend test suite.

Provides:
  - Environment variable setup (SECRET_KEY, DATABASE_URL)
  - A SQLAlchemy in-memory test database session with rollback-after-each-test
  - A helper function register_and_login() that registers a user via the API
    and returns the JWT access token string
"""
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient

# ── Force test environment variables BEFORE importing any application modules ──
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from src.models.base import Base
# Import all models so their table definitions are registered on Base.metadata
from src.models.user import User  # noqa: F401
from src.models.defect import Defect  # noqa: F401
from src.models.change import Change  # noqa: F401
from src.models.impact_analysis import ImpactAnalysis  # noqa: F401
from src.models.test_case import TestCase  # noqa: F401
from src.app.database import get_db
from src.main import app


# ---------------------------------------------------------------------------
# In-memory test engine (module-scoped — created once per test session)
# ---------------------------------------------------------------------------

TEST_DB_URL = "sqlite:///:memory:"

_test_engine = create_engine(
    TEST_DB_URL,
    connect_args={"check_same_thread": False},
)
Base.metadata.create_all(_test_engine)

_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


# ---------------------------------------------------------------------------
# db_session fixture — function-scoped with rollback after each test
# ---------------------------------------------------------------------------

@pytest.fixture()
def db_session():
    """
    Yield a SQLAlchemy Session backed by the test SQLite DB.
    The session is rolled back after each test so tests remain isolated.
    """
    connection = _test_engine.connect()
    transaction = connection.begin()
    session = _TestSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()


# ---------------------------------------------------------------------------
# FastAPI TestClient fixture (function-scoped, overrides get_db dependency)
# ---------------------------------------------------------------------------

@pytest.fixture()
def client(db_session):
    """
    Return a FastAPI TestClient whose get_db dependency is overridden to use
    the test db_session, ensuring full request → DB isolation per test.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # rollback is handled by db_session fixture

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.pop(get_db, None)


# ---------------------------------------------------------------------------
# Helper: register_and_login
# ---------------------------------------------------------------------------

def register_and_login(client: TestClient, email: str, password: str, username: str) -> str:
    """
    Register a new user via POST /api/auth/register, then assert success
    and return the JWT access_token string.

    Args:
        client:   A FastAPI TestClient instance.
        email:    The email address for the new user.
        password: The plaintext password (>= 8 characters).
        username: The username for the new user.

    Returns:
        The JWT access_token string from the registration response.

    Raises:
        AssertionError: if the registration request does not return HTTP 201.
    """
    response = client.post(
        "/api/auth/register",
        json={"email": email, "password": password, "username": username},
    )
    assert response.status_code == 201, (
        f"register_and_login failed for {email}: "
        f"status={response.status_code}, body={response.text}"
    )
    return response.json()["access_token"]
