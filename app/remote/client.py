import asyncio
import json
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.remote.schemas import DataflowRecord


def _replace_sync(url: str, api_key: str, records: list[DataflowRecord]) -> int:
    request = Request(
        f"{url.rstrip('/')}/api/v1/dataflows",
        data=json.dumps({"data": [record.model_dump() for record in records]}).encode(),
        headers={"Content-Type": "application/json", "X-API-Key": api_key},
        method="PUT",
    )
    with urlopen(request, timeout=60) as response:
        return int(json.loads(response.read().decode())["data"]["count"])


async def reemplazar_dataflows(
    url: str, api_key: str, records: list[DataflowRecord]
) -> int:
    try:
        return await asyncio.to_thread(_replace_sync, url, api_key, records)
    except (HTTPError, URLError, TimeoutError) as error:
        raise RuntimeError(f"No se pudo enviar dataflows al servidor remoto: {error}") from error
