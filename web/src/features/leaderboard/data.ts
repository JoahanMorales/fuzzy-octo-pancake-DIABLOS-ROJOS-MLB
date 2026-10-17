/* Contract loader (HACK-050 rule): read data/real/ when data/real/manifest.json exists, else data/mock/.
   Every document is validated with the HACK-038 schemas; the badge comes from `demo_data`. */
import { useEffect, useState } from 'react';
import { parseContractFile } from '../../contract/types';

export type Source = 'real' | 'mock';
type Fetch = (url: string) => Promise<{ ok: boolean; json: () => Promise<unknown> }>;

const BASE = `${import.meta.env.BASE_URL ?? './'}data/`;
let sourcePromise: Promise<Source> | null = null;

export function resetSourceCache() {
  sourcePromise = null;
}

export function dataSource(fetcher: Fetch = fetch): Promise<Source> {
  if (!sourcePromise) {
    sourcePromise = fetcher(`${BASE}real/manifest.json`)
      .then((r) => (r.ok ? 'real' : 'mock') as Source)
      .catch(() => 'mock' as Source);
  }
  return sourcePromise;
}

export async function loadDoc<T>(rel: string, fetcher: Fetch = fetch): Promise<{ doc: T; source: Source }> {
  const source = await dataSource(fetcher);
  const res = await fetcher(`${BASE}${source}/${rel}`);
  if (!res.ok) throw new Error(`no se encontró ${source}/${rel}`);
  return { doc: parseContractFile(rel, await res.json()) as T, source };
}

export type Loaded<T> =
  | { state: 'loading' }
  | { state: 'error'; message: string }
  | { state: 'ready'; doc: T; source: Source };

export function useDoc<T>(rel: string | null): Loaded<T> {
  const [out, setOut] = useState<Loaded<T>>({ state: 'loading' });
  useEffect(() => {
    if (!rel) return undefined;
    let live = true;
    setOut({ state: 'loading' });
    loadDoc<T>(rel)
      .then(({ doc, source }) => live && setOut({ state: 'ready', doc, source }))
      .catch((e: unknown) => live && setOut({ state: 'error', message: e instanceof Error ? e.message : String(e) }));
    return () => {
      live = false;
    };
  }, [rel]);
  return out;
}

const MINUS = '−';

/** Fixed decimals with a real minus sign (DESIGN.md copy rules). */
export function fmt(v: number, digits = 1, signed = false): string {
  const s = Math.abs(v).toFixed(digits);
  if (v < 0 && Number(s) !== 0) return MINUS + s;
  return signed && v > 0 ? `+${s}` : s;
}
