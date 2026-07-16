import argparse
import json
import sys
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


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


def ejecutar_run(api_url: str, payload: dict[str, object]) -> dict[str, object]:
    request = Request(
        f"{api_url.rstrip('/')}/api/v1/qlik/runs",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=300) as response:
        return json.loads(response.read().decode("utf-8"))


def main() -> int:
    parser = argparse.ArgumentParser(description="Ejecuta una exportacion Qlik mediante la API")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--tenant")
    parser.add_argument("--space")
    parser.add_argument("--dataflow", help="Si se omite, exporta todos los dataflows")
    parser.add_argument("--headless", action="store_true")
    args = parser.parse_args()

    try:
        result = ejecutar_run(
            args.api_url,
            construir_payload(
                headless=args.headless,
                tenant=args.tenant,
                space=args.space,
                dataflow=args.dataflow,
            ),
        )
    except (HTTPError, URLError, TimeoutError) as error:
        print(f"No se pudo ejecutar la API Qlik: {error}", file=sys.stderr)
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
