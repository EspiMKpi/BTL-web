"""
Tests for core.deps — get_current_user and get_optional_current_user.
Exercises the dependency layer directly via HTTP calls through the /api/auth/me endpoint.
"""

import pytest
from bson import ObjectId

from app.core.security import create_access_token


class TestGetCurrentUser:
    async def test_valid_token(self, client, test_user, auth_headers):
        resp = await client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        assert resp.json()["email"] == test_user["email"]

    async def test_expired_token(self, client, db):
        """A token whose exp is in the past should be rejected."""
        from datetime import datetime, timedelta, timezone
        import jwt
        from app.core.config import settings

        payload = {
            "user_id": str(ObjectId()),
            "email": "expired@vozflix.com",
            "exp": datetime.now(timezone.utc) - timedelta(hours=1),
        }
        token = jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401

    async def test_token_for_deleted_user(self, client, db):
        """Token is valid but user no longer exists in DB."""
        fake_id = str(ObjectId())
        token = create_access_token(fake_id, "ghost@vozflix.com")

        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 401
        assert "not found" in resp.json()["detail"].lower()

    async def test_no_auth_header(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_malformed_header(self, client):
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": "NotBearer somevalue"},
        )
        assert resp.status_code == 401


class TestGetOptionalCurrentUser:
    """The /api/content/home endpoint uses optional auth."""

    async def test_unauthenticated_home(self, client):
        resp = await client.get("/api/content/home")
        # Should succeed even without auth — returns rails without continue-watching
        assert resp.status_code == 200
        assert "rails" in resp.json()

    async def test_authenticated_home(self, client, auth_headers):
        resp = await client.get("/api/content/home", headers=auth_headers)
        assert resp.status_code == 200
        assert "rails" in resp.json()

    async def test_bad_token_returns_public_view(self, client):
        resp = await client.get(
            "/api/content/home",
            headers={"Authorization": "Bearer garbage"},
        )
        # Optional auth should not 401 — just treat as unauthenticated
        assert resp.status_code == 200
