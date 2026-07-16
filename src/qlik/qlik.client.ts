import fs from 'node:fs/promises';
import path from 'node:path';
import { chromium, type Browser, type BrowserContext, type Page } from '@playwright/test';
import type { ConfiguracionQlik } from '../config.js';
import { HubPage } from './pages/hub.page.js';
import { LoginPage } from './pages/login.page.js';
import { TenantPage } from './pages/tenant.page.js';
import { DataflowPage } from './pages/dataflow.page.js';
import type { QlikRunResult, TenantInfo } from './types.js';

export class QlikClient {
  constructor(private readonly configuracion: ConfiguracionQlik) {}

  async run(): Promise<QlikRunResult> {
    const browser: Browser = await chromium.launch({ headless: this.configuracion.headless });
    let context: BrowserContext | undefined;
    let page: Page | undefined;

    try {
      const storageState = await this.storageStateIfExists();
      context = await browser.newContext({ acceptDownloads: true, storageState });
      context.setDefaultTimeout(30_000);
      context.setDefaultNavigationTimeout(120_000);
      page = await context.newPage();
      await page.goto(this.configuracion.targetUrl, { waitUntil: 'domcontentloaded' });

      const loginPage = new LoginPage(page);
      if (await page.getByLabel(/email/i).count()) {
        await loginPage.login(this.configuracion.email, this.configuracion.password);
        await fs.mkdir(path.dirname(this.configuracion.storageStatePath), { recursive: true });
        await context.storageState({ path: this.configuracion.storageStatePath });
      }

      const tenantPage = new TenantPage(page);
      const tenantScreen = page.getByText(/choose tenant|selecciona.*tenant/i);
      const tenants = (await tenantScreen.count()) ? await tenantPage.listTenants() : [];
      const selectedTenant: TenantInfo = tenants.length
        ? await tenantPage.selectTenant(this.configuracion.tenantName)
        : { name: this.configuracion.tenantName ?? 'tenant actual', hostname: new URL(page.url()).hostname };

      const hubPage = new HubPage(page);
      await hubPage.goToPrepareData();
      const selectedSpace = await hubPage.selectSpace(this.configuracion.spaceName);
      const dataflows = await hubPage.listDataflows();
      const selectedDataflow = await hubPage.selectDataflow(this.configuracion.dataflowName);
      await hubPage.openDataflow(selectedDataflow);
      const downloadedFile = await new DataflowPage(page).downloadJson(this.configuracion.downloadDir);

      return { tenants, selectedTenant, selectedSpace, dataflows, selectedDataflow, downloadedFile };
    } finally {
      await page?.close();
      await context?.close();
      await browser.close();
    }
  }

  private async storageStateIfExists(): Promise<string | undefined> {
    try {
      await fs.access(this.configuracion.storageStatePath);
      return this.configuracion.storageStatePath;
    } catch {
      return undefined;
    }
  }
}
