"""Tree models for the browser: the paper's Stuff+/Location+ composites as contract JSON (HACK-040).

A composite is a LightGBM multiclass booster (5 pitch outcomes) + a contact regressor (E[rv_x | in play]) + the
LMB value of each outcome + the Plus scaler fitted on the park-neutral (ρ = 1) predictions. ``web/src/model/
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
from stuffplus.models.common import as_model_frame
from stuffplus.models.stuff import OUTCOMES, StuffModel
from stuffplus.scale import PlusScaler

MODELS_DIR = config.repo_root() / "web" / "public" / "data" / "models"
FIXTURES_DIR = config.repo_root() / "web" / "src" / "model" / "fixtures"
MODEL_LABEL = "pitch_family Stuff+ composite"
SIZE_BUDGET_MB = 15.0
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


def export_composite(model: StuffModel, scaler: PlusScaler, name: str, *, model_version: str,
                     sources: Sequence[str], demo_data: bool, reference: pd.Series | None = None,
                     packed: bool = True) -> dict:
    """Contract payload for one composite (``reference``: Location+ league mean xRV by ``count|pitch_family``)."""
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
            cols.append(rows[f].map(lambda s: codes.get(str(s), np.nan)).to_numpy(float))
        else:
            cols.append(pd.to_numeric(rows[f], errors="coerce").to_numpy(float))
    return np.column_stack(cols)


def evaluate(payload: dict, rows: pd.DataFrame) -> pd.DataFrame:
    X = encode(payload, rows)
    k = payload["outcome"]["num_class"]
    raw = np.zeros((len(X), k))
    for t in payload["outcome"]["trees"]:
        root = _root(t)
        raw[:, t["tree_index"] % k] += [_leaf(root, r) for r in X]
    p = np.exp(raw - raw.max(axis=1, keepdims=True))
    p /= p.sum(axis=1, keepdims=True)
    contact = np.zeros(len(X))
    for t in payload["contact"]["trees"]:
        root = _root(t)
        contact += [_leaf(root, r) for r in X]
    v = np.array([c["rv"] for c in payload["class_values"]])
    out = pd.DataFrame(p, columns=[f"p_{o}" for o in OUTCOMES])
    out["contact_rv"] = contact
    out["xrv"] = p[:, :4] @ v[:4] + p[:, 4] * contact
    return out


# ---- fitting ----

def fit_stuff(d: pd.DataFrame, translate, **rounds) -> tuple[StuffModel, PlusScaler]:
    """The paper's Stuff+ composite (pitch_family, physics translator) + its park-neutral scaler."""
    from stuffplus.altitude import STUFF_FEATURES_INVARIANT

    m = StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=translate, **rounds).fit(d)
    sc = PlusScaler().fit(d.assign(x=m.predict_at_rho(d, 1.0)["xrv"].to_numpy()), "x")
    return m, sc


def fit_location(d: pd.DataFrame, **rounds):
    from stuffplus.models.location import LocationModel

    m = LocationModel(**rounds).fit(d)
    sc = PlusScaler().fit(d.assign(x=m.location_value(d)), "x")
    return m, sc


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
            vals[rng.random(n) < 0.08] = np.nan
            out[f] = vals
    return pd.DataFrame(out)


def golden(model: StuffModel, payload: dict, rows: pd.DataFrame) -> dict:
    """LightGBM's own predictions for ``rows`` (the parity target for vitest)."""
    X = as_model_frame(rows, payload["features"])
    probs = model.classifier.predict(X)
    contact = model.contact.predict(X)
    xrv = StuffModel._combine(probs, contact, model.class_values)
    recs = rows.astype(object).where(rows.notna(), None).to_dict(orient="records")
    return {"rows": recs, "probs": probs.tolist(), "contact": contact.tolist(), "xrv": xrv.tolist()}


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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--golden", action="store_true", help="only write the synthetic parity goldens")
    args = ap.parse_args()
    if args.golden:
        write_goldens()
        return
    from stuffplus import schema
    from stuffplus.io import load_raw

    translate, d = _prepare(schema.clean(load_raw()))
    rounds = dict(class_rounds=40, contact_rounds=30) if args.fast else {}
    version = "pitch_family_v1" + ("_fast" if args.fast else "")
    src = ["stuffplus/export_trees.py", "stuffplus/models/stuff.py", "stuffplus/altitude.py"]
    total = 0.0
    m, sc = fit_stuff(d, translate, **rounds)
    stuff = export_composite(m, sc, "stuff", model_version=version, sources=src, demo_data=False)
    total += write_json(stuff, MODELS_DIR / "stuff.json")
    write_json(golden(m, stuff, random_rows(stuff, 60, d, seed=1)), FIXTURES_DIR / "stuff_real_golden.json")
    lm, lsc = fit_location(d, **rounds)
    loc = export_composite(lm, lsc, "location", model_version=version, demo_data=False, reference=lm.reference,
                           sources=["stuffplus/export_trees.py", "stuffplus/models/location.py"])
    total += write_json(loc, MODELS_DIR / "location.json")
    lrows = random_rows(loc, 60, d, seed=2)
    lg = golden(lm, loc, lrows)
    lg["loc_value"] = lm.location_value(lrows.assign(
        count=lrows.Balls.round().astype("Int64").astype(str) + "-" + lrows.Strikes.round().astype("Int64").astype(str)),
        np.asarray(lg["xrv"])).tolist()
    write_json(lg, FIXTURES_DIR / "location_real_golden.json")
    print(f"wrote {MODELS_DIR} ({total:.2f} MB; budget {SIZE_BUDGET_MB} MB)")


if __name__ == "__main__":
    main()
