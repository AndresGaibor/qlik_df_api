import { expect, type Locator, type Page } from '@playwright/test';
import { TenantNotFoundError } from '../errors.js';
import { seleccionarPorNombreOPrimero } from '../parsers.js';
import type { TenantInfo } from '../types.js';

function hostnameFromText(text: string): string | undefined {
  return text.match(/[a-z0-9-]+(?:\.[a-z0-9-]+)+/i)?.[0];
}

export class TenantPage {
  constructor(private readonly page: Page) {}

  private async tenantButtons(): Promise<Locator> {
    await expect(this.page.getByText(/choose tenant|selecciona.*tenant/i)).toBeVisible({ timeout: 30_000 });
    return this.page.getByRole('button');
  }

  async listTenants(): Promise<TenantInfo[]> {
    const buttons = await this.tenantButtons();
    const tenants: TenantInfo[] = [];
    const count = await buttons.count();

    for (let index = 0; index < count; index += 1) {
      const button = buttons.nth(index);
      const text = (await button.innerText()).trim();
      const hostname = hostnameFromText(text);
      if (!hostname) continue;

      const name = text
        .replace(hostname, '')
        .split('\n')
        .map((value) => value.trim())
        .find(Boolean);
      if (name) tenants.push({ name, hostname });
    }

    return tenants;
  }

  async selectTenant(name?: string): Promise<TenantInfo> {
    const tenants = await this.listTenants();
    let selected: TenantInfo;
    try {
      selected = seleccionarPorNombreOPrimero(tenants, name, (tenant) => tenant.name);
    } catch (error) {
      throw new TenantNotFoundError(error instanceof Error ? error.message : 'Tenant no encontrado', {
        cause: error,
      });
    }

    await this.page.getByRole('button').filter({ hasText: selected.name }).first().click();
    return selected;
  }
}
