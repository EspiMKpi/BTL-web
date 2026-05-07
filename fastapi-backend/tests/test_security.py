"""
Tests for security utilities — password hashing, JWT creation and decoding.
"""

import pytest
from datetime import datetime, timedelta, timezone

import jwt

from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from app.core.config import settings


class TestPasswordHashing:
    def test_hash_and_verify(self):
        password = "TestPassword123!"
        hashed = hash_password(password)
        assert hashed != password
        assert verify_password(password, hashed) is True

    def test_wrong_password(self):
        hashed = hash_password("CorrectPassword")
        assert verify_password("WrongPassword", hashed) is False

    def test_different_hashes(self):
        """bcrypt should produce different hashes for the same password (salt)."""
        h1 = hash_password("same_password")
        h2 = hash_password("same_password")
        assert h1 != h2
        # But both should verify
        assert verify_password("same_password", h1) is True
        assert verify_password("same_password", h2) is True


class TestAccessToken:
    def test_create_and_decode(self):
        token = create_access_token("user123", "test@example.com")
        payload = decode_access_token(token)
        assert payload is not None
        assert payload["user_id"] == "user123"
        assert payload["email"] == "test@example.com"
        assert "exp" in payload

    def test_token_expiry(self):
        token = create_access_token("user123", "test@example.com")
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        exp = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        # Should expire ~7 days from now
        assert exp > datetime.now(timezone.utc) + timedelta(days=6)
        assert exp < datetime.now(timezone.utc) + timedelta(days=8)

    def test_decode_invalid_token(self):
        result = decode_access_token("invalid.token.here")
        assert result is None

    def test_decode_expired_token(self):
        payload = {
            "user_id": "user123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
        result = decode_access_token(token)
        assert result is None

    def test_decode_wrong_secret(self):
        payload = {
            "user_id": "user123",
            "email": "test@example.com",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        }
        token = jwt.encode(payload, "wrong_secret", algorithm=settings.JWT_ALGORITHM)
        result = decode_access_token(token)
        assert result is None


class TestConfig:
    def test_cors_origins_list(self):
        origins = settings.cors_origins_list
        assert isinstance(origins, list)
        assert "http://localhost:5173" in origins

    def test_default_settings(self):
        assert settings.DB_NAME == "movie_db"
        assert settings.JWT_ALGORITHM == "HS256"
        assert settings.JWT_EXPIRATION_DAYS == 7
