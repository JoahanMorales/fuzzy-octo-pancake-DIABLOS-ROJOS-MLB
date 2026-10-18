/* Bullpen logic for /cuerpo-tecnico (HACK-067). Pure functions over the contract documents: every number comes
   from pitcher/<id>.json (HACK-050) or design_lab.json (HACK-033/065); the suggested mix is a model suggestion,
   not a measured effect. */

export interface ArsenalPitch {
  pitch_id: number;
  pitch_family: string;
  shape: string;
  usage: number;
  velo: number;
  stuff_plus: number;
  stuff_plus_harp_helu: number;
  delta_cdmx: number;
}

export interface MixRow {
  pitch: ArsenalPitch;
  current: number;
  suggested: number;
}

export interface MixSuggestion {
  rows: MixRow[];
  moved: number; // share of pitches moved, 0..CAP
  from: ArsenalPitch | null;
  to: ArsenalPitch | null;
  arsenalNow: number; // usage-weighted Stuff+ en CDMX
  arsenalSuggested: number;
}

/** Usage moved at most per suggestion (10 points of usage) and never more than half of the losing pitch. */
export const MIX_CAP = 0.1;
/** Below this gap in ΔStuff+ between the two pitches the current mix is kept. */
export const MIN_GAP = 1.0;

export const FAMILY_ES: Record<string, string> = {
  'Four-Seam': 'Recta de 4 costuras', Sinker: 'Sinker', Cutter: 'Cutter', Slider: 'Slider', Curveball: 'Curva',
  Changeup: 'Cambio', Splitter: 'Splitter',
};

export const pitchName = (p: ArsenalPitch) => {
  const name = FAMILY_ES[p.pitch_family] ?? p.pitch_family;
  return p.shape && p.shape.toLowerCase() !== p.pitch_family.toLowerCase() ? `${name} (${p.shape})` : name;
};

export function weighted(pitches: ArsenalPitch[], usage: number[], key: 'stuff_plus' | 'stuff_plus_harp_helu'): number {
  const total = usage.reduce((a, b) => a + b, 0);
  return total > 0 ? pitches.reduce((t, p, i) => t + p[key] * usage[i], 0) / total : NaN;
}

/** The pitch whose Stuff+ drops most in Harp Helú air. */
export function losesMost(pitches: ArsenalPitch[]): ArsenalPitch | null {
  return pitches.length ? pitches.reduce((w, p) => (p.delta_cdmx < w.delta_cdmx ? p : w)) : null;
}

/** Move usage from the pitch that loses most in CDMX air to a pitch that resists it (loses at least MIN_GAP
 *  points less) and is worth the most in Harp Helú air; capped, and only when the CDMX arsenal improves. */
export function suggestHomeMix(pitches: ArsenalPitch[]): MixSuggestion {
  const current = pitches.map((p) => p.usage);
  const used = pitches.filter((p) => p.usage > 0);
  const from = losesMost(used);
  const resist = from ? used.filter((p) => p !== from && p.delta_cdmx - from.delta_cdmx >= MIN_GAP) : [];
  const to = resist.length ? resist.reduce((b, p) => (p.stuff_plus_harp_helu > b.stuff_plus_harp_helu ? p : b)) : null;
  const shift = (m: number) => pitches.map((p) => p.usage - (p === from ? m : 0) + (p === to ? m : 0));
  const arsenalNow = weighted(pitches, current, 'stuff_plus_harp_helu');
  let moved = from && to ? Math.min(MIX_CAP, from.usage / 2) : 0;
  if (moved > 0 && !(weighted(pitches, shift(moved), 'stuff_plus_harp_helu') > arsenalNow)) moved = 0;
  const suggested = shift(moved);
  return {
    rows: pitches.map((p, i) => ({ pitch: p, current: current[i], suggested: suggested[i] })),
    moved,
    from: moved > 0 ? from : null,
    to: moved > 0 ? to : null,
    arsenalNow,
    arsenalSuggested: weighted(pitches, suggested, 'stuff_plus_harp_helu'),
  };
}

export type PlanRow = [number, string, number, number, number];

/** Best design-lab tweak for this pitcher's latest season (design_lab plan is keyed pitcher_XXXXX_YEAR). */
export function pitchToDevelop(plan: Record<string, PlanRow[]> | null, pitcherId: string, year: number) {
  const rows = plan?.[`${pitcherId}_${year}`];
  if (!rows?.length) return null;
  const [, label, gainHH, gainSea] = [...rows].sort((a, b) => a[0] - b[0])[0];
  return { label, gainHH, gainSea };
}
