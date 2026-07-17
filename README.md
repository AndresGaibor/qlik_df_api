# Qlik Data Flow API

Automatización en Python para iniciar sesión en Qlik Cloud con Playwright,
listar dataflows via API REST, descargar el JSON de cada uno, extraer sus
destinos y enviar un único listado al servidor remoto.

El flujo recomendado es:

```text
Mac + Playwright/Qlik -> PUT autenticado -> API remota -> data/dataflows.csv
```

La guía detallada del despliegue HTTPS, Cloudflare, Apache/Plesk, Qlik Automate,
systemd y troubleshooting está en
[`docs/cloudflare-qlik-deployment.md`](docs/cloudflare-qlik-deployment.md).

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
REMOTE_API_URL=https://apiqd.andresgaibor.com
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
https://apiqd.andresgaibor.com/api/v1/impala/databases/default/tables/ventas/columns

Método:
GET

Header:
X-API-Key: TU_API_KEY
```

En la configuración de la conexión REST:

1. Selecciona el método `GET`.
2. Agrega el header `X-API-Key` con la misma clave configurada en `remote_server/.env`.
3. En **Certificate validation**, usa la validación normal del certificado público de Cloudflare.
4. Ejecuta **Test connection**.

La URL base pública del servidor es:

```text
https://apiqd.andresgaibor.com
```

Con Cloudflare activo, no selecciones **Skip server certificate validation**:
Qlik Cloud debe validar el certificado público de Cloudflare normalmente.

La opción **Skip server certificate validation** solo corresponde a la prueba
antigua usando directamente el certificado autofirmado y la IP. Debe usarse
únicamente en entornos de prueba.

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
https://apiqd.andresgaibor.com/api/v1/impala/databases/default/tables/ventas/columns

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
`apiqd.andresgaibor.com` detrás del proxy de Cloudflare. Qlik Automate verá el
certificado público de Cloudflare y no tendrá que confiar en el certificado
autofirmado del servidor.

#### Configuración en Cloudflare

En **DNS > Records** del dominio `andresgaibor.com`, crea:

```text
Type: A
Name: apiqd
IPv4 address: 209.50.245.140
Proxy status: Proxied (nube naranja)
```

En **SSL/TLS > Overview**, selecciona **Full (strict)**.

En **SSL/TLS > Origin Server > Create Certificate**, crea un certificado de
origen para:

```text
apiqd.andresgaibor.com
```

Guarda el certificado público como `/etc/nginx/ssl/cloudflare-origin.pem` y la
clave privada como `/etc/nginx/ssl/cloudflare-origin.key`. La clave privada no
debe versionarse ni compartirse.

#### Configuración en el servidor sin Plesk/Apache

Usa esta subsección solo si Nginx es quien ocupa directamente los puertos 80 y
443. Si `ss -ltnp` muestra `apache2` en esos puertos, usa la sección 6.5 y no
arranques un Nginx independiente.

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
    server_name apiqd.andresgaibor.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name apiqd.andresgaibor.com;

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
curl https://apiqd.andresgaibor.com/health
curl -H 'X-API-Key: TU_API_KEY' \
  https://apiqd.andresgaibor.com/api/v1/impala/databases/default/tables/ventas/columns
```

En Qlik Automate, el bloque **Call URL** debe usar:

```text
https://apiqd.andresgaibor.com/api/v1/impala/databases/default/tables/ventas/columns
```

El certificado de Cloudflare será validado normalmente, sin seleccionar ninguna
opción para ignorar SSL.

### 6.5 Servidor con Plesk y Apache en 80/443

Si `ss -ltnp` muestra `apache2` ocupando los puertos `80` y `443`, no se debe
arrancar un Nginx independiente en esos puertos. En ese caso, Apache/Plesk debe
terminar TLS y hacer proxy hacia Uvicorn.

Activa los módulos necesarios:

```bash
sudo a2enmod ssl proxy proxy_http headers
```

Crea `/etc/apache2/sites-available/apiqd.conf`:

```apache
<VirtualHost 209.50.245.140:80 *:80>
    ServerName apiqd.andresgaibor.com
    Redirect permanent / https://apiqd.andresgaibor.com/
</VirtualHost>

<VirtualHost 209.50.245.140:443 *:443>
    ServerName apiqd.andresgaibor.com

    SSLEngine on
    SSLCertificateFile /etc/nginx/ssl/cloudflare-origin.pem
    SSLCertificateKeyFile /etc/nginx/ssl/cloudflare-origin.key

    ProxyPreserveHost On
    ProxyPass / http://127.0.0.1:8001/
    ProxyPassReverse / http://127.0.0.1:8001/
    RequestHeader set X-Forwarded-Proto "https"
    ProxyTimeout 120
</VirtualHost>
```

Activa el sitio y recarga Apache:

```bash
sudo a2ensite apiqd.conf
sudo apachectl configtest
sudo systemctl reload apache2
```

Para probar el vhost localmente, el certificado de Cloudflare no será confiable
para `curl`, por eso se usa `-k` solo en esta prueba directa al origen:

