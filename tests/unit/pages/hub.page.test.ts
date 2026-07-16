import { describe, expect, it } from 'vitest';
import { parsearDataflows, seleccionarPorNombreOPrimero } from '../../../src/qlik/parsers.js';

describe('HubPage contract', () => {
  it('selecciona un dataflow configurado o el primero', () => {
    const dataflows = parsearDataflows([
      { name: 'Flujo A', type: 'Flujo de datos', href: '/dataflow/a' },
      { name: 'Flujo B', type: 'Flujo de datos', href: '/dataflow/b' },
    ]);

    expect(seleccionarPorNombreOPrimero(dataflows, 'Flujo B', (item) => item.name).href).toBe('/dataflow/b');
    expect(seleccionarPorNombreOPrimero(dataflows, undefined, (item) => item.name).href).toBe('/dataflow/a');
  });
});
