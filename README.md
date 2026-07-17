# Qlik Data Flow API

Automatización en Python para iniciar sesión en Qlik Cloud con Playwright,
descargar el JSON de cada dataflow, extraer sus destinos y enviar un único
listado al servidor remoto.

El flujo recomendado es:

```text
Mac + Playwright/Qlik -> PUT autenticado -> API remota -> data/dataflows.csv
```

El Mac no necesita levantar una API local. Ejecuta directamente
`python -m app.client`. El servidor remoto solamente almacena y consulta los
datos procesados.

## Requisitos

- Mac para ejecutar el scraping.
- Servidor Linux (Debian/Ubuntu recomendado) con una IP o dominio accesible.
- Python 3.11 o superior en ambos equipos.
- Cuenta autorizada de Qlik Cloud.
- Acceso de red desde el Mac al puerto HTTPS de la API remota.
- Playwright Chromium. La primera ejecución puede requerir intervención manual
  para MFA, SSO o CAPTCHA.

## 1. Descargar el proyecto

En el Mac y, si el servidor remoto también usa este repositorio, en el servidor:

```bash
git clone https://github.com/AndresGaibor/qlik_df_api.git
cd qlik_df_api
```

Para actualizar una instalación existente:

```bash
git pull --ff-only origin main
```

## 2. Instalar dependencias en el Mac

Instala Python si no está disponible. Con Homebrew:

```bash
brew install python@3.11
```

Crea el entorno virtual e instala el proyecto con sus dependencias de pruebas y
desarrollo:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install -e '.[test,dev]'
.venv/bin/python -m playwright install chromium
```

Si `python3.11` no existe pero `python3` es 3.11 o superior, se puede usar:

```bash
python3 -m venv .venv
```

Comprueba la instalación:

```bash
.venv/bin/python --version
.venv/bin/python -m playwright --version
```

## 3. Configurar Qlik en el Mac

Copia la plantilla y edita el archivo. Nunca subas `.env` a Git:

```bash
cp .env.example .env
```

Configuración mínima:

```env
QLIK_EMAIL=usuario@ejemplo.com
QLIK_PASSWORD=tu-password-de-qlik
QLIK_TENANT=
QLIK_SPACE=Bancolombia prueba
QLIK_DATAFLOW_NAME=
QLIK_TARGET_URL=https://qlikcloud.com/
QLIK_DOWNLOAD_DIR=downloads
QLIK_HEADLESS=false
QLIK_STORAGE_STATE=
REMOTE_API_URL=https://tu-dominio.example.com
REMOTE_API_KEY=la-misma-clave-configurada-en-el-servidor
```

Detalles importantes:

- `QLIK_DATAFLOW_NAME=` vacío procesa todos los dataflows del espacio.
- `QLIK_DATAFLOW_NAME=Nombre exacto` procesa solo ese dataflow.
- `QLIK_HEADLESS=false` permite ver el navegador y completar MFA/SSO/CAPTCHA.
- `QLIK_HEADLESS=true` sirve para ejecuciones totalmente automatizadas cuando
  la sesión no necesita interacción.
- `QLIK_STORAGE_STATE` puede apuntar a un archivo de sesión de Playwright para
  reutilizar una sesión autorizada. Si queda vacío, el login comienza en
  `QLIK_TARGET_URL`.
- `REMOTE_API_URL` no debe terminar necesariamente en `/`; el cliente añade la
  ruta `/api/v1/dataflows`.
- `REMOTE_API_KEY` debe coincidir exactamente con la clave del servidor.

El password de Qlik no se guarda en el CSV ni se imprime intencionalmente en
los logs.

## 4. Preparar el servidor remoto

Los siguientes pasos son para Debian/Ubuntu. Conéctate por SSH y actualiza los
paquetes:

```bash
ssh usuario@tu-servidor
sudo apt update
sudo apt install -y git python3.11 python3.11-venv python3-pip
```

Si la distribución no ofrece `python3.11`, instala una versión soportada de
Python 3.11 o superior y adapta el comando del entorno virtual.

Descarga el proyecto e instala solo las dependencias de ejecución:

```bash
git clone https://github.com/AndresGaibor/qlik_df_api.git
cd qlik_df_api
python3.11 -m venv .venv
.venv/bin/python -m pip install --upgrade pip setuptools wheel
.venv/bin/python -m pip install .
```

No es necesario instalar Chromium en el servidor remoto porque el scraping se
ejecuta en el Mac. Tampoco es necesario configurar credenciales Qlik allí.

## 5. Configurar la API remota

Genera una clave larga y aleatoria. La clave se configura manualmente en ambos
equipos y nunca se versiona:

```bash
openssl rand -hex 32
```

Crea `remote_server/.env`:

```bash
cp remote_server/.env.example remote_server/.env
chmod 600 remote_server/.env
```

Edita el archivo:

```env
REMOTE_API_KEY=pega-aqui-la-clave-generada
REMOTE_CSV_PATH=data/dataflows.csv
```

El directorio padre del CSV se crea automáticamente cuando llega el primer
`PUT`. Cada `PUT` reemplaza todo el CSV; no agrega duplicados ni conserva datos
de ejecuciones anteriores.

## 6. Probar la API remota manualmente

Desde el servidor, inicia temporalmente la API para validar la configuración:

```bash
.venv/bin/uvicorn remote_server.main:app --host 0.0.0.0 --port 8001
```

En otra terminal verifica salud, sin autenticación:

```bash
curl http://127.0.0.1:8001/health
```

La respuesta esperada es:

```json
{"data":{"status":"ok"}}
```

Consulta los dataflows con la API key:

```bash
curl -i \
  -H 'X-API-Key: pega-aqui-la-clave-generada' \
  http://127.0.0.1:8001/api/v1/dataflows
