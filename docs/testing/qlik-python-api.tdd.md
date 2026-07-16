# Evidencia TDD: Qlik Python API

## Objetivo

Migrar el scaffold inicial a Python, exponer la automatizacion Qlik mediante
FastAPI y preparar persistencia async para SQLite y PostgreSQL.

## Garantias verificadas

| Garantia | Prueba | Resultado |
|---|---|---|
| SQLite es el default de configuracion | `tests/unit/test_config.py::test_settings_use_sqlite_by_default` | PASS |
| PostgreSQL acepta la URL async y normaliza drivers | `tests/unit/test_config.py::test_settings_accept_postgres_url` | PASS |
| Faltan credenciales produce error accionable | `tests/unit/test_config.py::test_settings_require_qlik_credentials_for_automation` | PASS |
| Healthcheck devuelve envelope API | `tests/api/test_health.py::test_health_returns_api_status` | PASS |
| El endpoint de runs inicializa la base SQLite | `tests/api/test_health.py::test_runs_endpoint_initializes_sqlite_database` | PASS |
| Paginacion invalida devuelve HTTP 400 | `tests/api/test_health.py::test_runs_endpoint_validates_pagination` | PASS |
| Un run sin credenciales devuelve HTTP 422 sin abrir navegador | `tests/api/test_health.py::test_run_endpoint_rejects_missing_qlik_credentials` | PASS |
| Selecciona tenant/dataflow por nombre o primero | `tests/unit/test_automation_selection.py` | PASS |

## Comandos ejecutados

- `.venv/bin/python -m pytest -q`: 9 passed.
- `.venv/bin/python -m pytest --cov=app --cov-report=term-missing`: 9 passed, 87%.
- `.venv/bin/ruff check app tests`: PASS.
- `.venv/bin/python -m compileall -q app tests`: PASS.
- `.venv/bin/playwright install chromium`: PASS.

## Gaps conocidos

- El flujo contra Qlik no se ejecuta en tests locales porque requiere credenciales
  reales y autorización del tenant. Debe validarse con `.env` local y `POST
  /api/v1/qlik/runs`.
- Cuando `QLIK_DATAFLOW_NAME` queda vacío, el flujo descarga un JSON separado por
  cada dataflow; si se informa, descarga únicamente ese dataflow.
- `app/qlik/automation.py` se excluye de cobertura unitaria por ser un adapter
  externo; su cobertura corresponde a una E2E autorizada.
- FastAPI/Starlette muestra una advertencia de compatibilidad sobre `TestClient`
  y futuras versiones de httpx; no afecta los resultados actuales.
