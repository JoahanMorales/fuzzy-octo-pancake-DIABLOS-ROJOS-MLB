/* Pure leaderboard logic: filters, sorting and the text conclusion beside the table. */
import type { z } from 'zod';
import type { leaderboardRowSchema, leaderboardSchema } from '../../contract/types';

export type Row = z.infer<typeof leaderboardRowSchema>;
export type Board = z.infer<typeof leaderboardSchema>;
export type Flavour = 'neutral' | 'cdmx';
export type Hand = 'all' | 'Right' | 'Left';
export type SortKey = 'stuff_plus' | 'stuff_plus_harp_helu' | 'delta_cdmx' | 'location_plus' | 'pitching_plus' | 'pitches';

export interface Filters {
  year: number | 'all';
  hand: Hand;
  minPitches: number;
  query: string;
}

export const FLAVOUR_KEY: Record<Flavour, SortKey> = { neutral: 'stuff_plus', cdmx: 'stuff_plus_harp_helu' };

export function years(rows: Row[]): number[] {
  return [...new Set(rows.map((r) => r.year))].sort((a, b) => b - a);
}

export function filterRows(rows: Row[], f: Filters): Row[] {
  const q = f.query.trim().toLowerCase();
  return rows.filter(
    (r) =>
      (f.year === 'all' || r.year === f.year) &&
      (f.hand === 'all' || r.throws === f.hand) &&
      r.pitches >= f.minPitches &&
      (!q || r.pitcher_anon_id.toLowerCase().includes(q) || r.arsenal.toLowerCase().includes(q)),
  );
}

/** Descending by default; ties broken by pitches then id so the order is stable. */
export function sortRows(rows: Row[], key: SortKey, dir: 'desc' | 'asc' = 'desc'): Row[] {
  const s = dir === 'desc' ? -1 : 1;
  return [...rows].sort(
    (a, b) => s * (a[key] - b[key]) || b.pitches - a.pitches || a.pitcher_anon_id.localeCompare(b.pitcher_anon_id),
  );
}

export interface Summary {
  n: number;
  meanDelta: number; // pitch-weighted ΔStuff+ CDMX
  losingShare: number; // share of pitcher-seasons with ΔStuff+ CDMX < 0
  best: Row | null; // smallest loss (largest ΔCDMX)
}

export function summarize(rows: Row[]): Summary {
  if (!rows.length) return { n: 0, meanDelta: 0, losingShare: 0, best: null };
  const w = rows.reduce((t, r) => t + r.pitches, 0);
  const meanDelta = rows.reduce((t, r) => t + r.delta_cdmx * r.pitches, 0) / w;
  const losing = rows.filter((r) => r.delta_cdmx < 0).length / rows.length;
  const best = rows.reduce((b, r) => (r.delta_cdmx > b.delta_cdmx ? r : b), rows[0]);
  return { n: rows.length, meanDelta, losingShare: losing, best };
}

export function handLabel(throws: string): string {
  return throws === 'Right' ? 'Derecho' : throws === 'Left' ? 'Zurdo' : throws;
}