```

Antes de exponer el servicio a Internet, colócalo detrás de HTTPS mediante un
reverse proxy como Nginx, Caddy o un túnel privado. No envíes la API key por una
conexión HTTP pública.

## 7. Mantener la API remota ejecutándose

Para una instalación simple con systemd, crea el servicio:

```bash
sudo nano /etc/systemd/system/qlik-dataflows.service
```

Contenido, ajustando `User` y `WorkingDirectory`:

```ini
[Unit]
Description=Qlik Dataflows Remote API
After=network.target

[Service]
Type=simple
User=usuario
WorkingDirectory=/home/usuario/qlik_df_api
ExecStart=/home/usuario/qlik_df_api/.venv/bin/uvicorn remote_server.main:app --host 127.0.0.1 --port 8001
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Activa y revisa el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now qlik-dataflows.service
sudo systemctl status qlik-dataflows.service
sudo journalctl -u qlik-dataflows.service -f
```

Usar `127.0.0.1` con un reverse proxy es preferible a publicar directamente
Uvicorn en `0.0.0.0`. Si se usa un firewall, permite únicamente SSH y HTTPS:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 443/tcp
sudo ufw enable
```

## 8. Ejecutar el scraping desde el Mac

Desde la raíz del proyecto:

```bash
.venv/bin/python -m app.client
```

El proceso:

1. Abre Qlik Cloud con Playwright.
2. Completa el login y permite intervención manual si `QLIK_HEADLESS=false`.
3. Selecciona el tenant y el espacio configurados.
4. Descarga un JSON por cada dataflow seleccionado.
5. Extrae los targets y sus metadatos.
6. Envía un único `PUT` al servidor remoto.
7. Imprime el resultado JSON en la terminal.

Para seleccionar opciones sin modificar `.env`:

```bash
.venv/bin/python -m app.client --tenant "mi-tenant"
.venv/bin/python -m app.client --space "Bancolombia prueba"
.venv/bin/python -m app.client --dataflow "Prueba de conexion S3"
.venv/bin/python -m app.client --headless
```

Se pueden combinar:

```bash
.venv/bin/python -m app.client \
  --tenant "mi-tenant" \
  --space "Bancolombia prueba" \
  --dataflow "Prueba de conexion S3"
```

