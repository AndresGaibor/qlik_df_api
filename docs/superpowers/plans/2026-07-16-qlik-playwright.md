# Qlik Playwright Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir una automatizacion local de Qlik Cloud que lea credenciales desde `.env`, seleccione tenant y espacio, liste flujos de datos y descargue un JSON.

**Architecture:** Proyecto TypeScript con `@playwright/test`, Page Objects pequenos y un orquestador `QlikClient`. La configuracion se valida antes de abrir el navegador; el flujo usa locators semanticamente fuertes y `storageState` opcional para persistir sesiones sin guardar credenciales.

**Tech Stack:** Node.js, TypeScript, Playwright Test, dotenv, Zod, Vitest para unit tests.

## Global Constraints

- Credenciales exclusivamente desde variables de entorno locales.
- No automatizar CAPTCHA, MFA o SSO.
- Preferencia de selectores: `getByRole`, `getByLabel`, `getByText`, `getByTestId`; evitar clases generadas.
- No usar sleeps fijos; usar auto-waiting y assertions web-first.
- No registrar credenciales ni versionar `.env`, storage state o descargas.
- Mantener archivos enfocados y validacion de entradas al inicio.

---

### Task 1: Scaffold seguro y dependencias

**Files:**
- Create: `package.json`
- Create: `tsconfig.json`
- Create: `playwright.config.ts`
- Create: `.env.example`
- Create: `.gitignore`
- Create: `src/config.ts`
- Test: `tests/unit/config.test.ts`

**Interfaces:**
- Produce `ConfiguracionQlik` y `cargarConfiguracion(env?: NodeJS.ProcessEnv): ConfiguracionQlik`.
- `ConfiguracionQlik` contiene `email`, `password`, `tenantName?`, `spaceName`, `dataflowName?`, `targetUrl`, `downloadDir`, `headless` y `storageStatePath`.

- [ ] **Step 1: Crear scaffold y dependencias**

Ejecutar `npm init -y`, instalar `@playwright/test`, `dotenv`, `zod`, `typescript`, `tsx`, `vitest` y `@types/node` como dependencias de desarrollo/ejecucion segun corresponda.

- [ ] **Step 2: Escribir tests RED de configuracion**

Cubrir email/password faltantes, `QLIK_HEADLESS` booleano, defaults de URL/carpeta y rechazo de `QLIK_SPACE` vacio.

- [ ] **Step 3: Implementar validacion**

Usar un schema Zod y copiar solo valores necesarios. Nunca incluir el password en errores serializados.

- [ ] **Step 4: Configurar Playwright y Git**

Configurar `testDir: './tests/e2e'`, Chromium, `trace: 'retain-on-failure'`, screenshots en fallos, `acceptDownloads: true` y timeout configurable. Ignorar `.env`, `artifacts/`, `playwright/.auth/`, `downloads/`, `test-results/` y `playwright-report/`.

- [ ] **Step 5: Verificar GREEN**

Ejecutar `npm test -- --run tests/unit/config.test.ts` y `npx tsc --noEmit`.

### Task 2: Selectores y parsing puros

**Files:**
- Create: `src/qlik/types.ts`
- Create: `src/qlik/selectors.ts`
- Create: `src/qlik/parsers.ts`
- Test: `tests/unit/parsers.test.ts`

**Interfaces:**
- Produce `TenantInfo`, `SpaceInfo`, `DataflowInfo`, `QlikRunResult`.
- Produce `seleccionarPorNombreOPrimero<T>(items: readonly T[], nombre: string | undefined, obtenerNombre: (item: T) => string): T`.
- Produce `normalizarNombreDataflow(value: string): string`.

- [ ] **Step 1: Escribir tests RED**

Probar selección por nombre exacto, fallback al primero, error de lista vacía, deduplicación de spaces repetidos y extracción de nombres/URLs desde HTML representativo.

- [ ] **Step 2: Implementar tipos, selectores y parsers**

Los selectores centralizados deben usar los `data-testid` documentados por Qlik solo cuando no exista locator accesible. No usar clases como `css-*`.

- [ ] **Step 3: Verificar GREEN**

Ejecutar `npm test -- --run tests/unit/parsers.test.ts` y `npx tsc --noEmit`.

### Task 3: Page Objects de login y tenant

**Files:**
- Create: `src/qlik/pages/login.page.ts`
- Create: `src/qlik/pages/tenant.page.ts`
- Test: `tests/unit/pages/tenant.page.test.ts`

**Interfaces:**
- `LoginPage.login(email: string, password: string): Promise<void>`.
- `TenantPage.listTenants(): Promise<TenantInfo[]>`.
- `TenantPage.selectTenant(name?: string): Promise<TenantInfo>`.

- [ ] **Step 1: Escribir tests RED con Page/Locator mocks**

Verificar que el login usa labels y rol del botón, que tenant devuelve nombre/hostname y que seleccionar sin nombre usa el primer tenant.

- [ ] **Step 2: Implementar `LoginPage`**

Usar `getByLabel(/email/i)`, `getByLabel(/password/i)` y `getByRole('button', { name: /log in|iniciar sesión/i })`. Detectar texto de MFA/SSO/CAPTCHA y lanzar `AuthenticationError` accionable.

