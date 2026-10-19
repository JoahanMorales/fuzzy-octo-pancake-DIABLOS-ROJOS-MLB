"""Tree models for the browser: the production Stuff+/Location+ models as contract JSON (HACK-040, HACK-066).

A composite is a LightGBM multiclass booster (5 pitch outcomes) + a contact regressor (E[rv_x | in play]) + the
LMB value of each outcome + the Plus scaler fitted on the park-neutral (ρ = 1) predictions. Production (HACK-057,
HACK-066) adds the temperature calibrator (``calibration.T``: P → softmax(log P / T)) and, for Stuff+ v2, the
``count`` block: per-count outcome values, offsets, means and the family/league count weights, so the browser
computes the count-neutral value Σ_c w_f(c)·[xRV(stuff, c) − m_c] exactly like ``CountNeutral.predict_xrv``. ``web/src/model/
predict.ts`` evaluates the same trees; parity goldens are synthetic (conftest generator + random vectors).

Trees keep only what evaluation needs. ``nested`` = HACK-038 ``tree_structure`` (``missing_type``/``default_left``
omitted when they equal LightGBM's defaults). ``packed`` (default, the real export) = LightGBM's own flat layout,
because nested JSON of the paper composites is 41 MB against a 15 MB budget: per tree, arrays over internal nodes
``split_feature``, ``threshold``, ``decision`` (bit 1 categorical, 2 default_left, 4 missing Zero, 8 missing NaN),
``left``/``right`` (child ≥ 0 = internal node, < 0 = leaf ``~child``) and ``leaf_value`` (10 significant digits;
thresholds are never rounded). Parity to 1e-6 is checked in tests and vitest.

    python -m stuffplus.export_trees            # real data: refit the paper composites, write web/public/data/models/
    python -m stuffplus.export_trees --fast     # fewer rounds (smoke)
    python -m stuffplus.export_trees --golden   # synthetic parity goldens for vitest (web/src/model/fixtures/)
"""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Sequence

import numpy as np
import pandas as pd

from stuffplus import config
from stuffplus.models.stuff import OUTCOMES, StuffModel
from stuffplus.scale import PlusScaler

MODELS_DIR = config.repo_root() / "web" / "public" / "data" / "models"
FIXTURES_DIR = config.repo_root() / "web" / "src" / "model" / "fixtures"
MODEL_LABEL = "pitch_family Stuff+ composite"
SIZE_BUDGET_MB = 20.0  # models/ inside the 25 MB web build (scripts/check_web_dist.py)
_NODE_KEYS = ("split_feature", "threshold", "decision_type")


def strip_tree(node: dict) -> dict:
    """Contract node with only the fields evaluation needs."""
    if "leaf_value" in node:
        return {"leaf_value": float(node["leaf_value"])}
    out = {k: node[k] for k in _NODE_KEYS}
    if node.get("missing_type", "None") != "None":
        out["missing_type"] = node["missing_type"]
    if not node.get("default_left", True):
        out["default_left"] = False
    out["left_child"] = strip_tree(node["left_child"])
    out["right_child"] = strip_tree(node["right_child"])
    return out


LEAF_DIGITS = 10
_MISSING = {"None": 0, "Zero": 4, "NaN": 8}


def pack_tree(root: dict) -> dict:
    """LightGBM-style flat arrays for one tree (see module docstring)."""
    out = {k: [] for k in ("split_feature", "threshold", "decision", "left", "right", "leaf_value")}

    def go(n: dict) -> int:
        if "leaf_value" in n:
            out["leaf_value"].append(float(f"{n['leaf_value']:.{LEAF_DIGITS}g}"))
            return ~(len(out["leaf_value"]) - 1)
        i = len(out["split_feature"])
        out["split_feature"].append(int(n["split_feature"]))
        cat = n["decision_type"] == "=="
        out["threshold"].append(str(n["threshold"]) if cat else float(n["threshold"]))
        out["decision"].append(int(cat) | (2 if n.get("default_left", True) else 0) | _MISSING[n.get("missing_type", "None")])
        out["left"].append(0)
        out["right"].append(0)
        out["left"][i] = go(n["left_child"])
        out["right"][i] = go(n["right_child"])
        return i

    go(root)
    return out


