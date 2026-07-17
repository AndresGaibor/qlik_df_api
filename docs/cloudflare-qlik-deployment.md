# Despliegue HTTPS con Cloudflare y Qlik

Guía operativa de la configuración final y de los problemas encontrados al
publicar la API remota para Qlik Automate.

## Arquitectura final

```text
Qlik Automate
    |
    | HTTPS https://apiqd.andresgaibor.com
    v
Cloudflare proxy (nube naranja, Full strict)
    |
    | HTTPS al origen, puerto 443
    v
Apache/Plesk en 209.50.245.140:443
    |
    | HTTP local
    v
Uvicorn en 127.0.0.1:8001
```

Apache es el frontend real del servidor porque Plesk ya ocupa los puertos 80 y
443. No se debe iniciar un Nginx independiente en esos puertos.

## 1. Configuración en Cloudflare

En `andresgaibor.com`, crear el registro:

```text
Type: A
Name: apiqd
IPv4 address: 209.50.245.140
Proxy status: Proxied (nube naranja)
```

En **SSL/TLS > Overview**, seleccionar:

```text
Full (strict)
```

En **SSL/TLS > Origin Server > Create Certificate**:

```text
Private key type: RSA (2048)
Hostname: apiqd.andresgaibor.com
Validity: 15 years
```

Guardar los dos bloques generados por Cloudflare:

- `Origin Certificate` en `/etc/nginx/ssl/cloudflare-origin.pem`.
- `Private Key` en `/etc/nginx/ssl/cloudflare-origin.key`.

La clave privada nunca debe compartirse ni versionarse.

Validar el par en el servidor:

```bash
sudo openssl pkey \
  -in /etc/nginx/ssl/cloudflare-origin.key \
  -check \
  -noout

sudo openssl x509 \
  -in /etc/nginx/ssl/cloudflare-origin.pem \
  -noout \
  -subject \
  -dates \
  -ext subjectAltName
```

El certificado debe mostrar:

```text
DNS:apiqd.andresgaibor.com
```

## 2. Servicio Uvicorn en segundo plano

Crear `/etc/systemd/system/qlik-dataflows.service`:

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

Activar y revisar:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now qlik-dataflows.service
sudo systemctl status qlik-dataflows.service
curl http://127.0.0.1:8001/health
```

Uvicorn no debe usar `--ssl-keyfile` ni `--ssl-certfile` en esta arquitectura.
Apache termina TLS y Uvicorn solo escucha localmente.

## 3. Apache como proxy

Activar módulos:

```bash
sudo a2enmod ssl proxy proxy_http headers
```

Crear `/etc/apache2/sites-available/apiqd.conf`:

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

Activar y recargar:

```bash
sudo a2ensite apiqd.conf
sudo apachectl configtest
sudo systemctl reload apache2
```

La prueba directa al origen usa la IP pública porque Plesk define vhosts
específicos para esa IP:

```bash
curl -k --resolve apiqd.andresgaibor.com:443:209.50.245.140 \
  https://apiqd.andresgaibor.com/health
```

La prueba pública pasa por Cloudflare y no requiere `-k`:

```bash
curl https://apiqd.andresgaibor.com/health
```

## 4. Configuración en Qlik Automate

En el bloque **Call URL**:

```text
URL:
https://apiqd.andresgaibor.com/api/v1/impala/databases/default/tables/ventas/columns

Method:
GET

