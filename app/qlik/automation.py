import json
import re
from datetime import UTC, datetime
from typing import Any

from playwright.async_api import Page, async_playwright

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
            if self.settings.qlik_storage_state.exists():
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

        if await page.get_by_label(re.compile("email", re.IGNORECASE)).count():
            await page.get_by_label(re.compile("email", re.IGNORECASE)).fill(
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
            self.settings.qlik_storage_state.parent.mkdir(parents=True, exist_ok=True)
            await context.storage_state(path=str(self.settings.qlik_storage_state))

        tenants = await self._list_tenants(page)
        selected_tenant = self._select(tenants, tenant_name, "tenant")
        if tenants:
            await page.get_by_role("button").filter(has_text=selected_tenant["name"]).first.click()

        await page.get_by_test_id("nav-menu.analytics_creation.prepare_data_home").click()
        await page.get_by_test_id("browser-space-filter-btn").click()
        space_item = page.get_by_test_id(f"space-menu-item-{space_name}")
        if not await space_item.count():
            raise QlikAutomationError(f"No se encontro el espacio solicitado: {space_name}")
        await space_item.click()
        await page.get_by_test_id("browser-space-filter-btn").get_by_text(space_name).wait_for()

        dataflows = await self._list_dataflows(page)
        selected_dataflow = self._select(dataflows, dataflow_name, "flujo de datos")
        card = page.get_by_test_id("appsItem").filter(has_text=selected_dataflow["name"]).first
        await card.get_by_test_id("app-card-container-link").click()
        await page.wait_for_url(re.compile(r"/dataflow/[^/]+/overview/summary"), timeout=60_000)

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
        filename = download.suggested_filename
        target = download_dir / (filename if filename.endswith(".json") else f"{filename}.json")
        await download.save_as(str(target))
        try:
            json.loads(target.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise QlikAutomationError("La descarga no contiene JSON valido.") from error

        return {
            "tenants": tenants,
            "selected_tenant": selected_tenant,
            "space": {"name": space_name},
            "dataflows": dataflows,
            "selected_dataflow": selected_dataflow,
            "downloaded_file": str(target),
            "completed_at": datetime.now(UTC).isoformat(),
        }

    async def _list_tenants(self, page: Page) -> list[dict[str, str]]:
        if not await page.get_by_text(
            re.compile("choose tenant|selecciona.*tenant", re.IGNORECASE)
        ).count():
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
