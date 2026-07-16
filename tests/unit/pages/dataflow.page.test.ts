import fs from 'node:fs/promises';
import os from 'node:os';
import path from 'node:path';
import { describe, expect, it } from 'vitest';
import { validarArchivoJson } from '../../../src/qlik/pages/dataflow.page.js';

describe('validarArchivoJson', () => {
  it('acepta un JSON dentro de la carpeta configurada', async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'qlik-download-'));
    const file = path.join(directory, 'data.json');
    await fs.writeFile(file, JSON.stringify({ ok: true }));

    await expect(validarArchivoJson(file, directory)).resolves.toBeUndefined();
  });

  it('rechaza JSON invalido y rutas fuera del directorio', async () => {
    const directory = await fs.mkdtemp(path.join(os.tmpdir(), 'qlik-download-'));
    const file = path.join(directory, 'data.json');
    await fs.writeFile(file, '{no valido');

    await expect(validarArchivoJson(file, directory)).rejects.toThrow(/JSON valido/);
    await expect(validarArchivoJson(path.join(directory, '..', 'outside.json'), directory)).rejects.toThrow(
      /fuera/,
    );
  });
});
