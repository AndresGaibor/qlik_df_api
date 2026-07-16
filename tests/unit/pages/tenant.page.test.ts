import { describe, expect, it } from 'vitest';
import { seleccionarPorNombreOPrimero } from '../../../src/qlik/parsers.js';

describe('TenantPage contract', () => {
  it('usa la regla de seleccion por nombre o primero', () => {
    const tenants = [
      { name: 'Tenant A', hostname: 'a.example.com' },
      { name: 'Tenant B', hostname: 'b.example.com' },
    ];

    expect(seleccionarPorNombreOPrimero(tenants, 'Tenant B', (tenant) => tenant.name)).toEqual(tenants[1]);
    expect(seleccionarPorNombreOPrimero(tenants, undefined, (tenant) => tenant.name)).toEqual(tenants[0]);
  });
});