Header:
X-API-Key: TU_API_KEY
```

No incluir la API key en la URL. No seleccionar `Skip server certificate
validation`: el certificado público que ve Qlik Automate es el de Cloudflare.

La documentación de Qlik indica que `Call URL` requiere una cadena completa de
certificados cuando verifica SSL y no documenta una opción para desactivar esa
validación.

Referencia:
<https://help.qlik.com/en-US/cloud-services/Subsystems/Hub/Content/Sense_QlikAutomation/basic/call-url-block.htm>

## 5. Conexión REST de Qlik Cloud

Una conexión REST de Qlik Cloud es distinta de `Call URL`. Para la configuración
actual debe usar:

```text
https://apiqd.andresgaibor.com/api/v1/impala/databases/default/tables/ventas/columns
```

Método `GET`, header `X-API-Key` y validación normal del certificado público.

`Skip server certificate validation` solo corresponde a la prueba antigua con
el certificado autofirmado directo en `https://209.50.245.140:8001`. No es la
configuración recomendada cuando Cloudflare está activo.

## 6. Actualizar código y reiniciar

Después de actualizar la API:

```bash
cd /root/qlik_df_api
.venv/bin/python -m pip install .
sudo systemctl restart qlik-dataflows.service
sudo systemctl status qlik-dataflows.service
curl http://127.0.0.1:8001/health
```

Los cambios de Python no requieren reiniciar Apache. Revisar logs con:

```bash
sudo journalctl -u qlik-dataflows.service -f
```

## 7. Firewall y SSH

Con Cloudflare y Apache, dejar públicos únicamente SSH, HTTP y HTTPS:

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw delete allow 8001/tcp
sudo ufw reload
```

El puerto 8001 debe quedar accesible solo desde localhost.

Permisos SSH recomendados:

```bash
chmod 700 /home/andresadmin/.ssh
chmod 600 /home/andresadmin/.ssh/authorized_keys
```

La salida `passwordauthentication yes` significa que SSH todavía permite
contraseñas. No desactivar `PasswordAuthentication` hasta comprobar el acceso
por llave en una segunda sesión SSH.

## 8. Problemas encontrados y soluciones

### Certificado autofirmado: `curl: (60)`

El certificado autofirmado cifra la conexión, pero no es confiable para curl,
clientes Python ni Qlik Automate. `curl -k` solo sirve para pruebas. La solución
final fue usar Cloudflare con un subdominio y certificado de origen.

### Clave PEM incompleta

Si `openssl pkey` muestra `No supported data to decode`, la clave no contiene el
bloque completo. Debe comenzar con `BEGIN PRIVATE KEY` y terminar con
`END PRIVATE KEY`.

### `key values mismatch`

La clave y el certificado provienen de generaciones distintas de Cloudflare.
Regenerar ambos y reemplazar los dos archivos juntos.

### `unknown directive "brotli"`

Nginx cargaba Brotli sin tener el módulo instalado. Como Nginx no es el frontend
final de este servidor, se desactivó conservando una copia:

```bash
sudo mv /etc/nginx/conf.d/brotli.conf \
  /etc/nginx/conf.d/brotli.conf.disabled
```

### `ssl_prefer_server_ciphers directive is duplicate`

Había directivas SSL duplicadas en Nginx. Se conservó el archivo y se desactivó:

```bash
sudo mv /etc/nginx/conf.d/ssl.conf \
  /etc/nginx/conf.d/ssl.conf.disabled
```

### `Address already in use` en Nginx

Apache/Plesk ya ocupaba los puertos 80 y 443. No se debe detener Apache sin
revisar otros sitios. La solución fue usar Apache como proxy.

### `wrong version number`

Apache estaba seleccionando un vhost Plesk HTTP para la IP específica. El vhost
de la API se configuró con `209.50.245.140:443` además de `*:443`, y la prueba
local se cambió para usar la IP pública con `--resolve`.

### `Unit qlik-dataflows.service not found`

El servicio systemd no existía. Se creó en `/etc/systemd/system`, se habilitó
con `systemctl enable --now` y quedó configurado para reiniciarse después de un
reinicio del servidor.

### SSH y Fail2Ban

La configuración de `authorized_keys` y `ignoreip` de Fail2Ban es independiente
del proxy HTTPS. No modificar la autenticación SSH mientras no se haya probado
el acceso por llave en otra sesión.
