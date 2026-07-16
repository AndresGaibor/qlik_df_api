import { expect, type Page } from '@playwright/test';
import { DataflowNotFoundError, SpaceNotFoundError } from '../errors.js';
import { parsearDataflows, seleccionarPorNombreOPrimero } from '../parsers.js';
import { selectoresQlik } from '../selectors.js';
import type { DataflowInfo, SpaceInfo } from '../types.js';

export class HubPage {
  constructor(private readonly page: Page) {}

  async goToPrepareData(): Promise<void> {
    await this.page.getByTestId(selectoresQlik.prepareDataLink).click();
    await expect(this.page.getByTestId(selectoresQlik.spaceFilterButton)).toBeVisible();
  }

  async selectSpace(spaceName: string): Promise<SpaceInfo> {
    await this.page.getByTestId(selectoresQlik.spaceFilterButton).click();
    const spaceItem = this.page.getByTestId(`space-menu-item-${spaceName}`);

    if (!(await spaceItem.count())) {
      throw new SpaceNotFoundError(`No se encontro el espacio solicitado: ${spaceName}`);
    }

    await spaceItem.click();
    await expect(this.page.getByTestId(selectoresQlik.spaceFilterButton)).toContainText(spaceName);
    return { name: spaceName, id: await spaceItem.getAttribute('id') ?? undefined };
  }

  async listDataflows(): Promise<DataflowInfo[]> {
    const cards = this.page.getByTestId(selectoresQlik.dataflowCard);
    const records: { name?: string; type?: string; href?: string }[] = [];

    for (let index = 0; index < await cards.count(); index += 1) {
      const card = cards.nth(index);
      const name = await card.getAttribute('data-testmeta');
      const link = card.getByTestId(selectoresQlik.dataflowLink).first();
      const href = await link.getAttribute('href');
      const type = await card.getAttribute('aria-label');
      records.push({ name: name ?? undefined, type: type ?? undefined, href: href ?? undefined });
    }

    return parsearDataflows(records);
  }

  async selectDataflow(name?: string): Promise<DataflowInfo> {
    const dataflows = await this.listDataflows();
    try {
      return seleccionarPorNombreOPrimero(dataflows, name, (dataflow) => dataflow.name);
    } catch (error) {
      throw new DataflowNotFoundError(error instanceof Error ? error.message : 'Flujo no encontrado', {
        cause: error,
      });
    }
  }

  async openDataflow(dataflow: DataflowInfo): Promise<void> {
    const card = this.page.getByTestId(selectoresQlik.dataflowCard).filter({ hasText: dataflow.name }).first();
    await card.getByTestId(selectoresQlik.dataflowLink).click();
    await this.page.waitForURL(/\/dataflow\/[^/]+\/overview\/summary/);
  }
}