def unpack_tree(t: dict) -> dict:
    """Packed arrays → nested contract node (used by the reference evaluator)."""
    def node(c: int) -> dict:
        if c < 0:
            return {"leaf_value": t["leaf_value"][~c]}
        code = t["decision"][c]
        n = {"split_feature": t["split_feature"][c], "threshold": t["threshold"][c],
             "decision_type": "==" if code & 1 else "<=", "default_left": bool(code & 2),
             "missing_type": "NaN" if code & 8 else ("Zero" if code & 4 else "None")}
        n["left_child"], n["right_child"] = node(t["left"][c]), node(t["right"][c])
        return n

    return node(0 if t["split_feature"] else -1)


def dump_trees(booster, packed: bool = True) -> list[dict]:
    trees = []
    for t in booster.dump_model()["tree_info"]:
        root = strip_tree(t["tree_structure"])
        trees.append({"tree_index": int(t["tree_index"]), **({"packed": pack_tree(root)} if packed
                                                             else {"tree_structure": root})})
    return trees


def _root(t: dict) -> dict:
    return unpack_tree(t["packed"]) if "packed" in t else t["tree_structure"]


def categories_of(booster, features: Sequence[str]) -> dict[str, list[str]]:
    """Category levels in the booster's own code order (pandas_categorical follows the categorical features)."""
    cats = booster.pandas_categorical or []
    cat_features = [f for f in features if f in ("pitch_family", "AutoPitchType")]
    return {f: [str(c) for c in levels] for f, levels in zip(cat_features, cats)}


EPS = 1e-9  # stuffplus.calibration.EPS


def _base(model):
    """The fitted (possibly calibrated) booster model behind a production wrapper."""
    return getattr(model, "model", model) if type(model).__name__ == "CountNeutral" else model


def _calibration(base) -> dict | None:
    cal = getattr(base, "_calibrator", None)
    if cal is None or type(cal).__name__ == "Identity":
        return None
    if type(cal).__name__ != "Temperature":
        raise NotImplementedError(f"the browser only evaluates temperature calibration, got {type(cal).__name__}")
    return {"method": "temperature", "T": float(cal.T)}


def _count_block(base, count_neutral: bool) -> dict | None:
    if getattr(base, "count_values", None) is None:
        return None
    counts = [str(c) for c in base.count_values.index]
    fw = base.family_weights.reindex(columns=counts) if base.family_weights is not None else None
    return {
        "value": "count_neutral" if count_neutral else "at_count",
        "counts": counts,  # "b-s", the order of every list below
        "values": base.count_values.reindex(index=counts).to_numpy(float).tolist(),  # [count][outcome]
        "offset": base.count_offset.reindex(counts).to_numpy(float).tolist(),
        "mean": base.count_mean.reindex(counts).to_numpy(float).tolist(),
        "league_weights": base.league_weights.reindex(counts).to_numpy(float).tolist(),
        "family_weights": {str(f): row.tolist() for f, row in fw.iterrows()} if fw is not None else {},
    }


def export_composite(model, scaler: PlusScaler, name: str, *, model_version: str,
                     sources: Sequence[str], demo_data: bool, reference: pd.Series | None = None,
                     packed: bool = True) -> dict:
    """Contract payload for one model (``reference``: Location+ league mean xRV by ``count|pitch_family``).
    ``model`` is a StuffModel (v1), a calibrated LocationModel or a production ``CountNeutral`` Stuff+ v2."""
    count_neutral = type(model).__name__ == "CountNeutral"
    model = _base(model)
    features = list(model.features)
    payload = {
        "model_version": model_version, "model": MODEL_LABEL, "translation": "physics_translator",
        "demo_data": bool(demo_data), "sources": list(sources), "name": name, "features": features,
        "categories": categories_of(model.classifier, features),
        "class_values": [{"outcome": o, "rv": float(model.class_values.get(i, 0.0))} for i, o in enumerate(OUTCOMES)],
        "plus": {"center": scaler.center, "spread": scaler.spread, "reference": "park-neutral", "sign": scaler.sign,
                 "by": list(scaler.by), "stats": scaler.stats},
        "outcome": {"num_class": len(OUTCOMES), "trees": dump_trees(model.classifier, packed)},
        "contact": {"trees": dump_trees(model.contact, packed)},
    }
    cal = _calibration(model)
    if cal is not None:
        payload["calibration"] = cal
    count = _count_block(model, count_neutral)
    if count is not None:
        payload["count"] = count
    if reference is not None:
        payload["reference"] = {str(k): float(v) for k, v in reference.items()}
    return payload