- [ ] **Step 3: Implementar `TenantPage`**

Esperar la pantalla `Choose tenant` mediante texto/heading, localizar botones de tenant y extraer nombre/hostname de cada tarjeta sin depender de clases.

- [ ] **Step 4: Verificar GREEN**

Ejecutar la prueba unitaria y `npx tsc --noEmit`.

### Task 4: Page Object del hub, espacios y dataflows

**Files:**
- Create: `src/qlik/pages/hub.page.ts`
- Test: `tests/unit/pages/hub.page.test.ts`

**Interfaces:**
- `HubPage.goToPrepareData(): Promise<void>`.
- `HubPage.selectSpace(spaceName: string): Promise<SpaceInfo>`.
- `HubPage.listDataflows(): Promise<DataflowInfo[]>`.
- `HubPage.openDataflow(dataflow: DataflowInfo): Promise<void>`.

- [ ] **Step 1: Escribir tests RED**

Cubrir navegación por `nav-menu.analytics_creation.prepare_data_home`, apertura del selector, búsqueda opcional por nombre, selección del espacio y extracción de múltiples tarjetas `appsItem`.

- [ ] **Step 2: Implementar navegación y espacio**

Abrir `browser-space-filter-btn`, usar `space-menu-item-<nombre>` cuando exista y verificar el chip seleccionado. Si el nombre no existe, lanzar `SpaceNotFoundError` con nombres visibles, sin incluir secretos.

- [ ] **Step 3: Implementar listado y apertura**

Extraer `data-testmeta`, tipo accesible y href del enlace `app-card-container-link`. Seleccionar por nombre o fallback al primero y esperar URL `/dataflow/<id>/overview/summary`.

- [ ] **Step 4: Verificar GREEN**

Ejecutar `npm test -- --run tests/unit/pages/hub.page.test.ts` y `npx tsc --noEmit`.

### Task 5: Descarga JSON y orquestador

**Files:**
- Create: `src/qlik/errors.ts`
- Create: `src/qlik/pages/dataflow.page.ts`
- Create: `src/qlik/qlik.client.ts`
- Create: `src/cli.ts`
- Test: `tests/unit/pages/dataflow.page.test.ts`
- Test: `tests/unit/qlik.client.test.ts`

**Interfaces:**
- `DataflowPage.downloadJson(downloadDir: string): Promise<string>`.
- `QlikClient.run(): Promise<QlikRunResult>`.
- CLI `npm run qlik:download` imprime solo resultado no sensible en JSON.

- [ ] **Step 1: Escribir tests RED**

Verificar que la descarga se arma con `Promise.all([page.waitForEvent('download'), click])`, que el archivo se guarda dentro de `downloadDir`, que JSON inválido genera `DownloadError` y que el cliente coordina el flujo completo.

- [ ] **Step 2: Implementar errores tipados**

Crear `ConfigurationError`, `AuthenticationError`, `TenantNotFoundError`, `SpaceNotFoundError`, `DataflowNotFoundError` y `DownloadError`, todos sin incluir valores secretos.

- [ ] **Step 3: Implementar `DataflowPage`**

Abrir el menú contextual accesible o por `getByTestId('context-menu')`, localizar el elemento de exportación por rol/test id y capturar la descarga. Validar extensión, ruta contenida en la carpeta permitida y `JSON.parse` del contenido.

- [ ] **Step 4: Implementar `QlikClient` y CLI**

Crear contexto con `acceptDownloads`, cargar `storageState` si existe, ejecutar login solo cuando la sesión no esté autenticada, guardar estado después del login y cerrar página/contexto en `finally`.

- [ ] **Step 5: Verificar GREEN**

Ejecutar ambas pruebas unitarias, `npx tsc --noEmit` y `npm run qlik:download` sin `.env` para comprobar un error seguro de configuración.

### Task 6: E2E optativo, documentación y verificación final

**Files:**
- Create: `tests/e2e/qlik-download.spec.ts`
- Create: `README.md`
- Create: `docs/testing/qlik-playwright.tdd.md`
- Modify: `package.json`

- [ ] **Step 1: Crear E2E optativo**

El test debe hacer `test.skip(!process.env.QLIK_E2E, '...')`, cargar configuración desde `.env`, listar tenants, verificar el espacio, listar dataflows, abrir el seleccionado y validar que el JSON descargado parsea correctamente.

- [ ] **Step 2: Documentar uso**

Documentar `cp .env.example .env`, instalación de navegadores, ejecución de unit tests, ejecución headed para completar MFA manualmente y ejecución E2E explícita. Nunca incluir valores reales.

- [ ] **Step 3: Verificar cobertura y calidad**

Ejecutar `npm test -- --coverage`, `npx tsc --noEmit`, `npx playwright test --list` y el lint disponible. Registrar resultados reales y gaps en el reporte TDD.

- [ ] **Step 4: Revisar seguridad**

Confirmar que `git diff --check` no muestra errores, `.env` no aparece en `git status`, ningún log contiene password y las rutas de descarga no permiten escapar de `QLIK_DOWNLOAD_DIR`.
