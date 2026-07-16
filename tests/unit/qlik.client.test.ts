import { describe, expect, it } from 'vitest';
import { QlikClient } from '../../src/qlik/qlik.client.js';

describe('QlikClient', () => {
  it('expone el contrato de ejecucion', () => {
    expect(typeof new QlikClient({} as never).run).toBe('function');
  });
});