def write_json(payload, path: Path) -> float:
    """Minified JSON (NaN → null); returns the size in MB."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_nan_to_none(payload), separators=(",", ":"), allow_nan=False), encoding="utf-8")
    return path.stat().st_size / 1e6


def _nan_to_none(x):
    if isinstance(x, float) and math.isnan(x):
        return None
    if isinstance(x, dict):
        return {k: _nan_to_none(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_nan_to_none(v) for v in x]
    return x


# ---- pure-Python evaluator of the exported JSON (the reference the TypeScript port mirrors) ----

def _leaf(node: dict, row: Sequence[float]) -> float:
    while "leaf_value" not in node:
        v = row[node["split_feature"]]
        if node["decision_type"] == "==":
            go_left = (not math.isnan(v) and v >= 0
                       and int(v) in {int(c) for c in str(node["threshold"]).split("||")})
        else:
            mt = node.get("missing_type", "None")
            if math.isnan(v) and mt != "NaN":
                v = 0.0
            if (mt == "Zero" and abs(v) <= 1e-35) or (mt == "NaN" and math.isnan(v)):
                go_left = node.get("default_left", True)
            else:
                go_left = v <= node["threshold"]
        node = node["left_child"] if go_left else node["right_child"]
    return node["leaf_value"]


def encode(payload: dict, rows: pd.DataFrame) -> np.ndarray:
    """Feature matrix as the evaluator sees it: categories → their code, unseen/missing → NaN."""
    cols = []
    for f in payload["features"]:
        if f in payload["categories"]:
            codes = {c: i for i, c in enumerate(payload["categories"][f])}
            cols.append(rows[f].map(lambda s: codes.get(str(s), np.nan)).to_numpy(float) if f in rows
                        else np.full(len(rows), np.nan))
        else:
            cols.append(pd.to_numeric(rows[f], errors="coerce").to_numpy(float) if f in rows
                        else np.full(len(rows), np.nan))
    return np.column_stack(cols)


def _softmax(z: np.ndarray) -> np.ndarray:
    e = np.exp(z - z.max(axis=1, keepdims=True))
    return e / e.sum(axis=1, keepdims=True)


def _components(payload: dict, rows: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Calibrated outcome probabilities and contact value at the rows' own features."""
    X = encode(payload, rows)
    k = payload["outcome"]["num_class"]
    raw = np.zeros((len(X), k))
    for t in payload["outcome"]["trees"]:
        root = _root(t)
        raw[:, t["tree_index"] % k] += [_leaf(root, r) for r in X]
    p = _softmax(raw)
    cal = payload.get("calibration")
    if cal and cal["method"] == "temperature":
        p = _softmax(np.log(np.clip(p, EPS, 1.0)) / cal["T"])
    contact = np.zeros(len(X))
    for t in payload["contact"]["trees"]:
        root = _root(t)
        contact += [_leaf(root, r) for r in X]
    return p, contact


def _count_keys(rows: pd.DataFrame) -> list[str | None]:
    """stuffplus.models.stuff_v2._count_key: clipped only for the table lookup (trees see the raw count)."""
    if "Balls" not in rows or "Strikes" not in rows:
        return [None] * len(rows)  # no count: components only; the count-neutral value does not need it
    b, s = pd.to_numeric(rows["Balls"], errors="coerce"), pd.to_numeric(rows["Strikes"], errors="coerce")
    return [None if (pd.isna(x) or pd.isna(y)) else f"{min(max(int(x), 0), 3)}-{min(max(int(y), 0), 2)}"
            for x, y in zip(b, s)]


