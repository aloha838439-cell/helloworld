"""
Integration tests for the /api/auth endpoints.

Covers:
  C4 — POST /api/auth/register happy path
  C5 — POST /api/auth/register error cases
  C6 — POST /api/auth/login JWT issuance
  C7 — GET  /api/auth/me current-user endpoint

All tests use a FastAPI TestClient backed by an in-memory SQLite database
(provided by the conftest.py db_session fixture) so they never touch any
production or shared database.
"""
import os
import time
import pytest
from fastapi.testclient import TestClient
from passlib.context import CryptContext
from jose import jwt as jose_jwt
from datetime import datetime, timedelta, timezone

# Ensure test env vars are set before importing application modules
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test_auth.db")

from src.main import app
from src.app.database import get_db
from tests.conftest import register_and_login  # shared helper

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "test-secret-key")
ALGORITHM = "HS256"


# ---------------------------------------------------------------------------
# C4 — Register happy path
# ---------------------------------------------------------------------------

class TestRegisterSuccess:
    """C4: Successful user registration."""

    def test_register_success(self, client):
        """POST /api/auth/register with valid data returns HTTP 201."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "newuser@example.com",
                "password": "securepass123",
                "username": "newuser",
            },
        )
        assert response.status_code == 201
        data = response.json()
        # Must contain an access token
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        # User sub-object must be present
        assert "user" in data
        user_data = data["user"]
        assert user_data["email"] == "newuser@example.com"
        assert user_data["username"] == "newuser"

    def test_register_response_has_no_hashed_password(self, client):
        """The registration response must NOT expose hashed_password."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "nohash@example.com",
                "password": "securepass456",
                "username": "nohashuser",
            },
        )
        assert response.status_code == 201
        data = response.json()
        # hashed_password must not appear anywhere in the top-level response
        assert "hashed_password" not in data
        # Also must not appear in the nested user object
        assert "hashed_password" not in data.get("user", {})

    def test_register_password_is_hashed(self, client, db_session):
        """The password stored in the DB must be a bcrypt hash, not plaintext."""
        from src.models.user import User

        plain_password = "StrongPassword99"
        email = "hashcheck@example.com"

        response = client.post(
            "/api/auth/register",
            json={
                "email": email,
                "password": plain_password,
                "username": "hashcheckuser",
            },
        )
        assert response.status_code == 201

        # Query the DB directly to verify the stored hash
        user = db_session.query(User).filter(User.email == email).first()
        assert user is not None
        assert user.hashed_password != plain_password
        # bcrypt.verify confirms the hash matches the original password
        assert pwd_context.verify(plain_password, user.hashed_password) is True


# ---------------------------------------------------------------------------
# C5 — Register error cases
# ---------------------------------------------------------------------------

class TestRegisterErrors:
    """C5: Registration validation and conflict errors."""

    def test_register_duplicate_email(self, client):
        """Registering with an already-used email must return HTTP 400."""
        payload = {
            "email": "duplicate@example.com",
            "password": "FirstPass123",
            "username": "firstuser",
        }
        # First registration — should succeed
        first = client.post("/api/auth/register", json=payload)
        assert first.status_code == 201

        # Second registration with the same email — must fail
        second = client.post(
            "/api/auth/register",
            json={
                "email": "duplicate@example.com",
                "password": "AnotherPass123",
                "username": "seconduser",
            },
        )
        # The router returns 400 for duplicate email
        assert second.status_code == 400
        assert "email" in second.json()["detail"].lower() or "registered" in second.json()["detail"].lower()

    def test_register_short_password(self, client):
        """A password shorter than 8 characters must return HTTP 400."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "shortpass@example.com",
                "password": "abc",          # only 3 chars
                "username": "shortpassuser",
            },
        )
        # Router validates password length and returns 400
        assert response.status_code == 400
        detail = response.json()["detail"].lower()
        assert "password" in detail or "characters" in detail

    def test_register_missing_email_field(self, client):
        """Omitting the required email field must return HTTP 422 (Pydantic validation)."""
        response = client.post(
            "/api/auth/register",
            json={
                "password": "ValidPass123",
                "username": "missingemail",
            },
        )
        assert response.status_code == 422

    def test_register_missing_password_field(self, client):
        """Omitting the required password field must return HTTP 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "nopassword@example.com",
                "username": "nopassworduser",
            },
        )
        assert response.status_code == 422

    def test_register_missing_username_field(self, client):
        """Omitting the required username field must return HTTP 422."""
        response = client.post(
            "/api/auth/register",
            json={
                "email": "nousername@example.com",
                "password": "ValidPass123",
            },
        )
        assert response.status_code == 422

    def test_register_duplicate_username(self, client):
        """Registering with an already-used username must return HTTP 400."""
        # First registration
        first = client.post(
            "/api/auth/register",
            json={
                "email": "user_a@example.com",
                "password": "PassForA123",
                "username": "shared_username",
            },
        )
        assert first.status_code == 201

        # Second registration with the same username
        second = client.post(
            "/api/auth/register",
            json={
                "email": "user_b@example.com",
                "password": "PassForB123",
                "username": "shared_username",
            },
        )
        assert second.status_code == 400
        assert "username" in second.json()["detail"].lower() or "taken" in second.json()["detail"].lower()


# ---------------------------------------------------------------------------
# C6 — Login JWT issuance
# ---------------------------------------------------------------------------

