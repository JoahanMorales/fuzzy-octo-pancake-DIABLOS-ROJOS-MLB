/**
 * LightGBM tree evaluator for the Stuff+/Location+ composites exported by `stuffplus/export_trees.py` (HACK-040).
 *
 * xRV = Σ_{c<4} P(c)·V(c) + P(in play)·E[rv_x | in play], with P = softmax of the multiclass trees
 * (tree k belongs to class k mod num_class). Plus = center + spread·sign·(xRV − μ_g)/σ_g, μ/σ fitted on the
 * park-neutral (ρ = 1) predictions (stuffplus.scale.PlusScaler). Decisions mirror LightGBM's C++ Tree:
 * numerical NaN becomes 0 unless missing_type is "NaN"; missing values follow default_left; categorical
 * thresholds are "a||b" code sets that go left, and NaN/negative/unseen codes go right. Trees come nested
 * (HACK-038 `tree_structure`) or packed (LightGBM's flat arrays, used by the real export to fit the size budget).
 *
 * Production (HACK-057/066): `calibration.T` rescales the probabilities (softmax(log P / T), stuffplus.calibration
 * Temperature) and Stuff+ v2 carries a `count` block. xRV at a count c = Σ_{k<4} P_k·V_c(k) + P(in play)·contact
 * + offset_c; with `count.value = "count_neutral"` the model's xRV is Σ_c w_f(c)·[xRV(stuff, c) − m_c]
 * (CountNeutral.predict_xrv), so the pitch's own count never moves its Stuff+. Probabilities and contact are at
 * the row's count, exactly like CountNeutral.predict_components.
 */

// Same field names as the HACK-038 contract (`tree_structure`); kept local so this module has no contract import.
export type TreeNode = {
  split_feature?: number;
  threshold?: number | string;
  decision_type?: string;
  default_left?: boolean;
  missing_type?: string;
  left_child?: TreeNode;
  right_child?: TreeNode;
  leaf_value?: number;
};

/** LightGBM's flat layout (export default): child ≥ 0 = internal node, < 0 = leaf ~child; decision bits:
 *  1 categorical, 2 default_left, 4 missing Zero, 8 missing NaN. */
export interface PackedTree {
  split_feature: number[];
  threshold: (number | string)[];
  decision: number[];
  left: number[];
  right: number[];
  leaf_value: number[];
}

export interface BoosterTree {
  tree_index: number;
  tree_structure?: TreeNode;
  packed?: PackedTree;
}

export interface PlusStats {
  mean: number;
  sd: number;
  n?: number;
}

export interface CompositeModel {
  name: string;
  features: string[];
  categories: Record<string, string[]>;
  class_values: { outcome: string; rv: number }[];
  plus: {
    center: number;
    spread: number;
    reference: string;
    sign?: number;
    by?: string[];
    stats?: Record<string, PlusStats>;
  };
  outcome: { num_class: number; trees: BoosterTree[] };
  contact: { trees: BoosterTree[] };
  reference?: Record<string, number>;
  calibration?: { method: string; T: number };
  count?: CountBlock;
}

export interface CountBlock {
  value: 'count_neutral' | 'at_count';
  counts: string[]; // "b-s", the order of every list
  values: number[][]; // [count][outcome] rv_x
  offset: number[];
  mean: number[];
  league_weights: number[];
  family_weights: Record<string, (number | null)[]>;
}

export type FeatureValue = number | string | boolean | null | undefined;
export type FeatureRow = Record<string, FeatureValue>;

export interface Prediction {
  probs: number[];
  contact: number;
  xrv: number; // count-neutral value for production Stuff+ v2, else the composite xRV
  xrvAtCount: number; // xRV at the row's own count (NaN for v2 without Balls/Strikes)
}

const GLOBAL = '__all__';
const ZERO = 1e-35;

/** Feature vector in booster order: categories → code index, unseen or missing → NaN. */
export function encode(model: CompositeModel, row: FeatureRow): number[] {
  return model.features.map((f) => {
    const v = row[f];
    const levels = model.categories[f];
    if (levels) {
      const i = levels.indexOf(String(v));
      return v === null || v === undefined || i < 0 ? NaN : i;
    }
    if (v === null || v === undefined || v === '') return NaN;
    return Number(v);
  });
}

const DEFAULT_LEFT = 2, MISSING_ZERO = 4, MISSING_NAN = 8;
const MISSING_CODE: Record<string, number> = { None: 0, Zero: MISSING_ZERO, NaN: MISSING_NAN };
const catSets = new WeakMap<object, Map<number, Set<number>>>();

function categorySet(owner: object, key: number, threshold: number | string): Set<number> {
  let byKey = catSets.get(owner);
  if (!byKey) catSets.set(owner, (byKey = new Map()));
  let set = byKey.get(key);
  if (!set) byKey.set(key, (set = new Set(String(threshold).split('||').map(Number))));
  return set;
}

