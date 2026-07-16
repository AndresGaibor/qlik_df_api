import type { DataflowInfo, SpaceInfo, TenantInfo } from './types.js';

export function seleccionarPorNombreOPrimero<T>(
  items: readonly T[],
  nombre: string | undefined,
  obtenerNombre: (item: T) => string,
): T {
  if (items.length === 0) {
    throw new Error('No hay elementos disponibles para seleccionar');
  }

  if (!nombre) {
    return items[0];
  }

  const esperado = nombre.trim().toLocaleLowerCase();
  const encontrado = items.find((item) => obtenerNombre(item).trim().toLocaleLowerCase() === esperado);

  if (!encontrado) {
    throw new Error(`No se encontro el elemento solicitado: ${nombre}`);
  }

  return encontrado;
}

export function normalizarNombreDataflow(value: string): string {
  return value.replace(/\s+/g, ' ').trim();
}

export function deduplicarEspacios(spaces: readonly SpaceInfo[]): SpaceInfo[] {
  return [...new Map(spaces.map((space) => [space.id ?? space.name, space])).values()];
}

export function parsearTenants(records: readonly { name?: string; hostname?: string }[]): TenantInfo[] {
  return records
    .filter((record): record is { name: string; hostname: string } => Boolean(record.name && record.hostname))
    .map(({ name, hostname }) => ({ name: name.trim(), hostname: hostname.trim() }));
}

export function parsearDataflows(
  records: readonly { name?: string; type?: string; href?: string }[],
): DataflowInfo[] {
  return records
    .filter((record): record is { name: string; type: string; href: string } =>
      Boolean(record.name && record.type && record.href),
    )
    .map(({ name, type, href }) => ({
      name: normalizarNombreDataflow(name),
      type: type.trim(),
      href,
    }));
}
