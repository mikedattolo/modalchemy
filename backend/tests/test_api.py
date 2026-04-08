"""Tests for the FastAPI application endpoints."""

import pytest
from httpx import ASGITransport, AsyncClient

from modforge.main import app


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    resp = await client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"
    assert "version" in data


@pytest.mark.asyncio
async def test_get_settings(client):
    resp = await client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    assert "backend_port" in data
    assert "decompiler" in data


@pytest.mark.asyncio
async def test_list_workspaces_empty(client):
    resp = await client.get("/api/workspaces")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_decompile_rejects_non_jar(client):
    resp = await client.post(
        "/api/decompile",
        files={"file": ("test.txt", b"not a jar", "text/plain")},
    )
    assert resp.status_code == 400
    assert "jar" in resp.json()["detail"].lower()