class TestLoginJWT:
    """C6: Login endpoint JWT creation and validation."""

    def test_login_success_returns_jwt(self, client):
        """A valid login must return HTTP 200 with an access_token whose sub equals the user's id."""
        # Register a user first
        reg = client.post(
            "/api/auth/register",
            json={
                "email": "jwtuser@example.com",
                "password": "JWTPass9999",
                "username": "jwtuser",
            },
        )
        assert reg.status_code == 201
        user_id = reg.json()["user"]["id"]

        # Login
        response = client.post(
            "/api/auth/login",
            json={"email": "jwtuser@example.com", "password": "JWTPass9999"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

        # Decode the JWT and verify the 'sub' claim equals the user's id
        payload = jose_jwt.decode(
            data["access_token"],
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        assert "sub" in payload
        assert int(payload["sub"]) == user_id

    def test_login_jwt_expires_in_30min(self, client):
        """The JWT exp claim must be approximately now + 1800 seconds (±100s tolerance)."""
        # Register user
        client.post(
            "/api/auth/register",
            json={
                "email": "expcheck@example.com",
                "password": "ExpCheck123",
                "username": "expcheckuser",
            },
        )

        before = time.time()
        response = client.post(
            "/api/auth/login",
            json={"email": "expcheck@example.com", "password": "ExpCheck123"},
        )
        after = time.time()

        assert response.status_code == 200
        token = response.json()["access_token"]

        payload = jose_jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM],
            options={"verify_exp": False},
        )
        exp = payload["exp"]
        # exp should be ~30 minutes (1800 seconds) after the request was issued
        expected_exp_low = before + 1800 - 100
        expected_exp_high = after + 1800 + 100
        assert expected_exp_low <= exp <= expected_exp_high, (
            f"exp={exp} is not within ±100s of now+1800 "
            f"(expected range [{expected_exp_low:.0f}, {expected_exp_high:.0f}])"
        )

    def test_login_wrong_password_401(self, client):
        """Logging in with an incorrect password must return HTTP 401."""
        client.post(
            "/api/auth/register",
            json={
                "email": "wrongpass@example.com",
                "password": "CorrectPass123",
                "username": "wrongpassuser",
            },
        )

        response = client.post(
            "/api/auth/login",
            json={"email": "wrongpass@example.com", "password": "WrongPass999"},
        )
        assert response.status_code == 401

    def test_login_nonexistent_user_401(self, client):
        """Logging in with an email that has never been registered must return HTTP 401."""
        response = client.post(
            "/api/auth/login",
            json={"email": "ghost@nonexistent.com", "password": "AnyPassword1"},
        )
        assert response.status_code == 401

    def test_login_response_has_no_hashed_password(self, client):
        """The login response must NOT expose hashed_password."""
        client.post(
            "/api/auth/register",
            json={
                "email": "logincheck@example.com",
                "password": "LoginCheck123",
                "username": "logincheckuser",
            },
        )
        response = client.post(
            "/api/auth/login",
            json={"email": "logincheck@example.com", "password": "LoginCheck123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "hashed_password" not in data
        assert "hashed_password" not in data.get("user", {})


# ---------------------------------------------------------------------------
# C7 — /me endpoint
# ---------------------------------------------------------------------------

class TestMeEndpoint:
    """C7: GET /api/auth/me — current user retrieval."""

    def test_me_with_valid_token(self, client):
        """A valid Bearer token must return HTTP 200 with the correct user email."""
        token = register_and_login(
            client,
            email="me_valid@example.com",
            password="MeValid1234",
            username="mevaliduser",
        )

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["email"] == "me_valid@example.com"
        assert data["username"] == "mevaliduser"

    def test_me_response_has_no_hashed_password(self, client):
        """GET /api/auth/me must NOT expose hashed_password."""
        token = register_and_login(
            client,
            email="me_nohash@example.com",
            password="MeNoHash123",
            username="menohashuser",
        )

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        assert "hashed_password" not in response.json()

    def test_me_without_token(self, client):
        """Calling GET /api/auth/me without any Authorization header must return HTTP 401."""
        response = client.get("/api/auth/me")
        assert response.status_code == 401

    def test_me_with_expired_token(self, client):
        """A JWT whose exp is in the past must cause GET /api/auth/me to return HTTP 401."""
        # Create a token that expired 1 hour ago
        expired_payload = {
            "sub": "999999",
            "exp": datetime.now(tz=timezone.utc) - timedelta(hours=1),
        }
        expired_token = jose_jwt.encode(expired_payload, SECRET_KEY, algorithm=ALGORITHM)

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert response.status_code == 401

    def test_me_with_invalid_token_signature(self, client):
        """A JWT signed with a different key must return HTTP 401."""
        wrong_key_payload = {
            "sub": "1",
            "exp": datetime.now(tz=timezone.utc) + timedelta(minutes=30),
        }
        bad_token = jose_jwt.encode(wrong_key_payload, "completely-wrong-secret", algorithm=ALGORITHM)

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {bad_token}"},
        )
        assert response.status_code == 401

    def test_me_with_malformed_token(self, client):
        """A completely malformed Bearer value must return HTTP 401."""
        response = client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer not.a.valid.jwt.at.all"},
        )
        assert response.status_code == 401

    def test_me_returns_correct_user_fields(self, client):
        """GET /api/auth/me response must include id, email, username, is_active, is_admin."""
        token = register_and_login(
            client,
            email="me_fields@example.com",
            password="MeFields123",
            username="mefieldsuser",
        )

        response = client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200
        data = response.json()
        for field in ("id", "email", "username", "is_active", "is_admin"):
            assert field in data, f"Expected field '{field}' missing from /me response"
