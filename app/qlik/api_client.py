from typing import Any

import httpx


class QlikCloudAPIError(RuntimeError):
    """Error al interactuar con la API de Qlik Cloud."""


def _extraer_tenant_url(url_pagina: str) -> str:
    parts = url_pagina.split("/")
    if len(parts) >= 3:
        return f"{parts[0]}//{parts[2]}"
    raise QlikCloudAPIError(f"No se pudo extraer el tenant URL de: {url_pagina}")


def _mapear_dataflow(item: dict[str, Any]) -> dict[str, Any]:
    attrs = item.get("resourceAttributes", {})
    return {
        "dataflow_id": attrs.get("id") or item.get("resourceId", ""),
        "dataflow_name": item.get("name", ""),
        "description": item.get("description", ""),
        "resource_type": item.get("resourceSubType", ""),
        "space_id": item.get("spaceId", ""),
        "url": (item.get("links", {}).get("open", {}) or {}).get("href", ""),
        "created_at": attrs.get("createdDate", ""),
        "updated_at": attrs.get("modifiedDate", ""),
    }


async def _get_cookies_jar(cookies: list[dict[str, Any]]) -> dict[str, str]:
    jar: dict[str, str] = {}
    for cookie in cookies:
        name = cookie.get("name", "")
        value = cookie.get("value", "")
        if name and value:
            jar[name] = value
    return jar


async def listar_espacios(
    cookies: list[dict[str, Any]],
    tenant_url: str,
    nombre_espacio: str | None = None,
) -> list[dict[str, str]]:
    jar = await _get_cookies_jar(cookies)
    url = f"{tenant_url}/api/v1/spaces"
    params: dict[str, str] = {"limit": "100", "sort": "+name"}
    if nombre_espacio:
        params["name"] = nombre_espacio

    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.get(url, params=params, cookies=jar)
        if resp.status_code != 200:
            raise QlikCloudAPIError(
                f"Error listando espacios: {resp.status_code} {resp.text[:200]}"
            )
        data = resp.json()
    return data.get("data", [])


async def listar_dataflows_api(
    cookies: list[dict[str, Any]],
    tenant_url: str,
    space_id: str,
    resource_types: str | None = None,
) -> list[dict[str, Any]]:
    jar = await _get_cookies_jar(cookies)
    url = f"{tenant_url}/api/v1/items"
    default_types = (
        "app[dataflow-prep],app[single-table-prep],app[script],"
        "script[qvs],dataset[qix-df,qvd,connection_based_dataset]"
    )
    params: dict[str, str] = {
        "sort": "-recentlyUsed",
        "limit": "100",
        "spaceId": space_id,
        "resourceType": resource_types or default_types,
        "noActions": "true",
        "next": "",
    }

    todos: list[dict[str, Any]] = []
    async with httpx.AsyncClient(timeout=30) as client:
        while True:
            resp = await client.get(url, params=params, cookies=jar)
            if resp.status_code != 200:
                raise QlikCloudAPIError(
                    f"Error listando dataflows: {resp.status_code} {resp.text[:200]}"
                )
            data = resp.json()
            items = data.get("data", [])
            todos.extend(items)

            enlace_siguiente = (data.get("links") or {}).get("next", {})
            if not enlace_siguiente:
                break
            url = enlace_siguiente["href"]
            params = {}

    return [_mapear_dataflow(item) for item in todos]
