/* Recruiting logic for /reclutamiento (HACK-068): league pitcher-seasons outside the Diablos staff, ranked by
   Stuff+ en CDMX among those that lose little in Harp Helú air. Pure functions over leaderboard.json and
   staff.json (HACK-050); the CSV export carries aggregates only. */
import { filterRows, sortRows, type Hand, type Row } from '../leaderboard/logic';

export type { Row };

export interface RecruitFilters {
  year: number | 'all';
  hand: Hand;
  minPitches: number;
  maxLoss: number; // keep pitcher-seasons whose ΔStuff+ CDMX ≥ −maxLoss
  shapes: string[]; // every selected shape must be in the arsenal
}

export const SHORTLIST_MAX = 10;

/** "riding 4S 53% · 4S 20% · gyro slider 17%" → ["riding 4S", "4S", "gyro slider"]. */
export function arsenalShapes(arsenal: string): string[] {
  return arsenal
    .split('·')
    .map((s) => s.trim().replace(/\s+\d+%$/, ''))
    .filter(Boolean);
}

/** Shapes present in the rows, most frequent first. */
export function shapeOptions(rows: Row[]): string[] {
  const n = new Map<string, number>();
  rows.forEach((r) => arsenalShapes(r.arsenal).forEach((s) => n.set(s, (n.get(s) ?? 0) + 1)));
  return [...n.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0])).map(([s]) => s);
}

export function median(xs: number[]): number {
  if (!xs.length) return NaN;
  const s = [...xs].sort((a, b) => a - b);
  const m = Math.floor(s.length / 2);
  return s.length % 2 ? s[m] : (s[m - 1] + s[m]) / 2;
}

/** Candidates: not on the Diablos staff, filtered, ranked by Stuff+ en CDMX (ties: smaller loss). */
export function candidates(rows: Row[], diablos: Set<string>, f: RecruitFilters): Row[] {
  const base = filterRows(rows, { year: f.year, hand: f.hand, minPitches: f.minPitches, query: '' }).filter(
    (r) =>
      !diablos.has(r.pitcher_anon_id) &&
      r.delta_cdmx >= -f.maxLoss &&
      f.shapes.every((s) => arsenalShapes(r.arsenal).includes(s)),
  );
  return sortRows(base, 'stuff_plus_harp_helu');
}

export const rowKey = (r: Row) => `${r.pitcher_anon_id}_${r.year}`;

/** Add or remove a pitcher-season from the shortlist (max SHORTLIST_MAX). */
export function toggleShortlist(list: string[], key: string): string[] {
  if (list.includes(key)) return list.filter((k) => k !== key);
  return list.length >= SHORTLIST_MAX ? list : [...list, key];
}

const CSV_COLUMNS = [
  'pitcher_anon_id', 'year', 'throws', 'pitches', 'stuff_plus', 'stuff_plus_harp_helu', 'delta_cdmx',
  'location_plus', 'pitching_plus', 'arsenal',
] as const;

/** Aggregate-only CSV (one row per pitcher-season; never pitch-level data). */
export function shortlistCsv(rows: Row[]): string {
  const cell = (v: string | number) => {
    const s = String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  return [CSV_COLUMNS.join(','), ...rows.map((r) => CSV_COLUMNS.map((c) => cell(r[c])).join(','))].join('\n') + '\n';
}
