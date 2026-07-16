# Automatizacion de Qlik Cloud con Playwright

## Objetivo

Crear una automatizacion local y parametrizable que lea las credenciales desde
`.env`, inicie sesion en Qlik Cloud, liste los tenants disponibles, seleccione
un tenant, navegue a Preparar datos, seleccione un espacio, liste los flujos de
datos, abra uno configurable y descargue su archivo JSON.

## Alcance

- Proyecto TypeScript ejecutable con Playwright Test.
- Credenciales exclusivamente desde variables de entorno locales.
- Seleccion de tenant y flujo por nombre, con fallback al primer elemento.
- Seleccion de espacio por nombre configurable.
- Descargas guardadas en una carpeta configurable y validada.
- Reutilizacion opcional de `storageState` para evitar login repetido.
- Manejo explicito de MFA/SSO: no se intenta evadirlo.
- Selectores semanticamente fuertes: `getByRole`, `getByLabel`, `getByText` y
  `getByTestId`; no se usaran clases CSS generadas como contrato.

Fuera de alcance:

- Recuperar credenciales desde correo.
- Automatizar CAPTCHA, MFA o SSO.
- Usar APIs privadas de Qlik en lugar del flujo web.
- Ejecutar contra tenants sin autorizacion del usuario.

## Arquitectura

La automatizacion se separara en Page Objects pequenos:

- `LoginPage`: carga Qlik Cloud y envia email/password.
- `TenantPage`: espera la pantalla de seleccion, extrae tenants y selecciona
  por nombre o indice.
- `HubPage`: navega a Preparar datos, abre el selector de espacios y extrae
  flujos de datos visibles.
- `DataflowPage`: abre el flujo y ejecuta la descarga JSON desde el menu de
  acciones.
- `QlikClient`: coordina el flujo y retorna un resultado serializable con
  tenants, espacio, flujos y ruta del archivo descargado.

La configuracion se validara al inicio. Las credenciales nunca se incluiran en
logs, screenshots intencionales ni resultados. Los artefactos de sesion y las
descargas quedaran excluidos de Git.

## Configuracion

`.env.example` documentara:

- `QLIK_EMAIL`
- `QLIK_PASSWORD`
- `QLIK_TENANT` opcional; si falta, se selecciona el primero
- `QLIK_SPACE` requerido para evitar seleccionar un espacio equivocado
- `QLIK_DATAFLOW_NAME` opcional; si falta, se selecciona el primero
- `QLIK_TARGET_URL` opcional para soportar una URL inicial distinta
- `QLIK_DOWNLOAD_DIR` opcional
- `QLIK_HEADLESS` opcional

`.env` se ignorara mediante `.gitignore` y se proporcionara una validacion que
falle rapido cuando falten email o password.

## Selectores y flujo

1. Login: `getByLabel('Email')`, `getByLabel('Password')` y el boton accesible
   de login. Se aceptaran variaciones de idioma mediante regex.
2. Tenant: localizar las tarjetas por el boton accesible dentro de la pantalla
   `Choose tenant`; extraer nombre y hostname de cada tarjeta sin depender de
   clases generadas.
3. Preparar datos: usar el enlace con `data-testid`
   `nav-menu.analytics_creation.prepare_data_home`.
4. Espacio: abrir `getByTestId('browser-space-filter-btn')`, localizar el
   elemento `getByTestId('space-menu-item-<nombre>')` o su rol `link` y
   verificar que el espacio seleccionado se refleja en el filtro.
5. Flujos: extraer cada `getByTestId('appsItem')`, su `data-testmeta`, tipo y
   enlace `getByTestId('app-card-container-link')` dentro de la tarjeta.
6. Detalle: abrir el enlace del flujo seleccionado y esperar la URL
   `/dataflow/<id>/overview/summary`.
7. JSON: abrir el menu contextual del detalle y esperar la descarga asociada al
   elemento de exportacion. La respuesta validara que el archivo existe y que
   su contenido es JSON valido.

## Errores y resiliencia

- Errores tipados para configuracion invalida, autenticacion, tenant/espacio/
  flujo inexistente y descarga invalida.
- Auto-waiting de Playwright y assertions web-first; no se usaran sleeps fijos.
- Timeouts configurables y trace/screenshot solo en fallos.
- Reintentos limitados para navegacion cuando el error sea de red, sin repetir
  automaticamente un login fallido.
- Si aparece MFA, SSO o CAPTCHA, el proceso termina con un mensaje accionable.

## Pruebas

- Unitarias para validacion de configuracion y seleccion de tenant, espacio y
  flujo.
- Pruebas de parsing contra HTML representativo de Qlik, sin credenciales.
- E2E optativa con `QLIK_E2E=1`, credenciales reales y descarga temporal.
- La prueba E2E no se ejecutara por defecto en CI ni durante la instalacion.

## Criterios de aceptacion

- `npm install` y la instalacion de navegadores de Playwright completan.
- El comando principal falla claramente si faltan variables requeridas.
- El flujo puede listar tenants y seleccionar uno por nombre o por indice.
- El flujo puede listar espacios y flujos de datos usando selectores fuertes.
- El flujo abre el dataflow configurado y guarda un JSON valido.
- No se versionan `.env`, passwords, `storageState` ni descargas.
