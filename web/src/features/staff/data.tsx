/* Contract loader for the HACK-048 pages (same rule as HACK-047/050): read data/real/ when
   data/real/manifest.json exists, else data/mock/. Documents are validated with the HACK-038 schemas and the
   badge comes from `demo_data`. Models always live in data/models/ (HACK-040). */
import { useEffect, useState } from 'react';
import { parseContractFile } from '../../contract/types';

export type Source = 'real' | 'mock';
export type Fetcher = (url: string) => Promise<{ ok: boolean; json: () => Promise<unknown> }>;

export const DATA_BASE = `${import.meta.env.BASE_URL ?? './'}data/`;
let sourcePromise: Promise<Source> | null = null;

export function resetSourceCache() {
  sourcePromise = null;
}

export function dataSource(fetcher: Fetcher = fetch): Promise<Source> {
  if (!sourcePromise) {
    sourcePromise = fetcher(`${DATA_BASE}real/manifest.json`)
      .then((r) => (r.ok ? 'real' : 'mock') as Source)
      .catch(() => 'mock' as Source);
  }
  return sourcePromise;
}

export async function loadDoc<T>(rel: string, fetcher: Fetcher = fetch): Promise<{ doc: T; source: Source }> {
  const source = await dataSource(fetcher);
  const res = await fetcher(`${DATA_BASE}${source}/${rel}`);
  if (!res.ok) throw new Error(`no se encontró ${source}/${rel}`);
  return { doc: parseContractFile(rel, await res.json()) as T, source };
}

export type Loaded<T> =
  | { state: 'loading' }
  | { state: 'error'; message: string }
  | { state: 'ready'; doc: T; source: Source };

/** Runs `load` once; components stay pure functions of what it returns. */
export function useLoaded<T>(load: () => Promise<{ doc: T; source: Source }>, key: string): Loaded<T> {
  const [out, setOut] = useState<Loaded<T>>({ state: 'loading' });
  useEffect(() => {
    let live = true;
    setOut({ state: 'loading' });
    load()
      .then(({ doc, source }) => live && setOut({ state: 'ready', doc, source }))
      .catch((e: unknown) => live && setOut({ state: 'error', message: e instanceof Error ? e.message : String(e) }));
    return () => {
      live = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return out;
}

const MINUS = '−';

/** Fixed decimals with a real minus sign (DESIGN.md copy rules); null → "-". */
export function fmt(v: number | null | undefined, digits = 1, signed = false): string {
  if (v === null || v === undefined || Number.isNaN(v)) return '-';
  const s = Math.abs(v).toFixed(digits);
  if (v < 0 && Number(s) !== 0) return MINUS + s;
  return signed && v > 0 ? `+${s}` : s;
}

/** Whether the page shows the deploy aggregates (real/) or the example mock (demo_data). */
export function DataBadge({ source, demo }: { source: Source; demo: boolean }) {
  const real = source === 'real' && !demo;
  return (
    <span className={`h48-badge ${real ? 'is-real' : 'is-demo'}`} title={real ? 'data/real/' : 'data/mock/'}>
      {real ? 'Datos reales (agregados)' : 'Ejemplo'}
    </span>
  );
}

export function Status({ loaded }: { loaded: Loaded<unknown> }) {
  if (loaded.state === 'loading') return <p className="h48-muted" role="status">Cargando datos…</p>;
  if (loaded.state === 'error') return <p className="h48-error" role="alert">No se pudieron cargar los datos: {loaded.message}</p>;
  return null;
}
