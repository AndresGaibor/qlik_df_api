import importlib

from fastapi.testclient import TestClient


def test_remote_server_replaces_csv_and_requires_api_key(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("REMOTE_API_KEY", "clave-de-prueba")
    monkeypatch.setenv("REMOTE_CSV_PATH", str(tmp_path / "dataflows.csv"))
    module = importlib.import_module("remote_server.main")
    module = importlib.reload(module)

    payload = {
        "data": [
            {
                "dataflow_id": "flow-1",
                "app_id": "app-1",
                "dataflow_name": "Flujo 1",
                "description": "Descripcion",
            }
        ]
    }
    with TestClient(module.app) as client:
        unauthorized = client.put("/api/v1/dataflows", json=payload)
        replaced = client.put(
            "/api/v1/dataflows", json=payload, headers={"X-API-Key": "clave-de-prueba"}
        )
        listed = client.get(
            "/api/v1/dataflows", headers={"X-API-Key": "clave-de-prueba"}
        )
        by_name = client.get(
            "/api/v1/dataflows/name/Flujo_1",
            headers={"X-API-Key": "clave-de-prueba"},
        )

    assert unauthorized.status_code == 401
    assert replaced.json() == {"data": {"count": 1}}
    assert listed.json()["data"][0]["dataflow_id"] == "flow-1"
    assert by_name.status_code == 200
    assert by_name.json()["data"][0]["dataflow_name"] == "Flujo 1"
    assert by_name.json()["data"][0]["app_id"] == "app-1"
