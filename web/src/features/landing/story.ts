import { flyPitch, type Family, type Flight, type Vec3 } from '../../physics/flight';
import type { ParksFile, ShapesFile, StaffFile, ValidationFile } from './load';

export type { ParksFile, ShapesFile, StaffFile, ValidationFile };
export type ShapeRow = ShapesFile['shapes'][number];
export type StaffPitcher = StaffFile['franchises'][number]['pitchers'][number];

/** Recta sintética para el dibujo. No es un lanzamiento del archivo ni una cifra del informe. */
export const DEMO_RELEASE = { velo: 94, ivb: 16, hb: 7, family: 'Four-Seam' as Family };

export interface HeroNumbers {
  leagueDelta: number;
  leagueModel: string;
  pitchingSkill: number;
  pitchingSplit: string;
  biasReduction: number;
  biasSplit: string;
  demo: boolean;
  sources: string[];
}

function row(v: ValidationFile, split: string, model: string, metric: string) {
  return v.rows.find((r) => r.split === split && r.model === model && r.metric === metric);
}

/** Cuánto baja el sesgo del modelo respecto al nulo. Positivo = el sesgo se encogió. */
export function biasReduction(baseline: number, model: number): number {
  if (baseline === 0) return 0;
  return (baseline - model) / Math.abs(baseline);
}

export function heroNumbers(v: ValidationFile): HeroNumbers {
  const skill = row(v, 'season_holdout', 'Pitching+', 'skill_vs_baseline');
  const base = row(v, 'park_holdout', 'baseline', 'bias');
  const model = row(v, 'park_holdout', 'Pitching+', 'bias');
  if (!skill || !base || !model) {
    throw new Error('validation.json no trae Skill de Pitching+ ni el sesgo del park holdout');
  }
  return {
    leagueDelta: v.highlights.league_delta_cdmx,
    leagueModel: v.highlights.source_model,
    pitchingSkill: skill.value,
    pitchingSplit: skill.split,
    biasReduction: biasReduction(base.value, model.value),
    biasSplit: base.split,
    demo: v.demo_data,
    sources: v.sources,
  };
}

export function signed(n: number, digits = 1): string {
  const sign = n < 0 ? '−' : n > 0 ? '+' : '';
  return sign + Math.abs(n).toFixed(digits);
}

export function percentFromFraction(fraction: number): string {
  return `${signed(fraction * 100, 1)} %`;
}

export function lowestExtremePark(parks: ParksFile['parks']) {
  const extreme = parks.filter((p) => p.bucket === 'Extreme Altitude');
  const pool = extreme.length > 0 ? extreme : parks;
  return pool.reduce((best, park) => (park.rho < best.rho ? park : best));
}

export function shapeExtremes(shapes: ShapeRow[]) {
  const sorted = [...shapes].sort((a, b) => a.delta_stuff - b.delta_stuff);
  return { loses: sorted[0], resists: sorted[sorted.length - 1] };
}

export function mostContactDamage(shapes: ShapeRow[]) {
  return [...shapes].sort((a, b) => b.delta_contact_runs - a.delta_contact_runs)[0];
}

export function staffSnapshot(staff: StaffFile) {
  return staff.franchises.map((franchise) => {
    const ranked = franchise.pitchers.filter((p) => p.delta_cdmx != null);
    const hurt = [...ranked].sort((a, b) => (a.delta_cdmx ?? 0) - (b.delta_cdmx ?? 0))[0];
    const holds = [...ranked].sort((a, b) => (b.delta_cdmx ?? 0) - (a.delta_cdmx ?? 0))[0];
    return { id: franchise.id, hurt, holds };
  });
}

export function forestScale(shapes: ShapeRow[]) {
  const lo = Math.min(...shapes.map((s) => Math.min(s.delta_lo, s.delta_stuff)), 0);
  const hi = Math.max(...shapes.map((s) => Math.max(s.delta_hi, s.delta_stuff)), 0);
  const span = hi - lo || 1;
  const pct = (value: number) => ((value - lo) / span) * 100;
  return { pct, zero: pct(0) };
}

export function demoFlights(rho: number): { sea: Flight; cdmx: Flight } {
  return {
    sea: flyPitch({ ...DEMO_RELEASE, rho: 1 }),
    cdmx: flyPitch({ ...DEMO_RELEASE, rho }),
  };
}

export function sideView(flight: Flight, step = 10) {
  return flight.pos
    .filter((_, index) => index % step === 0 || index === flight.pos.length - 1)
    .map((point) => ({ dist: point[1], height: point[2], arm: point[0] }));
}

export function toScene(point: Vec3, scale = 0.5): [number, number, number] {
  const plate = 17 / 12;
  return [point[0] * scale, point[2] * scale, -(point[1] - plate) * scale];
}
