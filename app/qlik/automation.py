import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urljoin

from playwright.async_api import Page, async_playwright
from playwright.async_api import TimeoutError as PlaywrightTimeoutError

from app.core.config import Settings


class QlikAutomationError(RuntimeError):
    """Error seguro para la API, sin credenciales en el mensaje."""


class QlikAutomation:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def run(
        self,
        tenant_name: str | None = None,
        space_name: str | None = None,
        dataflow_name: str | None = None,
        headless: bool | None = None,
    ) -> dict[str, Any]:
        selected_space = space_name or self.settings.qlik_space
        if selected_space is None:
            raise QlikAutomationError("No se configuro un espacio Qlik.")
        self.settings.validate_qlik(selected_space)
        download_dir = self.settings.qlik_download_dir.resolve()
        download_dir.mkdir(parents=True, exist_ok=True)

        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(
                headless=self.settings.qlik_headless if headless is None else headless
            )
            context_options: dict[str, Any] = {"accept_downloads": True}
            if self.settings.qlik_storage_state and self.settings.qlik_storage_state.exists():
                context_options["storage_state"] = str(self.settings.qlik_storage_state)
            context = await browser.new_context(**context_options)
            page = await context.new_page()
            try:
                result = await self._execute_flow(
                    page, context, tenant_name, selected_space, dataflow_name
                )
                return result
            finally:
                await context.close()
                await browser.close()

    async def _execute_flow(
        self,
        page: Page,
        context: Any,
        tenant_name: str | None,
        space_name: str,
        dataflow_name: str | None,
    ) -> dict[str, Any]:
        download_dir = self.settings.qlik_download_dir.resolve()
        await page.goto(
            self.settings.qlik_target_url, wait_until="domcontentloaded", timeout=120_000
        )
        await self._wait_for_page_ready(page)

        login_email = page.get_by_label(re.compile("email", re.IGNORECASE))
        if await login_email.count():
            await login_email.first.fill(
                self.settings.qlik_email or ""
            )
            await page.get_by_label(re.compile("password|contraseña", re.IGNORECASE)).fill(
                self.settings.qlik_password.get_secret_value()
                if self.settings.qlik_password
                else ""
            )
            await page.get_by_role(
                "button", name=re.compile("log in|iniciar sesión", re.IGNORECASE)
            ).click()
            challenge = page.get_by_text(
                re.compile("multi-factor|two-factor|mfa|sso|captcha", re.IGNORECASE)
            )
            if await challenge.count():
                raise QlikAutomationError(
                    "Qlik requiere MFA, SSO o CAPTCHA; completa el desafio manualmente."
                )
            await page.wait_for_url(re.compile(r"^(?!.*(?:login|auth0)).*"), timeout=60_000)
            await self._wait_for_page_ready(page)
            if self.settings.qlik_storage_state:
                self.settings.qlik_storage_state.parent.mkdir(parents=True, exist_ok=True)
                await context.storage_state(path=str(self.settings.qlik_storage_state))

        tenants = await self._list_tenants(page)
        if tenants:
            selected_tenant = self._select(tenants, tenant_name, "tenant")
            await page.get_by_role("button").filter(has_text=selected_tenant["name"]).first.click()
            await page.get_by_test_id(
                "nav-menu.analytics_creation.prepare_data_home"
            ).wait_for(state="visible", timeout=60_000)
        else:
            selected_tenant = {
                "name": tenant_name or "tenant actual",
                "hostname": page.url.split("/")[2] if "://" in page.url else page.url,
            }

        await page.get_by_test_id("nav-menu.analytics_creation.prepare_data_home").click()
        await page.wait_for_load_state("load", timeout=60_000)
        await page.get_by_test_id("browser-space-filter-btn").click()
        space_item = page.get_by_test_id(f"space-menu-item-{space_name}")
        if not await space_item.count():
            raise QlikAutomationError(f"No se encontro el espacio solicitado: {space_name}")
        await space_item.click()
        await page.get_by_test_id("browser-space-filter-btn").get_by_text(space_name).wait_for()

        dataflows = await self._list_dataflows(page)
        selected_dataflows = (
            [self._select(dataflows, dataflow_name, "flujo de datos")]
            if dataflow_name
            else dataflows
        )
        downloaded_files = []
        catalog_url = page.url
        for dataflow in selected_dataflows:
            await page.goto(urljoin(catalog_url, dataflow["href"]), wait_until="domcontentloaded")
            await page.wait_for_load_state("load", timeout=60_000)
            await page.wait_for_url(re.compile(r"/dataflow/[^/]+/overview/summary"), timeout=60_000)
            downloaded_files.append(
                await self._download_current_dataflow(page, download_dir, dataflow["name"])
            )

        return {
            "tenants": tenants,
            "selected_tenant": selected_tenant,
            "space": {"name": space_name},
            "dataflows": dataflows,
            "selected_dataflows": selected_dataflows,
            "downloaded_files": downloaded_files,
            "completed_at": datetime.now(UTC).isoformat(),
        }

    async def _download_current_dataflow(
        self, page: Page, download_dir: Any, dataflow_name: str
    ) -> str:
        context_menu = page.get_by_test_id("context-menu")
        if await context_menu.count():
            await context_menu.first.click()
        else:
            await page.get_by_role(
                "button", name=re.compile("más acciones|more actions", re.IGNORECASE)
            ).first.click()

        export_button = page.get_by_test_id("export-button")
        export_action = (
            export_button.first
            if await export_button.count()
            else page.get_by_role(
                "menuitem", name=re.compile("export|exportar", re.IGNORECASE)
            ).first
        )
        async with page.expect_download() as download_info:
            await export_action.click()
        download = await download_info.value
        target = self._unique_json_path(download_dir, dataflow_name)
        await download.save_as(str(target))
        try:
            json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise QlikAutomationError("La descarga no contiene JSON valido.") from error
        return str(target)

    @staticmethod
    async def _wait_for_page_ready(page: Page) -> None:
        await page.wait_for_load_state("load", timeout=60_000)
        login = page.get_by_label(re.compile("email", re.IGNORECASE))
        tenant = page.get_by_text(re.compile("choose tenant|selecciona.*tenant", re.IGNORECASE))
        prepare_data = page.get_by_test_id("nav-menu.analytics_creation.prepare_data_home")
        await login.or_(tenant).or_(prepare_data).first.wait_for(
            state="visible", timeout=60_000
        )

    @staticmethod
    def _unique_json_path(download_dir: Any, dataflow_name: str) -> Any:
        safe_name = re.sub(r"[^a-zA-Z0-9._-]+", "_", dataflow_name).strip("._") or "dataflow"
        target = download_dir / f"{safe_name}.json"
        counter = 2
        while target.exists():
            target = download_dir / f"{safe_name}_{counter}.json"
            counter += 1
        return target

    async def _list_tenants(self, page: Page) -> list[dict[str, str]]:
        tenant_heading = page.get_by_text(
            re.compile("choose tenant|selecciona.*tenant", re.IGNORECASE)
        )
        try:
            await tenant_heading.wait_for(timeout=5_000)
        except PlaywrightTimeoutError:
            return []
        tenants: list[dict[str, str]] = []
        for text in await page.get_by_role("button").all_inner_texts():
            hostname_match = re.search(r"[a-z0-9-]+(?:\.[a-z0-9-]+)+", text, re.IGNORECASE)
            if hostname_match:
                name = next((line.strip() for line in text.splitlines() if line.strip()), "")
                tenants.append({"name": name, "hostname": hostname_match.group(0)})
        return tenants

    async def _list_dataflows(self, page: Page) -> list[dict[str, str]]:
        dataflows: list[dict[str, str]] = []
        cards = page.get_by_test_id("appsItem")
        if await cards.count() == 0:
            await cards.first.wait_for(state="visible", timeout=60_000)
        for index in range(await cards.count()):
            card = cards.nth(index)
            name = await card.get_attribute("data-testmeta")
            href = await card.get_by_test_id("app-card-container-link").first.get_attribute("href")
            if name and href:
                dataflows.append({"name": " ".join(name.split()), "href": href})
        return dataflows

    @staticmethod
    def _select(items: list[dict[str, str]], name: str | None, item_type: str) -> dict[str, str]:
        if not items:
            raise QlikAutomationError(f"No hay {item_type} disponibles.")
        if not name:
            return items[0]
        expected = name.strip().casefold()
        for item in items:
            if item["name"].strip().casefold() == expected:
                return item
        raise QlikAutomationError(f"No se encontro el {item_type} solicitado: {name}")
