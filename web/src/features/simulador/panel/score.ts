/**
 * Scores one release in two airs with the published trees (HACK-040) and `physics_translator`.
 * The flight engine draws the ball; it does not move the features the model sees.
 */
import { locationValue, predict, toPlus, type CompositeModel, type FeatureRow, type Prediction } from '../../../model/predict';
import physics from '../../../physics/physics.json';
import { RHO_REF, type Release } from '../flight/presets';

export interface Models {
  stuff: CompositeModel;
  location: CompositeModel;
  demo: boolean;
}

/** The trees stay in `public/data` and are fetched, so the app bundle does not swallow the boosters. */
export async function loadModels(fetchImpl: typeof fetch = fetch): Promise<Models> {
  const base = import.meta.env.BASE_URL;
  const [stuff, location] = await Promise.all([
    fetchImpl(`${base}data/models/stuff.json`).then((res) => {
      if (!res.ok) throw new Error('stuff');
      return res.json() as Promise<CompositeModel & { demo_data?: boolean }>;
    }),
    fetchImpl(`${base}data/models/location.json`).then((res) => {
      if (!res.ok) throw new Error('location');
      return res.json() as Promise<CompositeModel & { demo_data?: boolean }>;
    }),
  ]);
  return {
    stuff,
    location,
    demo: stuff.demo_data !== false || location.demo_data !== false,
  };
}

const K = physics.translator.k;
const FB_FAMILY = 'Four-Seam';

export function proportionalShift(y: number, k: number, rhoFrom: number, rhoTo: number, rhoRef = RHO_REF): number {
  return y * (1 + k * (rhoTo - rhoFrom) / (1 + k * (rhoFrom - rhoRef)));
}

export function seaRow(release: Release): FeatureRow {
  const axis = release.throws === 'R' ? release.axis : (360 - release.axis) % 360;
  const ivbDiff = release.fastball ? 0 : release.ivb - release.fbIvb;
  const hbDiff = release.fastball ? 0 : release.hb - release.fbHb;
  return {
    RelSpeed: release.velo,
    SpinRate: release.spin,
    spin_axis_arm: axis,
    InducedVertBreak: release.ivb,
    hb_arm: release.hb,
    RelHeight: release.height,
    rel_side_arm: release.side,
    Extension: release.extension,
    arm_angle: (Math.atan2(release.height - 5, Math.abs(release.side)) * 180) / Math.PI,
    is_rhp: release.throws === 'R' ? 1 : 0,
    pitch_family: release.family,
    rho: 1,
    velo_diff_fb: release.fastball ? 0 : release.velo - release.fbVelo,
    ivb_diff_fb: ivbDiff,
    hb_diff_fb: hbDiff,
  };
}

/** Move IVB, arm-side HB and the fastball diffs from `rhoFrom` to `rhoTo`. The four-seam k shifts the primary fastball. */
export function translateRow(row: FeatureRow, rhoTo: number, rhoFrom = 1): FeatureRow {
  const family = String(row.pitch_family);
  const kk = K[family as keyof typeof K] ?? K[FB_FAMILY];
  const fb = K[FB_FAMILY];
  const ivb = Number(row.InducedVertBreak);
  const hb = Number(row.hb_arm);
  const ivbDiff = Number(row.ivb_diff_fb);
  const hbDiff = Number(row.hb_diff_fb);
  const newIvb = proportionalShift(ivb, kk.ivb, rhoFrom, rhoTo);
  const newHb = proportionalShift(hb, kk.hb, rhoFrom, rhoTo);
  return {
    ...row,
    InducedVertBreak: newIvb,
    hb_arm: newHb,
    ivb_diff_fb: newIvb - proportionalShift(ivb - ivbDiff, fb.ivb, rhoFrom, rhoTo),
    hb_diff_fb: newHb - proportionalShift(hb - hbDiff, fb.hb, rhoFrom, rhoTo),
    rho: rhoTo,
  };
}