function decide(v: number, categorical: boolean, code: number, threshold: number | string, cats: () => Set<number>) {
  if (categorical) return !Number.isNaN(v) && v >= 0 && cats().has(Math.trunc(v));
  if (Number.isNaN(v) && !(code & MISSING_NAN)) v = 0;
  if ((code & MISSING_ZERO && Math.abs(v) <= ZERO) || (code & MISSING_NAN && Number.isNaN(v))) {
    return (code & DEFAULT_LEFT) !== 0;
  }
  return v <= (threshold as number);
}

export function leafValue(root: TreeNode, x: number[]): number {
  let node = root;
  while (node.leaf_value === undefined) {
    const code = (node.default_left ?? true ? DEFAULT_LEFT : 0) | MISSING_CODE[node.missing_type ?? 'None'];
    const n = node;
    const left = decide(x[n.split_feature as number], n.decision_type === '==', code, n.threshold as number | string,
      () => categorySet(n, 0, n.threshold as string));
    node = (left ? node.left_child : node.right_child) as TreeNode;
  }
  return node.leaf_value;
}

export function packedLeafValue(t: PackedTree, x: number[]): number {
  if (t.split_feature.length === 0) return t.leaf_value[0];
  let i = 0;
  for (;;) {
    const code = t.decision[i];
    const node = i;
    const left = decide(x[t.split_feature[i]], (code & 1) === 1, code, t.threshold[i],
      () => categorySet(t, node, t.threshold[node]));
    const next = left ? t.left[i] : t.right[i];
    if (next < 0) return t.leaf_value[~next];
    i = next;
  }
}

function treeValue(t: BoosterTree, x: number[]): number {
  if (t.packed) return packedLeafValue(t.packed, x);
  if (t.tree_structure) return leafValue(t.tree_structure, x);
  throw new Error(`tree ${t.tree_index}: neither packed nor tree_structure`);
}

/** Outcome probabilities, contact value and xRV for one encoded row. */
const EPS = 1e-9; // stuffplus.calibration.EPS

function softmax(z: number[]): number[] {
  const top = Math.max(...z);
  const e = z.map((r) => Math.exp(r - top));
  const sum = e.reduce((a, b) => a + b, 0);
  return e.map((v) => v / sum);
}

/** Calibrated probabilities and contact value for one encoded row. */
function components(model: CompositeModel, x: number[]): { probs: number[]; contact: number } {
  const k = model.outcome.num_class;
  const raw = new Array<number>(k).fill(0);
  for (const t of model.outcome.trees) raw[t.tree_index % k] += treeValue(t, x);
  let probs = softmax(raw);
  if (model.calibration?.method === 'temperature') {
    const T = model.calibration.T;
    probs = softmax(probs.map((p) => Math.log(Math.min(1, Math.max(EPS, p))) / T));
  }
  let contact = 0;
  for (const t of model.contact.trees) contact += treeValue(t, x);
  return { probs, contact };
}

/** stuffplus.models.stuff_v2._count_key: the count is clipped only for the table lookup (trees see the raw value). */
export function countKey(balls: FeatureValue, strikes: FeatureValue): string | null {
  const b = Number(balls), s = Number(strikes);
  if (balls === null || balls === undefined || strikes === null || strikes === undefined) return null;
  if (!Number.isFinite(b) || !Number.isFinite(s)) return null;
  return `${Math.min(Math.max(Math.trunc(b), 0), 3)}-${Math.min(Math.max(Math.trunc(s), 0), 2)}`;
}

function xrvAt(model: CompositeModel, probs: number[], contact: number, key: string | null): number {
  const k = model.outcome.num_class;
  const cb = model.count;
  if (!cb) {
    const values = model.class_values.map((c) => c.rv);
    let xrv = probs[k - 1] * contact;
    for (let c = 0; c < k - 1; c++) xrv += probs[c] * values[c];
    return xrv;
  }
  const j = key === null ? -1 : cb.counts.indexOf(key);
  if (j < 0) return NaN;
  let xrv = probs[k - 1] * contact + cb.offset[j];
  for (let c = 0; c < k - 1; c++) xrv += probs[c] * cb.values[j][c];
  return xrv;
}

/** Count-neutral value Σ_c w_f(c)·[xRV(stuff, c) − m_c] with the family's train count weights (league if unseen). */
export function stuffValue(model: CompositeModel, row: FeatureRow): number {
  const cb = model.count;
  if (!cb) throw new Error(`${model.name}: no count block (not a Stuff+ v2 export)`);
  const fam = cb.family_weights[String(row.pitch_family)];
  const w = fam && fam.every((v) => v !== null && Number.isFinite(v)) ? (fam as number[]) : cb.league_weights;
  let total = 0;
  cb.counts.forEach((key, j) => {
    if (!w[j]) return;
    const [b, s] = key.split('-').map(Number);
    const { probs, contact } = components(model, encode(model, { ...row, Balls: b, Strikes: s }));
    total += w[j] * (xrvAt(model, probs, contact, key) - cb.mean[j]);
  });
  return total;
}

