import { describe, expect, it } from 'vitest';
import { cargarConfiguracion } from '../../src/config.js';

const baseEnv = {
  QLIK_EMAIL: 'usuario@ejemplo.com',
  QLIK_PASSWORD: 'secreto',
  QLIK_SPACE: 'Espacio de prueba',
};

describe('cargarConfiguracion', () => {
  it('rechaza credenciales faltantes', () => {
    expect(() => cargarConfiguracion({ QLIK_SPACE: 'Espacio' })).toThrow(/QLIK_EMAIL/);
  });

  it('rechaza un espacio vacio', () => {
    expect(() => cargarConfiguracion({ ...baseEnv, QLIK_SPACE: ' ' })).toThrow(/QLIK_SPACE/);
  });

  it('aplica defaults seguros y convierte headless', () => {
    const configuracion = cargarConfiguracion({ ...baseEnv, QLIK_HEADLESS: 'false' });

    expect(configuracion.targetUrl).toBe('https://qlikcloud.com/');
    expect(configuracion.headless).toBe(false);
    expect(configuracion.downloadDir).toMatch(/downloads$/);
    expect(configuracion.storageStatePath).toMatch(/playwright\/\.auth\/qlik\.json$/);
  });

  it('rechaza un valor invalido para headless', () => {
    expect(() => cargarConfiguracion({ ...baseEnv, QLIK_HEADLESS: 'yes' })).toThrow(/QLIK_HEADLESS/);
  });
});