def _xrv_at(payload: dict, p: np.ndarray, contact: np.ndarray, keys) -> np.ndarray:
    v = np.array([c["rv"] for c in payload["class_values"]])
    cb = payload.get("count")
    if cb is None:
        return p[:, :4] @ v[:4] + p[:, 4] * contact
    idx = {c: i for i, c in enumerate(cb["counts"])}
    values, offset = np.array(cb["values"], float), np.array(cb["offset"], float)
    out = np.full(len(p), np.nan)
    for r, key in enumerate(keys):
        if key is not None:
            j = idx[key]
            out[r] = p[r, :4] @ values[j, :4] + p[r, 4] * contact[r] + offset[j]
    return out


def stuff_value(payload: dict, rows: pd.DataFrame) -> np.ndarray:
    """Count-neutral value Σ_c w_f(c)·[xRV(stuff, c) − m_c] (StuffV2Model.stuff_value, family weights)."""
    cb = payload["count"]
    league = np.array(cb["league_weights"], float)
    fams = rows["pitch_family"].astype(str) if "pitch_family" in rows else pd.Series([""] * len(rows))
    W = np.array([cb["family_weights"].get(f, league) for f in fams], float)
    W[np.isnan(W).any(axis=1)] = league
    out = np.zeros(len(rows))
    for j, key in enumerate(cb["counts"]):
        if not W[:, j].any():
            continue
        b, s = (int(x) for x in key.split("-"))
        at = rows.assign(Balls=b, Strikes=s)
        p, contact = _components(payload, at)
        out += W[:, j] * (_xrv_at(payload, p, contact, [key] * len(at)) - cb["mean"][j])
    return out


def evaluate(payload: dict, rows: pd.DataFrame) -> pd.DataFrame:
    """Components at the rows' own count; ``xrv`` is the count-neutral value for production Stuff+ v2
    (``CountNeutral``), else the composite xRV (``xrv_at_count`` is always the latter)."""
    p, contact = _components(payload, rows)
    out = pd.DataFrame(p, columns=[f"p_{o}" for o in OUTCOMES])
    out["contact_rv"] = contact
    keys = _count_keys(rows) if "count" in payload else None
    out["xrv_at_count"] = _xrv_at(payload, p, contact, keys)
    count_neutral = payload.get("count", {}).get("value") == "count_neutral"
    out["xrv"] = stuff_value(payload, rows) if count_neutral else out["xrv_at_count"]
    return out


# ---- fitting ----

def fit_stuff(d: pd.DataFrame, translate, k_inner: int = 3, **rounds):
    """Production Stuff+ (HACK-057: v2 count-neutral value + temperature) and its park-neutral scaler."""
    from stuffplus.models.stuff import fit_production_stuff

    m = fit_production_stuff(d, translate=translate, k_inner=k_inner, **rounds)
    sc = PlusScaler().fit(d.assign(x=m.predict_at_rho(d, 1.0)["xrv"].to_numpy()), "x")
    return m, sc


def fit_location(d: pd.DataFrame, k_inner: int = 3, **rounds):
    """Production Location+ (temperature; reference recomputed on calibrated predictions) and its scaler."""
    from stuffplus.models.location import fit_production_location

    m = fit_production_location(d, k_inner=k_inner, **rounds)
    sc = PlusScaler().fit(d.assign(x=m.location_value(d)), "x")
    return m, sc


# ---- Pitching+ (HACK-079): HACK-012 components + 8 target boosters + sign-constrained combination ----

# features the simulator panel cannot supply: filled with the training median of the pitch family (league if unseen)
PANEL_FILL = ["spin_diff_vs_fb", "axis_diff_vs_fb", "pitch_usage_pct", "arsenal_size", "tunnel_ratio",
              "decision_sep_vs_fb", "release_dist_vs_fb", "Outs", "inning_capped", "times_through_order",
              "pitch_number_in_pa", "prev_velo_diff", "prev_loc_diff"]
# production is 300/200/200 (13.7 MB of trees); the browser copy keeps fewer rounds so the build stays under 25 MB
PITCHING_ROUNDS = dict(class_rounds=70, contact_rounds=100, target_rounds=40)


