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
QLIK_SPACE=mi-espacio
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

### 6.1 HTTPS rápido sin dominio

Si no tienes dominio y necesitas acceder temporalmente mediante la IP pública,
puedes usar un certificado autofirmado. El navegador mostrará una advertencia de
seguridad porque ningún proveedor público ha validado ese certificado. Para uso
permanente o público, un dominio con un certificado de Let's Encrypt sigue siendo
la opción recomendada.

En el servidor, detén el Uvicorn HTTP que esté ejecutándose con `Ctrl+C` y crea
el certificado. Sustituye la IP por la IP pública real del servidor:

```bash
cd ~/qlik_df_api
IP_SERVIDOR="IP_PUBLICA_DEL_SERVIDOR"

mkdir -p certs
openssl req -x509 -newkey rsa:4096 -nodes \
  -keyout certs/server.key \
  -out certs/server.crt \
  -days 365 \
  -subj "/CN=${IP_SERVIDOR}" \
  -addext "subjectAltName=IP:${IP_SERVIDOR}"

chmod 600 certs/server.key
chmod 644 certs/server.crt
```

Permite el puerto HTTPS de Uvicorn en el firewall:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 8001/tcp
sudo ufw enable
```

Inicia la API con TLS:

```bash
.venv/bin/uvicorn remote_server.main:app \
  --host 0.0.0.0 \
  --port 8001 \
  --ssl-keyfile certs/server.key \
  --ssl-certfile certs/server.crt
```

La API estará disponible en:

```text
https://IP_PUBLICA_DEL_SERVIDOR:8001
```

Prueba desde otra terminal. La opción `-k` acepta el certificado autofirmado:

```bash
curl -k https://IP_PUBLICA_DEL_SERVIDOR:8001/health

curl -k \
  -H 'X-API-Key: pega-aqui-la-clave-generada' \
  https://IP_PUBLICA_DEL_SERVIDOR:8001/api/v1/dataflows
```

Para que el cliente del Mac valide el certificado sin desactivar TLS, copia el
certificado público al Mac:

```bash
scp usuario@IP_PUBLICA_DEL_SERVIDOR:~/qlik_df_api/certs/server.crt .
```

Configura la URL remota en el `.env` del Mac:

```env
REMOTE_API_URL=https://IP_PUBLICA_DEL_SERVIDOR:8001
```

Ejecuta el cliente indicando el certificado confiable:

```bash
SSL_CERT_FILE=server.crt .venv/bin/python -m app.client
```

`curl -k` y desactivar la verificación TLS en el código solo deben usarse para
pruebas. No publiques `certs/server.key` ni lo subas a Git.

### 6.2 Conectar desde Qlik Cloud

El certificado no tiene que instalarse en el Mac para que Qlik Cloud consuma la
API. Al crear una conexión **REST** en Qlik Cloud, configura exactamente lo
siguiente:

```text
URL:
https://209.50.245.140:8001/api/v1/impala/databases/default/tables/ventas/columns

Método:
GET

Header:
X-API-Key: TU_API_KEY
```

En la configuración de la conexión REST:

1. Selecciona el método `GET`.
2. Agrega el header `X-API-Key` con la misma clave configurada en `remote_server/.env`.
3. En **Certificate validation**, selecciona **Skip server certificate validation**.
4. Ejecuta **Test connection**.

La URL base del servidor es:

```text
https://209.50.245.140:8001
```

La opción **Skip server certificate validation** permite que Qlik Cloud use el
certificado autofirmado. Es la alternativa más rápida, pero debe usarse solo
para pruebas porque Qlik Cloud no valida que el servidor sea realmente el
servidor esperado.

Como alternativa, descarga únicamente `certs/server.crt` y súbelo en **Custom
Root CA Certificate** dentro de la conexión REST. Nunca subas `server.key`.
Después selecciona la validación mediante el certificado personalizado y prueba
la conexión nuevamente.

### 6.3 Qlik Automate: bloque Call URL

El bloque **Call URL** de Qlik Automate es diferente de una conexión REST. La
documentación oficial indica que, cuando la verificación SSL está activa, el
servidor externo debe entregar la cadena completa de certificados. El bloque
`Call URL` no documenta una opción para omitir la validación TLS ni para cargar
una CA personalizada.

Referencia oficial:
<https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_QlikAutomation/basic/call-url-block.htm>

Configura el bloque con estos valores:

```text
URL:
https://209.50.245.140:8001/api/v1/impala/databases/default/tables/ventas/columns

Method:
GET

