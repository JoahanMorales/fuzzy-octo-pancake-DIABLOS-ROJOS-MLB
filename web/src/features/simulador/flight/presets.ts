/**
 * Shape releases whose sea-level movement, scored by the published Stuff+ trees and
 * `physics_translator`, lands within ±1.5 of `reports/altitude_delta/delta_by_shape.csv`
 * at `physics.json` → `rho.harp_helu`. They are representative releases, not league means.
 */
import type { Family } from '../../../physics/flight';
import physics from '../../../physics/physics.json';

export const HARP_RHO = physics.rho.harp_helu;
export const RHO_REF = physics.translator.rho_ref;

export interface Release {
  id: string;
  label: string;
  shape: string | null;
  family: Family;
  velo: number;
  spin: number;
  axis: number;
  ivb: number;
  hb: number;
  height: number;
  side: number;
  extension: number;
  throws: 'R' | 'L';
  fastball: boolean;
  fbVelo: number;
  fbIvb: number;
  fbHb: number;
  /** Where the release came from, shown next to the number. */
  source: string;
}

const FB = { fbVelo: 94, fbIvb: 16, fbHb: 8 };
const BODY = { height: 5.9, side: 1.7, extension: 6.3, throws: 'R' as const };

interface Seed {
  shape: string;
  label: string;
  family: Family;
  velo: number;
  spin: number;
  axis: number;
  ivb: number;
  hb: number;
  fastball?: boolean;
}

const SEEDS: Seed[] = [
  { shape: 'riding 4S', label: 'Recta de ride', family: 'Four-Seam', velo: 95.5, spin: 2450, axis: 185, ivb: 18, hb: -2, fastball: true },
  { shape: '4S', label: 'Recta de cuatro', family: 'Four-Seam', velo: 93, spin: 2250, axis: 200, ivb: 15, hb: 8, fastball: true },
  { shape: 'sweeper', label: 'Sweeper', family: 'Slider', velo: 81, spin: 2700, axis: 280, ivb: 8, hb: -18 },
  { shape: 'slider', label: 'Slider', family: 'Slider', velo: 85, spin: 2500, axis: 250, ivb: 0, hb: -14 },
  { shape: 'gyro slider', label: 'Gyro', family: 'Slider', velo: 86, spin: 2750, axis: 220, ivb: 1, hb: -6 },
  { shape: 'splitter', label: 'Splitter', family: 'Splitter', velo: 86, spin: 1400, axis: 190, ivb: -2, hb: -4 },
  { shape: '12-6 CB', label: 'Curva 12-6', family: 'Curveball', velo: 78, spin: 2700, axis: 20, ivb: -15, hb: 0 },
  { shape: '11-5 CB', label: 'Curva 11-5', family: 'Curveball', velo: 79, spin: 2550, axis: 50, ivb: -9, hb: 2 },
  { shape: 'cutter', label: 'Cutter', family: 'Cutter', velo: 90, spin: 2350, axis: 160, ivb: 15, hb: 4 },
  { shape: 'running 2S', label: 'Dos costuras', family: 'Sinker', velo: 93, spin: 2150, axis: 230, ivb: 12, hb: 16, fastball: true },
  { shape: 'sinking 2S', label: 'Sinker', family: 'Sinker', velo: 92, spin: 2050, axis: 240, ivb: 4, hb: 12, fastball: true },
  { shape: 'changeup', label: 'Cambio', family: 'Changeup', velo: 84, spin: 1750, axis: 220, ivb: 10, hb: 8 },
  { shape: 'power CH', label: 'Cambio de poder', family: 'Changeup', velo: 88, spin: 1850, axis: 210, ivb: 4, hb: 6 },
];

export const SHAPE_PRESETS: Release[] = SEEDS.map((seed) => ({
  id: seed.shape,
  label: seed.label,
  shape: seed.shape,
  family: seed.family,
  velo: seed.velo,
  spin: seed.spin,
  axis: seed.axis,
  ivb: seed.ivb,
  hb: seed.hb,
  ...BODY,
  fastball: Boolean(seed.fastball),
  ...FB,
  source: 'reports/altitude_delta/delta_by_shape.csv',
}));

export const RIDE = SHAPE_PRESETS[0];

interface ArsenalPitch {
  pitch_id: number;
  pitch_family: string;
  shape: string;
  pitches: number;
  velo: number;
  ivb: number;
  hb: number;
  spin: number;
}

interface PitcherFile {
  id: string;
  demo_data?: boolean;
  seasons: { throws: string; arsenal_pitches: ArsenalPitch[] }[];
}

function mostUsed(rows: ArsenalPitch[]): ArsenalPitch {
  return rows.reduce((best, row) => (row.pitches > best.pitches ? row : best));
}

/** Most-used pitch of pitcher_00019 (mock), with his primary fastball as the arsenal reference. */
const STAFF_SNAPSHOT: PitcherFile = {
  id: 'pitcher_00019',
  demo_data: true,
  seasons: [{
    throws: 'Right',
    arsenal_pitches: [
      { pitch_id: 1, pitch_family: 'Sinker', shape: 'running 2S', pitches: 188, velo: 93.944, ivb: 9.758, hb: 11.144, spin: 2340.046 },
      { pitch_id: 4, pitch_family: 'Slider', shape: 'gyro slider', pitches: 232, velo: 85.021, ivb: -0.469, hb: -5.687, spin: 2561.946 },
    ],
  }],
};

export function staffRelease(file: PitcherFile = STAFF_SNAPSHOT): Release {
  const season = file.seasons[file.seasons.length - 1];
  const pitch = mostUsed(season.arsenal_pitches);
  const fastballs = season.arsenal_pitches.filter((row) => row.pitch_family === 'Four-Seam' || row.pitch_family === 'Sinker');
  const fb = fastballs.length ? mostUsed(fastballs) : pitch;
  const fastball = pitch.pitch_family === 'Four-Seam' || pitch.pitch_family === 'Sinker';
  const axis = (Math.atan2(pitch.hb, pitch.ivb) * 180) / Math.PI;
  return {
    id: 'staff',
    label: 'Lanzador del staff',
    shape: null,
    family: pitch.pitch_family as Family,
    velo: pitch.velo,
    spin: pitch.spin,
    axis: (axis + 360) % 360,
    ivb: pitch.ivb,
    hb: pitch.hb,
    ...BODY,
    throws: season.throws === 'Left' ? 'L' : 'R',
    fastball,
    fbVelo: fb.velo,
    fbIvb: fb.ivb,
    fbHb: fb.hb,
    source: file.demo_data === false
      ? `${file.id} · pitch_id ${pitch.pitch_id}`
      : `${file.id} · pitch_id ${pitch.pitch_id} · agregado de ejemplo`,
  };
}

export const STAFF = staffRelease();

export const SHORTCUTS: { id: string; label: string; release: Release }[] = [
  { id: 'ride', label: 'Recta de ride', release: RIDE },
  { id: 'sweeper', label: 'Sweeper', release: SHAPE_PRESETS.find((row) => row.shape === 'sweeper')! },
  { id: 'splitter', label: 'Splitter', release: SHAPE_PRESETS.find((row) => row.shape === 'splitter')! },
  { id: 'staff', label: 'Lanzador del staff', release: STAFF },
];

export function byShape(shape: string): Release | undefined {
  return SHAPE_PRESETS.find((row) => row.shape === shape);
}
