/* Data for the simulator: every number comes from physics.json (HACK-041) or presets.json (synthetic, "ejemplo"). */
import physics from './physics.json';
import presets from './presets.json';
import { fly, type Flight, type Release, type Vec3 } from './flight';

export type Hand = 'R' | 'L';
export type Family = keyof typeof physics.magnus_elasticity;

export interface Pitch {
  id: string;
  family: Family;
  label: string;
  release: Release;
  elasticity: number;
}

export const RHO_HH = physics.rho.harp_helu;
export const RHO_SEA = physics.rho.sea_level;
export const PRESET_NOTE = presets.note;

export const PITCHES: Pitch[] = presets.pitches.map((p) => {
  const family = p.family as Family;
  return {
    id: p.id,
    family,
    label: p.label,
    release: { ...p.release, cd: physics.cd_sea[family] },
    elasticity: physics.magnus_elasticity[family],
  };
});

export interface Throw {
  pitch: Pitch;
  sea: Flight;
  hh: Flight;
  /** Separation of the two plate crossings, inches. */
  plateGapIn: number;
}

export function throwPitch(pitch: Pitch): Throw {
  const sea = fly(pitch.release, RHO_SEA, 1);
  const hh = fly(pitch.release, RHO_HH, pitch.elasticity);
  const plateGapIn = Math.hypot(hh.plate_x - sea.plate_x, hh.plate_z - sea.plate_z) * 12;
  return { pitch, sea, hh, plateGapIn };
}

/** Flight coords (x arm side, y toward the mound, z up; ft) to the scene (x = catcher's right, y up, z toward the
 *  catcher). A right-hander's arm side is the catcher's left. */
export function toWorld(p: Vec3, hand: Hand): Vec3 {
  return [hand === 'R' ? -p[0] : p[0], p[2], -p[1]];
}

const MINUS = '−';
export function fmt(v: number, digits = 1, signed = false): string {
  const s = Math.abs(v).toFixed(digits);
  if (v < 0 && s !== (0).toFixed(digits)) return MINUS + s;
  return signed && v > 0 ? `+${s}` : s;
}
