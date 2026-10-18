/* Stuff+ ± interval for the row's sample size (HACK-069), from real/uncertainty.json (analysis/export_web/
   uncertainty.py: 90 % split conformal by number of pitches and by air). No file, no band and no error. */
import { useEffect, useState } from 'react';
import { dataSource, fmt } from './data';

export type Air = 'neutral' | 'harp_helu';

export interface BandRow {
  air: Air;
  n_pitches: number;
  half_width: number;
  coverage: number;
}

export interface Bands {
  alpha: number;
  rows: BandRow[];
}

const BASE = `${import.meta.env.BASE_URL ?? './'}data/`;

/** Half-width for `pitches` pitches: the row of the largest calibrated n not above it. Below the smallest calibrated
 *  n there is no band (it would understate the uncertainty). Calibrated on pitcher-season means. */
export function halfWidth(bands: Bands | null, air: Air, pitches: number): BandRow | null {
  if (!bands) return null;
  const rows = bands.rows.filter((r) => r.air === air && Number.isFinite(r.half_width)).sort((a, b) => a.n_pitches - b.n_pitches);
  if (!rows.length || !(pitches > 0)) return null;
  return [...rows].reverse().find((r) => r.n_pitches <= pitches) ?? null;
}

export async function loadBands(fetcher: typeof fetch = fetch): Promise<Bands | null> {
  try {
    if ((await dataSource(fetcher as never)) !== 'real') return null;
    const r = await fetcher(`${BASE}real/uncertainty.json`);
    if (!r.ok) return null;
    const doc = (await r.json()) as Partial<Bands>;
    return Array.isArray(doc.rows) ? { alpha: doc.alpha ?? 0.1, rows: doc.rows as BandRow[] } : null;
  } catch {
    return null; // missing or not JSON (static-host fallback): no band
  }
}

export function useBands(): Bands | null {
  const [bands, setBands] = useState<Bands | null>(null);
  useEffect(() => {
    let live = true;
    loadBands().then((b) => live && setBands(b));
    return () => {
      live = false;
    };
  }, []);
  return bands;
}

/** "± 3.1" after a Stuff+ value, with a one-line tooltip on what it means. */
export function Band({ bands, air, pitches }: { bands: Bands | null; air: Air; pitches: number }) {
  const row = halfWidth(bands, air, pitches);
  if (!row) return null;
  const level = Math.round((1 - (bands?.alpha ?? 0.1)) * 100);
  const tip = `${level} % de las veces, el Stuff+ medido con ${row.n_pitches} lanzamientos queda a ±${fmt(row.half_width)} de su valor con el resto de la temporada (cobertura medida ${Math.round(row.coverage * 100)} %).`;
  return (
    <span className="lb-band" title={tip} aria-label={`más o menos ${fmt(row.half_width)}. ${tip}`}>
      ±{fmt(row.half_width)}
    </span>
  );
}