class PitchingExport:
    """The fitted Pitching+ pieces the browser needs; ``predict_xrv`` is the Python reference for the goldens."""

    def __init__(self, components, targets: dict, combiner, batter: dict, zone: dict, features: Sequence[str]):
        self.components, self.targets, self.combiner = components, targets, combiner
        self.batter, self.zone, self.features = batter, zone, list(features)

    def rates(self, rows: pd.DataFrame) -> pd.DataFrame:
        from stuffplus.models import multitarget as mt

        comps = self.components.predict_components(rows)
        probs = mt.predict_targets(self.targets, rows, self.features)
        zoned = rows.assign(outside_strike_zone=outside_zone(rows, self.zone))
        return mt.event_rates(probs, zoned, comps["p_in_play"].to_numpy(float), comps["xrv"].to_numpy(float))

    def predict_xrv(self, rows: pd.DataFrame) -> np.ndarray:
        return self.combiner.predict(self.rates(rows))


def outside_zone(rows: pd.DataFrame, zone: dict) -> np.ndarray:
    """Trackman's outside_strike_zone as a box on the plate (feet); the panel only knows the plate location."""
    x = pd.to_numeric(rows["plate_x_arm"], errors="coerce").abs().to_numpy(float)
    z = pd.to_numeric(rows["PlateLocHeight"], errors="coerce").to_numpy(float)
    out = (x > zone["x"]) | (z < zone["z_low"]) | (z > zone["z_high"])
    return np.where(np.isnan(x) | np.isnan(z), 0.0, out.astype(float))


def zone_box(d: pd.DataFrame) -> dict:
    """The box of pitches Trackman flags inside the zone (matches the flag on ~99 % of LMB pitches)."""
    ins = d[d["outside_strike_zone"].astype(float).eq(0.0)]
    return {"x": float(ins["PlateLocSide"].abs().max()), "z_low": float(ins["PlateLocHeight"].min()),
            "z_high": float(ins["PlateLocHeight"].max())}


def fit_pitching(pf: pd.DataFrame, k: int = 5, class_rounds: int = 300, contact_rounds: int = 200,
                 target_rounds: int = 200) -> tuple[PitchingExport, PlusScaler]:
    """Production Pitching+: combination weights fitted on out-of-fold rates (``combine()['final']``), boosters
    refitted on every pitch with the actual batters, Plus scaler on the league-average-batter xRV in the pitch's own
    air (``score.score_pitches``). ``pf`` = ``models.pitching.build_features`` output."""
    from stuffplus import splits
    from stuffplus.models import multitarget as mt
    from stuffplus.models.pitching import PITCHING_FEATURES, PitchingComponents, batter_table, run_oof, with_batter

    folds = list(splits.pitcher_group_kfold(pf, k=k))
    oof = run_oof(pf, folds, class_rounds=class_rounds, contact_rounds=contact_rounds, target_rounds=target_rounds)
    combiner = mt.Combiner().fit(oof["rates"], pf["rv_x"].to_numpy(float))
    tab, mu = batter_table(pf)
    train = with_batter(pf, tab, mu)
    pc = PitchingComponents(class_rounds=class_rounds, contact_rounds=contact_rounds).fit(train)
    targets = mt.fit_targets(train, PITCHING_FEATURES, rounds=target_rounds)
    m = PitchingExport(pc, targets, combiner, mu, zone_box(pf), PITCHING_FEATURES)
    sc = PlusScaler().fit(pf.assign(x=m.predict_xrv(with_batter(pf, tab, mu, neutral=True))), "x")
    return m, sc


def with_batters(pf: pd.DataFrame) -> pd.DataFrame:
    """``pf`` with each pitch's shrunk batter-season quality (the rows the boosters were trained on)."""
    from stuffplus.models.pitching import batter_table, with_batter

    return with_batter(pf, *batter_table(pf))


def panel_fill(pf: pd.DataFrame) -> dict:
    """Training medians of PANEL_FILL, league-wide and by pitch family."""
    med = pf[PANEL_FILL].median()
    by = pf.groupby(pf["pitch_family"].astype(str), observed=True)[PANEL_FILL].median()
    return {"league": {f: float(med[f]) for f in PANEL_FILL},
            "by_family": {fam: {f: float(v) for f, v in row.items() if pd.notna(v)} for fam, row in by.iterrows()}}


