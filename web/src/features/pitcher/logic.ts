/* Pure pitcher-page logic: movement in two airs (HACK-041 translator) and Stuff+ across the 20 parks. */
import type { z } from 'zod';
import physics from '../../physics/physics.json';
import type { parkSchema, pitcherSchema } from '../../contract/types';

export type PitcherDoc = z.infer<typeof pitcherSchema>;
export type Season = PitcherDoc['seasons'][number];
export type ArsenalPitch = Season['arsenal_pitches'][number];
export type Park = z.infer<typeof parkSchema>;

type Tr = { rho_ref: number; k: Record<string, { ivb: number; hb: number }> };
const TR = physics.translator as Tr;
export const RHO_HH: number = physics.rho.harp_helu;
export const RHO_REF: number = TR.rho_ref;

/** HACK-041 translator: y_to = y * (1 + k (rho_to - rho_from) / (1 + k (rho_from - rho_ref))). */
export function translate(y: number, k: number, rhoFrom: number, rhoTo: number, rhoRef = RHO_REF): number {
  return y * (1 + (k * (rhoTo - rhoFrom)) / (1 + k * (rhoFrom - rhoRef)));
}

export interface Movement {
  pitch: ArsenalPitch;
  sea: { hb: number; ivb: number };
  cdmx: { hb: number; ivb: number };
}

/** A pitch's average movement (observed across parks, taken at the league reference density) in sea-level air
 *  and in Harp Helú air. Families without a translator keep their movement. */
export function movement(p: ArsenalPitch, rhoHH = RHO_HH): Movement {
  const k = TR.k[p.pitch_family];
  const at = (rho: number) =>
    k ? { hb: translate(p.hb, k.hb, RHO_REF, rho), ivb: translate(p.ivb, k.ivb, RHO_REF, rho) } : { hb: p.hb, ivb: p.ivb };
  return { pitch: p, sea: at(1), cdmx: at(rhoHH) };
}

/** Stuff+ at density rho, linear in rho between the neutral value (rho = 1) and the Harp Helú value. */
export function stuffAt(neutral: number, harpHelu: number, rho: number, rhoHH = RHO_HH): number {
  return neutral + ((harpHelu - neutral) * (1 - rho)) / (1 - rhoHH);
}

export function parkCurve(season: Season, parks: Park[]) {
  return [...parks]
    .sort((a, b) => b.rho - a.rho)
    .map((p) => ({ park: p, stuff: stuffAt(season.stuff_plus, season.stuff_plus_harp_helu, p.rho) }));
}

export const FAMILY_LABEL: Record<string, string> = {
  'Four-Seam': 'Recta',
  Sinker: 'Sinker',
  Cutter: 'Cutter',
  Slider: 'Slider',
  Curveball: 'Curva',
  Changeup: 'Cambio',
  Splitter: 'Splitter',
};

export function familyLabel(f: string): string {
  return FAMILY_LABEL[f] ?? f;
}