No ejecutes `app.main` para este flujo. `app.main` conserva la API local y sus
endpoints históricos, pero el cliente directo es el punto de entrada operativo
para enviar datos al servidor remoto.

## 9. Consultar los datos almacenados

La consulta requiere la misma API key:

```bash
curl \
  -H "X-API-Key: $REMOTE_API_KEY" \
  https://tu-dominio.example.com/api/v1/dataflows
```

Filtros disponibles:

```bash
curl -H "X-API-Key: $REMOTE_API_KEY" \
  'https://tu-dominio.example.com/api/v1/dataflows?dataflow_name=Mi%20Dataflow'

curl -H "X-API-Key: $REMOTE_API_KEY" \
  'https://tu-dominio.example.com/api/v1/dataflows?dataflow_id=abc123'
```

El CSV también puede revisarse directamente en el servidor:

```bash
column -s, -t < data/dataflows.csv | less -S
```

## 10. Actualizar la instalación

En el servidor, detén o deja que systemd reinicie durante la actualización:

```bash
cd /home/usuario/qlik_df_api
git pull --ff-only origin main
.venv/bin/python -m pip install .
sudo systemctl restart qlik-dataflows.service
```

En el Mac:

```bash
cd /ruta/al/qlik_df_api
.venv/bin/python -m pip install -e '.[test,dev]'
```

Los archivos `.env`, `remote_server/.env`, el CSV, las descargas y el entorno
virtual no deben reemplazarse durante un `git pull` porque están fuera del
control de versiones.

## 11. Pruebas y calidad

Ejecuta desde la raíz del repositorio:

```bash
.venv/bin/python -m pytest -q
.venv/bin/python -m pytest --cov=app --cov-report=term-missing
.venv/bin/ruff check app remote_server tests
```

Las pruebas E2E reales de Qlik requieren una cuenta autorizada y no deben
ejecutarse en CI con credenciales reales. MFA, SSO y CAPTCHA no se evaden.

## Solución de problemas

### `ModuleNotFoundError: No module named ...`

Ejecuta siempre el comando usando `.venv/bin/python`, desde la raíz del
proyecto. Si el entorno no existe, repite la instalación de la sección 2 o 4.

### `python3.11-venv` no está instalado

En Debian/Ubuntu instala:

```bash
sudo apt update
sudo apt install -y python3.11-venv
```

Después elimina y recrea el entorno virtual si la creación anterior quedó
incompleta.

### `401 API key invalida`

Comprueba que `REMOTE_API_KEY` en el Mac sea idéntica a
`remote_server/.env` en el servidor, sin espacios ni comillas adicionales.
Reinicia systemd después de modificar el archivo remoto.

### `Connection refused` o timeout al enviar

Verifica el servicio y la red:

```bash
sudo systemctl status qlik-dataflows.service
curl https://tu-dominio.example.com/health
```

Comprueba DNS, HTTPS, reverse proxy, firewall y que
`REMOTE_API_URL` apunte al dominio correcto.

### Qlik abre pero el login no termina

Usa `QLIK_HEADLESS=false`, ejecuta el cliente desde una terminal visible y
completa MFA, SSO o CAPTCHA manualmente. Revisa también tenant, espacio y URL.

### El CSV contiene datos de una ejecución anterior

El comportamiento esperado es que cada ejecución exitosa reemplace el CSV
completo. Si el `PUT` falla, el repositorio mantiene el archivo anterior para no
dejarlo parcialmente escrito.

## Estructura relevante

```text
app/client.py                 Punto de entrada directo del Mac
app/qlik/automation.py        Login, navegación, descargas y envío remoto
app/qlik/processor.py         Extracción de dataflows y targets
app/remote/client.py          Cliente HTTP del servidor remoto
app/remote/csv_repository.py  Reemplazo y lectura atómica del CSV
remote_server/main.py         API remota protegida por X-API-Key
remote_server/config.py       Configuración del servidor remoto
tests/                        Pruebas unitarias y de API
```