def export_pitching(m: PitchingExport, scaler: PlusScaler, *, model_version: str, sources: Sequence[str],
                    demo_data: bool, fill: dict | None = None, packed: bool = True) -> dict:
    """``export_composite`` of the components + the 8 target boosters (binary: sigmoid of the tree sum), the
    combination (intercept + rate weights), the zone box, the league-average batter and the panel fill."""
    from stuffplus.models import multitarget as mt

    payload = export_composite(m.components, scaler, "pitching", model_version=model_version, sources=sources,
                               demo_data=demo_data, packed=packed)
    payload["targets"] = {t[2:]: {"trees": dump_trees(m.targets[t], packed)} for t in mt.TARGETS}
    payload["combination"] = {"intercept": float(m.combiner.intercept),
                              "weights": {k: float(v) for k, v in m.combiner.weights.items()}}
    payload["zone"] = dict(m.zone)
    payload["neutral"] = {"batter": {k: float(v) for k, v in m.batter.items()},
                          **(fill or {"league": {}, "by_family": {}})}
    return payload


def _sigmoid(z: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-z))


def evaluate_pitching(payload: dict, rows: pd.DataFrame) -> np.ndarray:
    """Combined xRV from the JSON alone (the rows carry every feature; filling is the panel's job)."""
    p, contact = _components(payload, rows)
    v = np.array([c["rv"] for c in payload["class_values"]])
    xrv_c = p[:, :4] @ v[:4] + p[:, 4] * contact
    X = encode(payload, rows)
    q = {name: _sigmoid(np.array([sum(_leaf(_root(t), r) for t in block["trees"]) for r in X]))
         for name, block in payload["targets"].items()}
    pin = p[:, 4]
    rates = {"whiff_rate": q["swing"] * q["whiff"], "called_strike_rate": (1 - q["swing"]) * q["called_strike"],
             "chase_rate": outside_zone(rows, payload["zone"]) * q["chase"], "weak_contact_rate": pin * q["weak_contact"],
             "groundball_rate": pin * q["groundball"], "hard_contact_rate": pin * q["hard_contact"],
             "out_in_pa": q["out_in_pa"], "xrv_components": xrv_c}
    comb = payload["combination"]
    return comb["intercept"] + sum(w * rates[k] for k, w in comb["weights"].items())


def pitching_golden(m: PitchingExport, rows: pd.DataFrame) -> dict:
    recs = rows.astype(object).where(rows.notna(), None).to_dict(orient="records")
    return {"rows": recs, "xrv": np.asarray(m.predict_xrv(rows), float).tolist()}


def fidelity(m: PitchingExport, sc: PlusScaler, pf: pd.DataFrame, scores: Path) -> dict:
    """Pearson r of the exported Pitching+ (in sample, league-average batter) with the leaderboard's OOF Pitching+."""
    s = pd.read_parquet(scores, columns=["PitchUID", "pitching_plus"]).set_index("PitchUID")["pitching_plus"]
    neutral = pf.drop(columns=[c for c in m.batter if c in pf]).assign(**m.batter)
    web = pd.Series(sc.transform(pf.assign(x=m.predict_xrv(neutral)), "x").to_numpy(), index=pf["PitchUID"])
    j = s.to_frame("lb").join(web.rename("web"), how="inner").dropna()
    return {"pearson_r": round(float(j.lb.corr(j.web)), 4), "n_pitches": int(len(j)), "against": scores.name}


def _prepare(clean: pd.DataFrame):
    from stuffplus.altitude import physics_translator
    from stuffplus.score import _load

    shape_model, d = _load("analysis/altitude_delta/run.py").prepare(clean)
    return physics_translator(shape_model), d


