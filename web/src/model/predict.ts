/**
 * LightGBM tree evaluator for the Stuff+/Location+ composites exported by `stuffplus/export_trees.py` (HACK-040).
 *
 * xRV = Σ_{c<4} P(c)·V(c) + P(in play)·E[rv_x | in play], with P = softmax of the multiclass trees
 * (tree k belongs to class k mod num_class). Plus = center + spread·sign·(xRV − μ_g)/σ_g, μ/σ fitted on the
 * park-neutral (ρ = 1) predictions (stuffplus.scale.PlusScaler). Decisions mirror LightGBM's C++ Tree:
 * numerical NaN becomes 0 unless missing_type is "NaN"; missing values follow default_left; categorical
 * thresholds are "a||b" code sets that go left, and NaN/negative/unseen codes go right. Trees come nested
 * (HACK-038 `tree_structure`) or packed (LightGBM's flat arrays, used by the real export to fit the size budget).
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
}

export type FeatureValue = number | string | boolean | null | undefined;
export type FeatureRow = Record<string, FeatureValue>;

export interface Prediction {
  probs: number[];
  contact: number;
  xrv: number;
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
export function predictEncoded(model: CompositeModel, x: number[]): Prediction {
  const k = model.outcome.num_class;
  const raw = new Array<number>(k).fill(0);
  for (const t of model.outcome.trees) raw[t.tree_index % k] += treeValue(t, x);
  const top = Math.max(...raw);
  const e = raw.map((r) => Math.exp(r - top));
  const sum = e.reduce((a, b) => a + b, 0);
  const probs = e.map((v) => v / sum);
  let contact = 0;
  for (const t of model.contact.trees) contact += treeValue(t, x);
  const values = model.class_values.map((c) => c.rv);
  let xrv = probs[k - 1] * contact;
  for (let c = 0; c < k - 1; c++) xrv += probs[c] * values[c];
  return { probs, contact, xrv };
}

export function predict(model: CompositeModel, row: FeatureRow): Prediction {
  return predictEncoded(model, encode(model, row));
}

/** xRV → Plus on the park-neutral ruler; `group` = values of `plus.by` (e.g. the season), else the LMB reference. */
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
