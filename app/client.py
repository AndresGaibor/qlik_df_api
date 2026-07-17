import argparse
import asyncio
import json
import sys

from app.core.config import get_settings
from app.qlik.automation import QlikAutomation


def construir_payload(
    *,
    headless: bool = False,
    tenant: str | None = None,
    space: str | None = None,
    dataflow: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {"headless": headless}
    if tenant:
        payload["tenant"] = tenant
    if space:
        payload["space"] = space
    if dataflow:
        payload["dataflow"] = dataflow
    return payload


async def ejecutar_scraping(
    *,
    tenant: str | None = None,
    space: str | None = None,
    dataflow: str | None = None,
    headless: bool | None = None,
) -> dict[str, object]:
    return await QlikAutomation(get_settings()).run(
        tenant_name=tenant,
        space_name=space,
        dataflow_name=dataflow,
        headless=headless,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta una exportacion Qlik mediante la API")
    parser.add_argument("--tenant")
    parser.add_argument("--space")
    parser.add_argument("--dataflow", help="Si se omite, exporta todos los dataflows")
    parser.add_argument("--headless", action="store_true", default=None)
    args = parser.parse_args()

    try:
        result = asyncio.run(
            ejecutar_scraping(
                tenant=args.tenant,
                space=args.space,
                dataflow=args.dataflow,
                headless=args.headless,
            )
        )
    except Exception as error:
        print(
            f"No se pudo ejecutar el scraping Qlik: {type(error).__name__}: {error}",
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
