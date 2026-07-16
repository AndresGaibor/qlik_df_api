import { describe, expect, it } from 'vitest';
import {
  deduplicarEspacios,
  normalizarNombreDataflow,
  parsearDataflows,
  parsearTenants,
  seleccionarPorNombreOPrimero,
} from '../../src/qlik/parsers.js';

describe('parsers y seleccion', () => {
  it('selecciona por nombre ignorando mayusculas y espacios externos', () => {
    const result = seleccionarPorNombreOPrimero([{ name: ' Comercial ' }], 'comercial', (item) => item.name);

    expect(result.name).toBe(' Comercial ');
  });

  it('selecciona el primer elemento cuando no hay nombre', () => {
    expect(seleccionarPorNombreOPrimero(['primero', 'segundo'], undefined, (item) => item)).toBe('primero');
  });

  it('rechaza una lista vacia y un nombre desconocido', () => {
    expect(() => seleccionarPorNombreOPrimero([], undefined, String)).toThrow(/No hay elementos/);
    expect(() => seleccionarPorNombreOPrimero(['A'], 'B', (item) => item)).toThrow(/B/);
  });

  it('deduplica espacios por id o nombre', () => {
    expect(
      deduplicarEspacios([
        { id: '1', name: 'A' },
        { id: '1', name: 'A actualizado' },
        { name: 'B' },
        { name: 'B' },
      ]),
    ).toEqual([{ id: '1', name: 'A actualizado' }, { name: 'B' }]);
  });

  it('descarta registros incompletos y normaliza dataflows', () => {
    expect(parsearTenants([{ name: ' Tenant ', hostname: 'host.example' }, { name: 'incompleto' }])).toEqual([
      { name: 'Tenant', hostname: 'host.example' },
    ]);
    expect(
      parsearDataflows([
        { name: ' Flujo   S3 ', type: ' Flujo de datos ', href: '/dataflow/1' },
        { name: 'sin url', type: 'x' },
      ]),
    ).toEqual([{ name: 'Flujo S3', type: 'Flujo de datos', href: '/dataflow/1' }]);
    expect(normalizarNombreDataflow('  a   b  ')).toBe('a b');
  });
});
