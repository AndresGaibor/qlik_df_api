import path from 'node:path';
import { config as loadDotenv } from 'dotenv';
import { z } from 'zod';

const environmentSchema = z.object({
  QLIK_EMAIL: z.string().trim().email(),
  QLIK_PASSWORD: z.string().min(1),
  QLIK_TENANT: z.string().trim().min(1).optional(),
  QLIK_SPACE: z.string().trim().min(1),
  QLIK_DATAFLOW_NAME: z.string().trim().min(1).optional(),
  QLIK_TARGET_URL: z.string().url().default('https://qlikcloud.com/'),
  QLIK_DOWNLOAD_DIR: z.string().trim().min(1).default('downloads'),
  QLIK_HEADLESS: z.enum(['true', 'false']).default('true'),
  QLIK_STORAGE_STATE: z.string().trim().min(1).default('playwright/.auth/qlik.json'),
});

export type ConfiguracionQlik = {
  email: string;
  password: string;
  tenantName?: string;
  spaceName: string;
  dataflowName?: string;
  targetUrl: string;
  downloadDir: string;
  headless: boolean;
  storageStatePath: string;
};

export function cargarConfiguracion(env: NodeJS.ProcessEnv = process.env): ConfiguracionQlik {
  loadDotenv();
  const parsed = environmentSchema.safeParse(env);

  if (!parsed.success) {
    const fields = parsed.error.issues.map((issue) => issue.path.join('.')).join(', ');
    throw new Error(`Configuracion Qlik invalida. Revisa: ${fields}`);
  }

  return {
    email: parsed.data.QLIK_EMAIL,
    password: parsed.data.QLIK_PASSWORD,
    tenantName: parsed.data.QLIK_TENANT,
    spaceName: parsed.data.QLIK_SPACE,
    dataflowName: parsed.data.QLIK_DATAFLOW_NAME,
    targetUrl: parsed.data.QLIK_TARGET_URL,
    downloadDir: path.resolve(parsed.data.QLIK_DOWNLOAD_DIR),
    headless: parsed.data.QLIK_HEADLESS === 'true',
    storageStatePath: path.resolve(parsed.data.QLIK_STORAGE_STATE),
  };
}
