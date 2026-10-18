import {
  parseContractFile,
  parksSchema,
  shapesSchema,
  staffSchema,
  validationSchema,
} from '../../contract/types';
import type { z } from 'zod';

export type ValidationFile = z.infer<typeof validationSchema>;
export type ShapesFile = z.infer<typeof shapesSchema>;
export type StaffFile = z.infer<typeof staffSchema>;
export type ParksFile = z.infer<typeof parksSchema>;

export interface LandingData {
  root: 'real' | 'mock';
  validation: ValidationFile;
  shapes: ShapesFile;
  staff: StaffFile;
  parks: ParksFile;
}

async function readJson(fetchImpl: typeof fetch, url: string): Promise<unknown> {
  const response = await fetchImpl(url);
  if (!response.ok) throw new Error(`No se pudo leer ${url}`);
  const text = await response.text();
  try {
    return JSON.parse(text);
  } catch {
    throw new Error(`${url} no es JSON`);
  }
}

/** Un host estático a veces responde 200 con el HTML de la app. Eso no es el manifiesto. */
async function jsonManifest(fetchImpl: typeof fetch, url: string): Promise<boolean> {
  try {
    const response = await fetchImpl(url);
    if (!response.ok) return false;
    const type = response.headers.get('content-type') ?? '';
    if (type.includes('text/html')) return false;
    JSON.parse(await response.text());
    return true;
  } catch {
    return false;
  }
}

/** Si `data/real/manifest.json` es JSON, el informe es real. Si no, el mock. */
export async function loadLanding(fetchImpl: typeof fetch = fetch): Promise<LandingData> {
  const base = import.meta.env.BASE_URL ?? './';
  const root = await jsonManifest(fetchImpl, `${base}data/real/manifest.json`) ? 'real' : 'mock';

  const [validation, shapes, staff, parks] = await Promise.all([
    readJson(fetchImpl, `${base}data/${root}/validation.json`),
    readJson(fetchImpl, `${base}data/${root}/shapes.json`),
    readJson(fetchImpl, `${base}data/${root}/staff.json`),
    readJson(fetchImpl, `${base}data/${root}/parks.json`),
  ]);

  return {
    root,
    validation: parseContractFile('validation.json', validation) as LandingData['validation'],
    shapes: parseContractFile('shapes.json', shapes) as LandingData['shapes'],
    staff: parseContractFile('staff.json', staff) as LandingData['staff'],
    parks: parseContractFile('parks.json', parks) as LandingData['parks'],
  };
}
