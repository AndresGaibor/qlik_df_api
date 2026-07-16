import secrets
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Query, status

from app.remote.csv_repository import CsvDataflowRepository
from app.remote.schemas import ReplaceDataflowsRequest
from remote_server.config import RemoteSettings

settings = RemoteSettings()
repository = CsvDataflowRepository(settings.remote_csv_path)
app = FastAPI(title="Qlik Dataflows Remote API", version="0.1.0")


def require_api_key(api_key: Annotated[str | None, Header(alias="X-API-Key")] = None) -> None:
    if not api_key or not secrets.compare_digest(
        api_key, settings.remote_api_key.get_secret_value()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="API key invalida")


@app.get("/health")
async def health() -> dict[str, dict[str, str]]:
    return {"data": {"status": "ok"}}


@app.put("/api/v1/dataflows")
async def replace_dataflows(
    payload: ReplaceDataflowsRequest,
    _: Annotated[None, Depends(require_api_key)],
) -> dict[str, dict[str, int]]:
    repository.replace(payload.data)
    return {"data": {"count": len(payload.data)}}


@app.get("/api/v1/dataflows")
async def list_dataflows(
    _: Annotated[None, Depends(require_api_key)],
    dataflow_id: str | None = Query(default=None),
    dataflow_name: str | None = Query(default=None),
) -> dict[str, list[dict[str, object]]]:
    records = repository.list_records()
    if dataflow_id:
        records = [record for record in records if record.dataflow_id == dataflow_id]
    if dataflow_name:
        records = [record for record in records if record.dataflow_name == dataflow_name]
    return {"data": [record.model_dump() for record in records]}
