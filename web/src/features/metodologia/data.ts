import { z } from 'zod';
import { validationSchema, validationRowSchema, envelopeSchema } from '../../contract/types';

const binSchema = z.object({ bin: z.number(), p_mean: z.number(), y_mean: z.number(), n: z.number().int().nonnegative(), split: z.string(), model: z.string(), demo_data: z.boolean().optional(), evidence: z.string().optional() });
// Optional aggregate fields published by HACK-050; older mock envelopes omit them.
const extraFields = {
  rows_fast: z.array(validationRowSchema).optional(),
  calibration_bins: z.array(binSchema).optional(),
  calibration_bins_holdouts: z.array(binSchema).optional(),
  calibration_methods: z.array(z.object({ model: z.string(), label: z.string(), method: z.string(), logloss: z.number(), ece: z.number(), xrv_slope: z.number() }).passthrough()).optional(),
  leak_audit: z.array(z.object({ set: z.string(), label: z.string(), whiff_auc: z.number(), whiff_auc_lo: z.number(), whiff_auc_hi: z.number(), stuff_allowed: z.boolean() }).passthrough()).optional(),
};
export const extraSchema = envelopeSchema.extend(extraFields).strict();
export const methodologySchema = validationSchema.extend(extraFields);
export type Validation = z.infer<typeof methodologySchema>;
export type Row = Validation['rows'][number];
export const REPO = 'https://github.com/JoahanMorales/fuzzy-octo-pancake-DIABLOS-ROJOS-MLB';
export const sourceLink = (path: string) => `${REPO}/blob/main/${path.split('/').map(encodeURIComponent).join('/')}`;
export const percent = (value: number) => `${(value * 100).toLocaleString('es-MX', { minimumFractionDigits: 2, maximumFractionDigits: 2 })} %`;
export const number = (value: number) => value.toLocaleString('es-MX', { maximumFractionDigits: 5 });

export async function loadValidation(signal: AbortSignal): Promise<Validation> {
  const base = import.meta.env.BASE_URL;
  const manifest = await fetch(`${base}data/real/manifest.json`, { signal });
  let directory = 'mock';
  if (manifest.ok && manifest.headers.get('content-type')?.includes('application/json')) {
    await manifest.json();
    directory = 'real';
  } else if (manifest.status !== 404 && !(manifest.ok && manifest.headers.get('content-type')?.includes('text/html'))) {
    throw new Error('No se pudo comprobar la disponibilidad de resultados.');
  }
  const response = await fetch(`${base}data/${directory}/validation.json`, { signal });
  if (!response.ok) throw new Error('No se pudo cargar la validación.');
  const data = validationSchema.parse(await response.json());
  if (directory === 'mock' && !data.demo_data) throw new Error('El archivo de ejemplo no está identificado como ejemplo.');
  if (directory === 'mock') return data;
  const extraResponse = await fetch(`${base}data/real/validation_extra.json`, { signal });
  if (extraResponse.status === 404 || (extraResponse.ok && extraResponse.headers.get('content-type')?.includes('text/html'))) return data;
  if (!extraResponse.ok) throw new Error('No se pudo cargar la evidencia complementaria.');
  const extra = extraSchema.parse(await extraResponse.json());
  if (extra.model_version !== data.model_version || extra.model !== data.model || extra.translation !== data.translation || extra.demo_data !== data.demo_data) {
    throw new Error('Los archivos de validación pertenecen a versiones o estados distintos.');
  }
  return { ...data, ...extra, sources: [...new Set([...data.sources, ...extra.sources])] };
}

export const SPLITS = [
  ['pitcher_kfold', 'Pitchers separados'], ['season_holdout', 'Temporada separada'],
  ['park_holdout', 'Altitud extrema separada'], ['leave_one_park_out', 'Cada parque por separado'],
] as const;
export function metric(rows: Row[], model: string, name: string) {
  return rows.find((row) => row.model === model && row.metric === name)?.value;
}