```bash
curl -k --resolve apiqd.andresgaibor.com:443:209.50.245.140 \
  https://apiqd.andresgaibor.com/health
```

La prueba pública debe hacerse sin `-k` y pasar por Cloudflare:

```bash
curl https://apiqd.andresgaibor.com/health
```

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

#### Alternativa legacy: IP directa con certificado autofirmado

Si no usas Cloudflare/Apache y elegiste la opción rápida sin reverse proxy,
permite también el puerto de Uvicorn:

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

#### Instalación actual en `/root/qlik_df_api` con Apache/Cloudflare

Si el proyecto está instalado como `root`, primero detén cualquier Uvicorn
manual que esté en primer plano con `Ctrl+C`. Luego crea el servicio:

```bash
sudo nano /etc/systemd/system/qlik-dataflows.service
```

Usa este contenido:

```ini
[Unit]
Description=Qlik Dataflows Remote API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/qlik_df_api
ExecStart=/root/qlik_df_api/.venv/bin/uvicorn remote_server.main:app --host 127.0.0.1 --port 8001
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
curl http://127.0.0.1:8001/health
```

Ejecutar la API como `root` es una solución rápida. Para una instalación
permanente, crea un usuario dedicado y cambia `User`, `WorkingDirectory` y las
rutas del servicio para no ejecutar Uvicorn con privilegios de administrador.

### Actualizar el código y reiniciar el servicio

Después de actualizar el código Python, no es necesario reiniciar Apache. Si
también cambiaron las dependencias, instálalas primero:

```bash
cd /root/qlik_df_api
.venv/bin/python -m pip install .
```

Reinicia Uvicorn y verifica su estado:

```bash
sudo systemctl restart qlik-dataflows.service
sudo systemctl status qlik-dataflows.service
curl http://127.0.0.1:8001/health
```

Para revisar errores en tiempo real:

```bash
sudo journalctl -u qlik-dataflows.service -f
```

## 8. Ejecutar el scraping desde el Mac

Desde la raíz del proyecto:

```bash
.venv/bin/python -m app.client
```

El proceso tiene dos fases:

**Fase 1 — API REST (listado rápido):**
1. Abre Qlik Cloud con Playwright y completa el login.
2. Extrae las cookies de la sesión autenticada.
3. Llama a la API de Qlik Cloud para listar los dataflows del espacio.
4. Envía el listado básico (id, nombre, descripción) al servidor remoto.

**Fase 2 — Scraping (JSON completo):**
4. Navega a la vista de Prepare Data y filtra por espacio.
5. Para cada dataflow: abre su overview, exporta el JSON via menú contextual.
6. Procesa los targets (filename, extension, format, etc.).
7. Envía el listado enriquecido al servidor remoto (reemplaza el anterior).
8. Imprime el resultado JSON en la terminal.

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
  https://apiqd.andresgaibor.com/api/v1/dataflows
```

Filtros disponibles:

```bash
curl -H "X-API-Key: $REMOTE_API_KEY" \
  'https://apiqd.andresgaibor.com/api/v1/dataflows?dataflow_name=Mi%20Dataflow'

curl -H "X-API-Key: $REMOTE_API_KEY" \
  'https://apiqd.andresgaibor.com/api/v1/dataflows?dataflow_id=abc123'
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

### `unknown directive "brotli"` al ejecutar `nginx -t`

El servidor tiene un archivo `/etc/nginx/conf.d/brotli.conf` que usa la
directiva `brotli`, pero el módulo Brotli de Nginx no está instalado. Brotli no
es necesario para esta API. Desactiva el archivo sin eliminarlo:

```bash
sudo mv /etc/nginx/conf.d/brotli.conf \
  /etc/nginx/conf.d/brotli.conf.disabled
sudo nginx -t
sudo systemctl reload nginx
```

### `ssl_prefer_server_ciphers directive is duplicate` al ejecutar `nginx -t`

El servidor tiene una configuración SSL duplicada en
`/etc/nginx/conf.d/ssl.conf`. Si las directivas SSL ya están definidas por otra
configuración de Nginx, desactiva este archivo conservando una copia:

```bash
sudo mv /etc/nginx/conf.d/ssl.conf \
  /etc/nginx/conf.d/ssl.conf.disabled
sudo nginx -t
sudo systemctl reload nginx
```

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
app/qlik/api_client.py        Cliente REST para Qlik Cloud API (listar dataflows)
app/qlik/automation.py        Login, listado API, scraping, descargas y envío
app/qlik/processor.py         Extracción de targets desde JSON descargado
app/remote/client.py          Cliente HTTP del servidor remoto
app/remote/csv_repository.py  Reemplazo y lectura atómica del CSV
remote_server/main.py         API remota protegida por X-API-Key
remote_server/config.py       Configuración del servidor remoto
docs/qlik-cloud-api.md        Documentación de endpoints Qlik Cloud
tests/                        Pruebas unitarias y de API
```
