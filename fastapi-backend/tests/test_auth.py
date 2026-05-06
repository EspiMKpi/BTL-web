"""
Tests for auth router — register, login, me.
"""

import pytest


# ── Register ──────────────────────────────────────────────────────────────

class TestRegister:
    async def test_register_success(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={"email": "new@vozflix.com", "password": "StrongPass1"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert "token" in body
        assert body["user"]["email"] == "new@vozflix.com"
        assert body["user"]["username"] == "new"  # derived from email

    async def test_register_duplicate_email(self, client, test_user):
        resp = await client.post(
            "/api/auth/register",
            json={"email": test_user["email"], "password": "StrongPass1"},
        )
        assert resp.status_code == 409

    async def test_register_short_password(self, client):
        resp = await client.post(
            "/api/auth/register",
            json={"email": "short@vozflix.com", "password": "123"},
        )
        assert resp.status_code == 400
        assert "8 characters" in resp.json()["detail"]

    async def test_register_missing_fields(self, client):
        resp = await client.post("/api/auth/register", json={"email": ""})
        assert resp.status_code == 422  # pydantic validation


# ── Login ─────────────────────────────────────────────────────────────────

class TestLogin:
    async def test_login_success(self, client, test_user):
        resp = await client.post(
            "/api/auth/login",
            json={"email": test_user["email"], "password": "Test1234!"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "token" in body
        assert body["user"]["email"] == test_user["email"]

    async def test_login_wrong_password(self, client, test_user):
        resp = await client.post(
            "/api/auth/login",
            json={"email": test_user["email"], "password": "WrongPass1"},
        )
        assert resp.status_code == 401

    async def test_login_unknown_email(self, client):
        resp = await client.post(
            "/api/auth/login",
            json={"email": "nobody@vozflix.com", "password": "Whatever1"},
        )
        assert resp.status_code == 401


# ── Me ────────────────────────────────────────────────────────────────────

class TestMe:
    async def test_me_authenticated(self, client, auth_headers):
        resp = await client.get("/api/auth/me", headers=auth_headers)
        assert resp.status_code == 200
        body = resp.json()
        assert body["email"] == "tester@vozflix.com"
        assert body["username"] == "tester"

    async def test_me_no_token(self, client):
        resp = await client.get("/api/auth/me")
        assert resp.status_code == 401

    async def test_me_invalid_token(self, client):
        resp = await client.get(
            "/api/auth/me",
            headers={"Authorization": "Bearer invalid.jwt.token"},
        )
        assert resp.status_code == 401
