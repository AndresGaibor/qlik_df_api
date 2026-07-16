import pytest
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from app.core.config import Settings, get_settings
from app.main import create_app


@pytest.mark.asyncio
async def test_health_returns_api_status() -> None:
    app = create_app(database_url="sqlite+aiosqlite:///:memory:")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"data": {"status": "ok"}}


def test_runs_endpoint_initializes_sqlite_database(tmp_path) -> None:
    database_url = f"sqlite+aiosqlite:///{tmp_path / 'test.db'}"
    app = create_app(database_url=database_url)

    with TestClient(app) as client:
        response = client.get("/api/v1/qlik/runs")

    assert response.status_code == 200
    assert response.json() == {"data": []}


def test_runs_endpoint_validates_pagination(tmp_path) -> None:
    app = create_app(database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}")

    with TestClient(app) as client:
        response = client.get("/api/v1/qlik/runs?limit=101")

    assert response.status_code == 400


def test_run_endpoint_rejects_missing_qlik_credentials(tmp_path, monkeypatch) -> None:
    for key in ("QLIK_EMAIL", "QLIK_PASSWORD", "QLIK_SPACE"):
        monkeypatch.delenv(key, raising=False)
    get_settings.cache_clear()
    app = create_app(
        settings=Settings(
            _env_file=None,
            database_url=f"sqlite+aiosqlite:///{tmp_path / 'test.db'}",
        )
    )

    with TestClient(app) as client:
        response = client.post("/api/v1/qlik/runs", json={"space": "Espacio"})

    assert response.status_code == 422
    assert "QLIK_EMAIL" in response.json()["detail"]
