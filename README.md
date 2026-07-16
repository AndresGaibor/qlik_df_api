# Qlik Data Flow API

API en Python para automatizar Qlik Cloud con Playwright y registrar las
ejecuciones en una base SQL. SQLite es el valor predeterminado local; la misma
configuracion acepta PostgreSQL mediante `DATABASE_URL`.

## Instalacion

```bash
python3 -m venv .venv
.venv/bin/pip install -e '.[test,dev]'
.venv/bin/playwright install chromium
cp .env.example .env
```

Edita `.env` y coloca tus credenciales Qlik. El password nunca se persiste en
la base ni se imprime en logs.

Deja `QLIK_STORAGE_STATE` vacío para iniciar siempre desde
`QLIK_TARGET_URL=https://qlikcloud.com/`. Si configuras una ruta, se reutilizará
la sesión guardada y Qlik puede entrar directamente al hub.

## Ejecutar la API

```bash
.venv/bin/uvicorn app.main:app --reload
```

Endpoints principales:

- `GET /health`
- `GET /api/v1/qlik/runs?limit=20&offset=0`
- `POST /api/v1/qlik/runs`

Ejemplo de ejecucion:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/qlik/runs \
  -H 'Content-Type: application/json' \
  -d '{"space":"Bancolombia prueba","headless":false}'
```

Sin `dataflow` se exporta un JSON independiente por cada flujo encontrado en el
espacio. Si se envia `dataflow`, solo se exporta ese flujo. Los archivos quedan
en `QLIK_DOWNLOAD_DIR` con el nombre del flujo. La respuesta devuelve las rutas
de los JSON guardados. MFA, SSO y CAPTCHA requieren intervencion manual; la
automatizacion no los evade.

## PostgreSQL

SQLite local:

```env
DATABASE_URL=sqlite+aiosqlite:///./data/qlik.db
```

PostgreSQL:

```env
DATABASE_URL=postgresql+asyncpg://usuario:password@localhost:5432/qlik
```

SQLAlchemy async selecciona el driver a partir de la URL. Las tablas se crean
al iniciar la aplicacion; para despliegues con cambios de esquema se puede
incorporar Alembic sin cambiar los repositorios ni los casos de uso.

## Pruebas

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
.venv/bin/ruff check app tests
```

Las pruebas E2E reales de Qlik deben ejecutarse solo con una cuenta autorizada
y un `.env` local que no se versiona.

## Servidor remoto de dataflows

En el servidor remoto configura `remote_server/.env`:

```env
REMOTE_API_KEY=una-clave-larga-y-aleatoria
REMOTE_CSV_PATH=data/dataflows.csv
```

Levántalo con:

```bash
.venv/bin/uvicorn remote_server.main:app --host 0.0.0.0 --port 8001
```

En el `.env` del Mac configura la URL y la misma clave:

```env
REMOTE_API_URL=https://tu-servidor.example.com:8001
REMOTE_API_KEY=una-clave-larga-y-aleatoria
```

Después de descargar y procesar todos los JSON, el Mac ejecuta un `PUT` único
que reemplaza completamente el CSV remoto. El servidor consulta los datos con:

```bash
curl -H "X-API-Key: una-clave-larga-y-aleatoria" \
  https://tu-servidor.example.com:8001/api/v1/dataflows
```

## Ejecutar desde Python

Con la API levantada, reemplaza `curl` por:

```bash
.venv/bin/python -m app.client
```

Esto exporta todos los dataflows. Para seleccionar uno:

```bash
.venv/bin/python -m app.client --dataflow "Prueba de conexion S3"
```

Opciones disponibles: `--api-url`, `--tenant`, `--space`, `--dataflow` y
`--headless`.
