import { cargarConfiguracion } from './config.js';
import { QlikClient } from './qlik/qlik.client.js';

try {
  const result = await new QlikClient(cargarConfiguracion()).run();
  process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
} catch (error) {
  const message = error instanceof Error ? error.message : 'Error desconocido';
  process.stderr.write(`No se pudo completar la automatizacion Qlik: ${message}\n`);
  process.exitCode = 1;
}
