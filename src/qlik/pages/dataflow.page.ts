import fs from 'node:fs/promises';
import path from 'node:path';
import { expect, type Page } from '@playwright/test';
import { DownloadError } from '../errors.js';
import { selectoresQlik } from '../selectors.js';

export async function validarArchivoJson(filePath: string, downloadDir: string): Promise<void> {
  const resolvedFile = path.resolve(filePath);
  const resolvedDir = path.resolve(downloadDir);
  const relativePath = path.relative(resolvedDir, resolvedFile);

  if (relativePath.startsWith('..') || path.isAbsolute(relativePath)) {
    throw new DownloadError('La descarga quedo fuera de la carpeta configurada.');
  }

  try {
    const content = await fs.readFile(resolvedFile, 'utf8');
    JSON.parse(content);
  } catch (error) {
    throw new DownloadError('La descarga no contiene JSON valido.', { cause: error });
  }
}

export class DataflowPage {
  constructor(private readonly page: Page) {}

  async downloadJson(downloadDir: string): Promise<string> {
    await fs.mkdir(downloadDir, { recursive: true });
    const contextMenu = this.page.getByTestId(selectoresQlik.contextMenu);
    if (await contextMenu.count()) {
      await contextMenu.first().click();
    } else {
      await this.page.getByRole('button', { name: /más acciones|more actions/i }).first().click();
    }

    const exportButton = this.page.getByTestId(selectoresQlik.exportButton);
    const exportAction = (await exportButton.count())
      ? exportButton.first()
      : this.page.getByRole('menuitem', { name: /export|exportar/i }).first();

    const [download] = await Promise.all([
      this.page.waitForEvent('download'),
      exportAction.click(),
    ]);

    const fileName = download.suggestedFilename();
    const targetPath = path.resolve(downloadDir, fileName.endsWith('.json') ? fileName : `${fileName}.json`);
    await download.saveAs(targetPath);
    await expect.poll(() => targetPath.length).toBeGreaterThan(0);
    await validarArchivoJson(targetPath, downloadDir);
    return targetPath;
  }
}
