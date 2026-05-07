"""
Tests for health check endpoint and app configuration.
"""

import pytest


class TestHealthCheck:
    async def test_health_check(self, client):
        resp = await client.get("/api/test")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_nonexistent_route(self, client):
        resp = await client.get("/api/nonexistent")
        assert resp.status_code == 404

    async def test_cors_headers(self, client):
        resp = await client.options(
            "/api/test",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET",
            },
        )
        # FastAPI CORS middleware should allow this
        assert resp.status_code in (200, 204)