def random_rows(payload: dict, n: int, ranges: pd.DataFrame, seed: int = 0) -> pd.DataFrame:
    """Random vectors in observed ranges (q01–q99 of ``ranges``), every category, an unseen one and NaNs."""
    rng = np.random.default_rng(seed)
    out = {}
    for f in payload["features"]:
        if f in payload["categories"]:
            levels = payload["categories"][f] + ["Knuckle-Curve"]
            out[f] = [levels[i % len(levels)] for i in range(n)]
        else:
            lo, hi = ranges[f].astype(float).quantile([0.01, 0.99])
            vals = rng.uniform(lo, hi, n)
            if f in ("Balls", "Strikes", "is_rhp", "same_side") or set(ranges[f].dropna().unique()) <= {0, 1}:
                vals = rng.integers(int(lo), int(hi) + 1, n).astype(float)
            if f not in ("Balls", "Strikes"):  # v2 needs a real count to look up its table
                vals[rng.random(n) < 0.08] = np.nan
            out[f] = vals
    return pd.DataFrame(out)


def golden(model, payload: dict, rows: pd.DataFrame) -> dict:
    """The fitted model's own predictions for ``rows`` (the parity target for vitest): calibrated probabilities and
    contact at the row's count, ``xrv_at_count`` and ``xrv`` (count-neutral for production Stuff+ v2)."""
    comps = _base(model).predict_components(rows)
    xrv = model.predict_xrv(rows) if type(model).__name__ == "CountNeutral" else comps["xrv"].to_numpy()
    recs = rows.astype(object).where(rows.notna(), None).to_dict(orient="records")
    return {"rows": recs, "probs": comps[[f"p_{o}" for o in OUTCOMES]].to_numpy().tolist(),
            "contact": comps["contact_rv"].to_numpy().tolist(), "xrv_at_count": comps["xrv"].to_numpy().tolist(),
            "xrv": np.asarray(xrv, float).tolist()}


def synthetic_frame() -> pd.DataFrame:
    from stuffplus import schema
    from stuffplus.models.location import add_pitch_family
    from stuffplus.score import _load
    from tests.fixtures.synthetic import make_synthetic_pitches

    return add_pitch_family(_load("analysis/stuff_model/run.py").prepare(schema.clean(make_synthetic_pitches())))