Header:
X-API-Key: TU_API_KEY
```

En **Call URL** no existe un campo equivalente a **Skip server certificate
validation**. Por lo tanto, el certificado autofirmado usado en la sección
anterior puede funcionar con una conexión REST configurada para omitir la
validación, pero no debe asumirse que funcionará desde `Call URL`.

Para usar `Call URL` de forma compatible, el servidor debe presentar un
certificado firmado por una autoridad pública confiable y entregar la cadena
completa. La opción práctica es usar un dominio y un certificado de Let's
Encrypt. Sin dominio, se necesita un certificado público emitido para la IP o
un mecanismo equivalente; el certificado autofirmado no es suficiente cuando
`Call URL` valida SSL.

### 6.4 Subdominio en Cloudflare para Qlik Automate

La configuración recomendada es publicar la API como
`api.andresgaibor.com` detrás del proxy de Cloudflare. Qlik Automate verá el
certificado público de Cloudflare y no tendrá que confiar en el certificado
autofirmado del servidor.

#### Configuración en Cloudflare

En **DNS > Records** del dominio `andresgaibor.com`, crea:

```text
Type: A
Name: api
IPv4 address: 209.50.245.140
Proxy status: Proxied (nube naranja)
```

En **SSL/TLS > Overview**, selecciona **Full (strict)**.

En **SSL/TLS > Origin Server > Create Certificate**, crea un certificado de
origen para:

```text
api.andresgaibor.com
```

Guarda el certificado público como `/etc/nginx/ssl/cloudflare-origin.pem` y la
clave privada como `/etc/nginx/ssl/cloudflare-origin.key`. La clave privada no
debe versionarse ni compartirse.

#### Configuración en el servidor

Instala Nginx:

```bash
sudo apt update
sudo apt install -y nginx
sudo mkdir -p /etc/nginx/ssl
sudo chmod 700 /etc/nginx/ssl
```

Crea el archivo `/etc/nginx/sites-available/qlik-api`:

```nginx
server {
    listen 80;
    server_name api.andresgaibor.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name api.andresgaibor.com;

    ssl_certificate /etc/nginx/ssl/cloudflare-origin.pem;
    ssl_certificate_key /etc/nginx/ssl/cloudflare-origin.key;

    location / {
        proxy_pass http://127.0.0.1:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Activa la configuración:

```bash
sudo ln -s /etc/nginx/sites-available/qlik-api /etc/nginx/sites-enabled/qlik-api
sudo nginx -t
sudo systemctl reload nginx
```

En `systemd`, Uvicorn debe quedar en HTTP local porque Nginx será quien
termine HTTPS. Cambia `ExecStart` por:

```ini
ExecStart=/root/qlik_df_api/.venv/bin/uvicorn remote_server.main:app --host 127.0.0.1 --port 8001
```

Aplica el cambio:

```bash
sudo systemctl daemon-reload
sudo systemctl restart qlik-dataflows.service
sudo systemctl restart nginx
```

Abre únicamente los puertos necesarios:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw delete allow 8001/tcp
sudo ufw enable
```

El estado DNS debe permanecer como **Proxied**. Si se cambia a **DNS only**,
Qlik Automate verá directamente el certificado de origen de Cloudflare y la
validación puede fallar.

Verifica desde fuera del servidor:

```bash
curl https://api.andresgaibor.com/health
curl -H 'X-API-Key: TU_API_KEY' \
  https://api.andresgaibor.com/api/v1/impala/databases/default/tables/ventas/columns
```

En Qlik Automate, el bloque **Call URL** debe usar:

```text
https://api.andresgaibor.com/api/v1/impala/databases/default/tables/ventas/columns
```

El certificado de Cloudflare será validado normalmente, sin seleccionar ninguna
opción para ignorar SSL.

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

Si elegiste la opción rápida sin reverse proxy, permite también el puerto de
Uvicorn:

```bash
sudo ufw allow 8001/tcp
```

Para ejecutar la opción rápida automáticamente con `systemd`, reemplaza la
línea `ExecStart` anterior por esta, ajustando `usuario` y la ruta si es
necesario:

```ini
ExecStart=/home/usuario/qlik_df_api/.venv/bin/uvicorn remote_server.main:app --host 0.0.0.0 --port 8001 --ssl-keyfile=/home/usuario/qlik_df_api/certs/server.key --ssl-certfile=/home/usuario/qlik_df_api/certs/server.crt
```

Después aplica el cambio:

```bash
sudo systemctl daemon-reload
sudo systemctl restart qlik-dataflows.service
sudo systemctl status qlik-dataflows.service
```

#### Instalación rápida actual en `/root/qlik_df_api`

Si el proyecto está instalado como `root`, primero detén el Uvicorn que está en
primer plano con `Ctrl+C`. Luego crea el servicio:

```bash
sudo nano /etc/systemd/system/qlik-dataflows.service
```

Usa este contenido:

```ini
[Unit]
Description=Qlik Dataflows Remote API HTTPS
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/qlik_df_api
ExecStart=/root/qlik_df_api/.venv/bin/uvicorn remote_server.main:app --host 0.0.0.0 --port 8001 --ssl-keyfile=/root/qlik_df_api/certs/server.key --ssl-certfile=/root/qlik_df_api/certs/server.crt
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
```

Guarda el archivo y activa el servicio:

```bash
sudo systemctl daemon-reload
sudo systemctl enable qlik-dataflows.service
sudo systemctl start qlik-dataflows.service
sudo systemctl status qlik-dataflows.service
```

El servicio seguirá ejecutándose aunque cierres la sesión SSH y volverá a
iniciarse automáticamente después de reiniciar el servidor. Para revisar los
logs en tiempo real:

```bash
sudo journalctl -u qlik-dataflows.service -f
```

Comprueba que responde:

```bash
curl -k https://209.50.245.140:8001/health
```

Ejecutar la API como `root` es una solución rápida. Para una instalación
permanente, crea un usuario dedicado y cambia `User`, `WorkingDirectory` y las
rutas del servicio para no ejecutar Uvicorn con privilegios de administrador.

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
.venv/bin/python -m app.client --space "mi-espacio"
.venv/bin/python -m app.client --dataflow "Prueba de conexion S3"
.venv/bin/python -m app.client --headless
```

Se pueden combinar:

```bash
.venv/bin/python -m app.client \
  --tenant "mi-tenant" \
  --space "mi-espacio" \
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
