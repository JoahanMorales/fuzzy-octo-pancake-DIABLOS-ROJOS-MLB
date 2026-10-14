"""Generate aggregate sensitivity reports from official data; never export pitches."""
from __future__ import annotations
import argparse
import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from stuffplus import config, schema
from stuffplus.io import load_raw
from stuffplus.altitude import STUFF_FEATURES_INVARIANT, physics_translator, counterfactual_scores
from stuffplus.models.stuff import StuffModel
from stuffplus.scale import PlusScaler
from stuffplus.physics.constants import RHO_HARP_HELU
from stuffplus.sensitivity import summarize_sensitivity


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fast", action="store_true", help="Exploratory lower-round fit, not validation")
    args = parser.parse_args()
    spec = importlib.util.spec_from_file_location("altitude_run", ROOT / "analysis/altitude_delta/run.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    shape, d = module.prepare(schema.clean(load_raw()))
    rounds = dict(class_rounds=60, contact_rounds=40) if args.fast else {}
    model = StuffModel(features=list(STUFF_FEATURES_INVARIANT), translate=physics_translator(shape), **rounds).fit(d)
    neutral = model.predict_at_rho(d, 1.0)
    scaler = PlusScaler().fit(d.assign(x=neutral["xrv"].to_numpy()), "x")
    scores = counterfactual_scores(d, model, scaler, RHO_HARP_HELU)
    frame = d[[c for c in ("PitchUID", "pitcher_anon_id", "year", "pitch_key", "pitch_family", "game_anon_id", "altitude_category") if c in d]].copy()
    for col in ("stuff_a", "stuff_b"):
        frame[col] = scores[col]
    frame["delta_ivb_in"] = scores.ivb_a - scores.ivb_b
    frame["delta_hb_arm_in"] = scores.hb_a - scores.hb_b
    env = model.predict_components(d)["xrv"].to_numpy()
    frame["observed_stuff_plus"] = scaler.transform(d.assign(x=env), "x").to_numpy()
    tables = summarize_sensitivity(frame)
    output = config.REPORTS_DIR / "pitcher_sensitivity"
    output.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(output / f"{name}.csv", index=False)
    metadata = {"demo_data": False, "exploratory": True, "fast": args.fast,
                "pitches": len(frame), "pitcher_seasons": len(tables["pitchers"]),
                "ranked": int(tables["pitchers"].eligible.sum()),
                "method": "In-sample globally prepared HACK-015 model; conditional game-cluster EB intervals; not holdout validation"}
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")
    print(json.dumps(metadata))


if __name__ == "__main__":
    main()