def write_goldens(out_dir: Path = FIXTURES_DIR, n: int = 120) -> None:
    from stuffplus.altitude import STUFF_FEATURES_INVARIANT
    from stuffplus.models.stuff import magnus_translate

    d = synthetic_frame()
    # production v2 (count block + temperature), small rounds: the parity fixture for HACK-066
    v2 = fit_stuff(d, magnus_translate, k_inner=2, class_rounds=30, contact_rounds=20)
    p2 = export_composite(v2[0], v2[1], "stuff", model_version="synthetic_v2", sources=["tests/fixtures/synthetic.py"],
                          demo_data=True)
    rows2 = pd.concat([d[p2["features"]].sample(n // 2, random_state=1).reset_index(drop=True),
                       random_rows(p2, n - n // 2, d, seed=4)], ignore_index=True)
    write_json(p2, out_dir / "stuff_v2_synthetic.json")
    write_json(golden(v2[0], p2, rows2), out_dir / "stuff_v2_synthetic_golden.json")
    # v1 composite (nested and packed layouts) keeps the HACK-040 path covered
    m = StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=magnus_translate, class_rounds=40,
                   contact_rounds=30).fit(d)
    sc = PlusScaler().fit(d.assign(x=m.predict_at_rho(d, 1.0)["xrv"].to_numpy()), "x")
    payload = export_composite(m, sc, "stuff", model_version="synthetic", sources=["tests/fixtures/synthetic.py"],
                               demo_data=True, packed=False)  # nested = the HACK-038 contract layout
    rows = pd.concat([d[payload["features"]].sample(n // 2, random_state=0).reset_index(drop=True),
                      random_rows(payload, n - n // 2, d)], ignore_index=True)
    write_json(payload, out_dir / "stuff_synthetic.json")
    write_json(export_composite(m, sc, "stuff", model_version="synthetic", sources=["tests/fixtures/synthetic.py"],
                                demo_data=True), out_dir / "stuff_synthetic_packed.json")
    write_json(golden(m, payload, rows), out_dir / "stuff_synthetic_golden.json")
    # Pitching+ (HACK-079): components + target boosters + combination, small rounds
    from stuffplus.models.pitching import build_features

    pf = build_features(d)
    pm, psc = fit_pitching(pf, k=2, class_rounds=20, contact_rounds=15, target_rounds=15)
    pp = export_pitching(pm, psc, model_version="synthetic", sources=["tests/fixtures/synthetic.py"], demo_data=True,
                         fill=panel_fill(pf))
    pb = with_batters(pf)
    prows = pd.concat([pb[pp["features"]].sample(n // 2, random_state=2).reset_index(drop=True),
                       random_rows(pp, n - n // 2, pb, seed=5)], ignore_index=True)
    write_json(pp, out_dir / "pitching_synthetic.json")
    write_json(pitching_golden(pm, prows), out_dir / "pitching_synthetic_golden.json")


def export_pitching_real(d: pd.DataFrame, args, version: str) -> float:
    """Pitching+ on the real data at PITCHING_ROUNDS (fast: smoke rounds), with its fidelity to the leaderboard."""
    from stuffplus.models.pitching import build_features

    pf = build_features(d)
    rounds = dict(class_rounds=40, contact_rounds=30, target_rounds=20) if args.fast else PITCHING_ROUNDS
    m, sc = fit_pitching(pf, k=2 if args.fast else 5, **rounds)
    p = export_pitching(m, sc, model_version=version.replace("stuff_v2", "pitching"), demo_data=False,
                        fill=panel_fill(pf), sources=["stuffplus/export_trees.py", "stuffplus/models/pitching.py",
                                                      "stuffplus/models/multitarget.py"])
    p["rounds"] = rounds
    if args.scores.exists():
        p["fidelity"] = fidelity(m, sc, pf, args.scores)
        print("pitching fidelity", p["fidelity"])
    return write_json(p, MODELS_DIR / "pitching.json")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--golden", action="store_true", help="only write the synthetic parity goldens")
    ap.add_argument("--only", choices=["all", "pitching"], default="all", help="pitching: only models/pitching.json")
    ap.add_argument("--scores", type=Path, default=config.ARTIFACTS_DIR / "scores" / "pitch_scores.parquet",
                    help="leaderboard scores for the Pitching+ fidelity check (skipped if missing)")
    args = ap.parse_args()
    if args.golden:
        write_goldens()
        return
    from stuffplus import schema
    from stuffplus.io import load_raw

    translate, d = _prepare(schema.clean(load_raw()))
    rounds = dict(class_rounds=40, contact_rounds=30) if args.fast else {}
    k_inner = 2 if args.fast else 3
    version = "stuff_v2" + ("_fast" if args.fast else "")
    src = ["stuffplus/export_trees.py", "stuffplus/models/stuff.py", "stuffplus/models/stuff_v2.py",
           "stuffplus/calibration.py", "stuffplus/altitude.py"]
    total = 0.0
    if args.only == "pitching":
        return print(f"pitching.json {export_pitching_real(d, args, version):.2f} MB")
    m, sc = fit_stuff(d, translate, k_inner=k_inner, **rounds)
    stuff = export_composite(m, sc, "stuff", model_version=version, sources=src, demo_data=False)
    total += write_json(stuff, MODELS_DIR / "stuff.json")
    write_json(golden(m, stuff, random_rows(stuff, 60, d, seed=1)), FIXTURES_DIR / "stuff_real_golden.json")
    lm, lsc = fit_location(d, k_inner=k_inner, **rounds)
    loc = export_composite(lm, lsc, "location", model_version=version, demo_data=False, reference=lm.reference,
                           sources=["stuffplus/export_trees.py", "stuffplus/models/location.py", "stuffplus/calibration.py"])
    total += write_json(loc, MODELS_DIR / "location.json")
    lrows = random_rows(loc, 60, d, seed=2)
    lg = golden(lm, loc, lrows)
    lg["loc_value"] = lm.location_value(lrows.assign(
        count=lrows.Balls.round().astype("Int64").astype(str) + "-" + lrows.Strikes.round().astype("Int64").astype(str)),
        np.asarray(lg["xrv"])).tolist()
    write_json(lg, FIXTURES_DIR / "location_real_golden.json")
    total += export_pitching_real(d, args, version)
    print(f"wrote {MODELS_DIR} ({total:.2f} MB; budget {SIZE_BUDGET_MB} MB)")


if __name__ == "__main__":
    main()