export interface SideScore {
  stuff: number;
  location: number;
  /** Pitching+ model is not in the export; serving uses Stuff+ until `models/pitching.json` exists. */
  pitching: number;
  pitchingSource: 'stuff-fallback';
  pred: Prediction;
  ivb: number;
  hb: number;
}

export interface PairScore {
  sea: SideScore;
  park: SideScore;
  deltaStuff: number;
  demo: boolean;
}

export interface ScoreContext {
  balls: number;
  strikes: number;
  batter: 'R' | 'L';
  plateSea: { x: number; z: number };
  platePark: { x: number; z: number };
}

function plusOf(model: CompositeModel, xrv: number): number {
  return toPlus(model, xrv);
}

function side(
  models: Models,
  row: FeatureRow,
  release: Release,
  plate: { x: number; z: number },
  ctx: ScoreContext,
): SideScore {
  const pred = predict(models.stuff, row);
  const locRow: FeatureRow = {
    plate_x_arm: plate.x,
    PlateLocHeight: plate.z,
    Balls: ctx.balls,
    Strikes: ctx.strikes,
    same_side: ctx.batter === release.throws ? 1 : 0,
    is_rhp: release.throws === 'R' ? 1 : 0,
    pitch_family: release.family,
    rho: row.rho,
  };
  const loc = predict(models.location, locRow);
  return {
    stuff: plusOf(models.stuff, pred.xrv),
    location: plusOf(models.location, locationValue(models.location, locRow, loc.xrv)),
    pitching: plusOf(models.stuff, pred.xrv),
    pitchingSource: 'stuff-fallback',
    pred,
    ivb: Number(row.InducedVertBreak),
    hb: Number(row.hb_arm),
  };
}

const NEUTRAL_PLATE = { x: 0, z: 2.5 };
const NEUTRAL_CTX: ScoreContext = { balls: 0, strikes: 0, batter: 'R', plateSea: NEUTRAL_PLATE, platePark: NEUTRAL_PLATE };

/** Stuff+ at sea level and at `rho`, plus Location+ if a context is passed. */
export function scoreRelease(release: Release, rho: number, models: Models, ctx: ScoreContext = NEUTRAL_CTX): PairScore {
  const seaRowRaw = seaRow(release);
  const parkRow = translateRow(seaRowRaw, rho, 1);
  return finish(models, release, seaRowRaw, parkRow, ctx);
}

export function stuffDelta(release: Release, rho: number, models: Models): number {
  return scoreRelease(release, rho, models).deltaStuff;
}

function finish(models: Models, release: Release, seaRowRaw: FeatureRow, parkRow: FeatureRow, ctx: ScoreContext): PairScore {
  const sea = side(models, seaRowRaw, release, ctx.plateSea, ctx);
  const park = side(models, parkRow, release, ctx.platePark, ctx);
  return { sea, park, deltaStuff: park.stuff - sea.stuff, demo: models.demo };
}

export const OUTCOME_LABEL = ['bola', 'strike cantado', 'whiff', 'foul', 'en juego'] as const;

export function whyLines(pair: PairScore): { label: string; delta: string }[] {
  const lines: { label: string; delta: string }[] = OUTCOME_LABEL.map((label, i) => ({
    label,
    delta: pp(pair.park.pred.probs[i] - pair.sea.pred.probs[i]),
  }));
  lines.push({
    label: 'contacto',
    delta: `${signed(pair.park.pred.contact - pair.sea.pred.contact, 3)} carreras`,
  });
  lines.push({
    label: 'IVB traducido',
    delta: `${signed(pair.park.ivb - pair.sea.ivb, 1)} in`,
  });
  lines.push({
    label: 'HB traducido',
    delta: `${signed(pair.park.hb - pair.sea.hb, 1)} in`,
  });
  return lines;
}

function signed(n: number, digits: number): string {
  const body = Math.abs(n).toFixed(digits);
  return n >= 0 ? `+${body}` : `−${body}`;
}

function pp(fraction: number): string {
  return `${signed(fraction * 100, 1)} pp`;
}