export function predict(model: CompositeModel, row: FeatureRow): Prediction {
  const { probs, contact } = components(model, encode(model, row));
  const xrvAtCount = xrvAt(model, probs, contact, model.count ? countKey(row.Balls, row.Strikes) : null);
  const xrv = model.count?.value === 'count_neutral' ? stuffValue(model, row) : xrvAtCount;
  return { probs, contact, xrv, xrvAtCount };
}

/** Score → Plus on the park-neutral ruler: pass xRV for Stuff+ and `locationValue` (not xRV) for Location+.
 *  `group` = values of `plus.by` (e.g. the season), else the LMB reference. */
export function toPlus(model: CompositeModel, xrv: number, group?: (string | number)[]): number {
  const { center, spread, sign = -1, stats } = model.plus;
  if (!stats?.[GLOBAL]) throw new Error(`${model.name}: plus.stats missing (export with stuffplus/export_trees.py)`);
  const g = (group && stats[group.join('|')]) || stats[GLOBAL];
  return center + spread * sign * ((xrv - g.mean) / g.sd);
}

/** Location+ value: xRV minus the league mean for the same count and pitch family (`reference`). */
export function locationValue(model: CompositeModel, row: FeatureRow, xrv?: number): number {
  const ref = model.reference;
  if (!ref) throw new Error(`${model.name}: no reference table`);
  const value = xrv ?? predict(model, row).xrv;
  const key = `${row.Balls}-${row.Strikes}|${row.pitch_family}`;
  const vals = Object.values(ref);
  return value - (ref[key] ?? vals.reduce((a, b) => a + b, 0) / vals.length);
}

/** Pitching+ export (HACK-079): components + 8 binary target boosters + the HACK-012 sign-constrained combination. */
export interface PitchingModel extends CompositeModel {
  targets: Record<string, { trees: BoosterTree[] }>;
  combination: { intercept: number; weights: Record<string, number> };
  zone: { x: number; z_low: number; z_high: number };
  neutral: {
    batter: Record<string, number>;
    league: Record<string, number>;
    by_family: Record<string, Record<string, number>>;
  };
}

const missing = (v: FeatureValue) => v === null || v === undefined || v === '';

/** Trackman's outside_strike_zone as the export's plate box; no plate location → 0 (as `event_rates`). */
export function outsideZone(model: PitchingModel, row: FeatureRow): number {
  const x = Number(row.plate_x_arm), z = Number(row.PlateLocHeight);
  if (missing(row.plate_x_arm) || missing(row.PlateLocHeight) || !Number.isFinite(x) || !Number.isFinite(z)) return 0;
  const { zone } = model;
  return Math.abs(x) > zone.x || z < zone.z_low || z > zone.z_high ? 1 : 0;
}

/** What a typed pitch cannot say: league-average batter, then the family's training medians (league if unseen). */
export function fillPitchingRow(model: PitchingModel, row: FeatureRow): FeatureRow {
  const fam = model.neutral.by_family[String(row.pitch_family)] ?? {};
  const out: FeatureRow = { ...row, ...model.neutral.batter };
  for (const [f, v] of Object.entries(model.neutral.league)) if (missing(out[f])) out[f] = fam[f] ?? v;
  return out;
}

/** Combined xRV (`PitchingExport.predict_xrv`): rates from the components and targets, then intercept + Σ w·rate. */
export function pitchingXrv(model: PitchingModel, row: FeatureRow): number {
  const x = encode(model, row);
  const { probs, contact } = components(model, x);
  const q: Record<string, number> = {};
  for (const [name, block] of Object.entries(model.targets)) {
    let s = 0;
    for (const t of block.trees) s += treeValue(t, x);
    q[name] = 1 / (1 + Math.exp(-s));
  }
  const pin = probs[model.outcome.num_class - 1];
  const rates: Record<string, number> = {
    whiff_rate: q.swing * q.whiff,
    called_strike_rate: (1 - q.swing) * q.called_strike,
    chase_rate: outsideZone(model, row) * q.chase,
    weak_contact_rate: pin * q.weak_contact,
    groundball_rate: pin * q.groundball,
    hard_contact_rate: pin * q.hard_contact,
    out_in_pa: q.out_in_pa,
    xrv_components: xrvAt(model, probs, contact, null),
  };
  let total = model.combination.intercept;
  for (const [k, w] of Object.entries(model.combination.weights)) total += w * rates[k];
  return total;
}
