"""python -m analysis.validation.run [--demo] [--fast] [--data PATH]."""
from __future__ import annotations

import argparse
from pathlib import Path

from analysis.stuff_model.run import prepare
from stuffplus import config, schema
from stuffplus.io import load_raw
from stuffplus.models.pitching import build_features
from stuffplus.physics.parks import build_maps
from stuffplus.validation.run_all import run_all


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--demo", action="store_true")
    p.add_argument("--fast", action="store_true")
    p.add_argument("--data", type=Path)
    p.add_argument("--out", type=Path, default=config.REPORTS_DIR / "validation")
    args = p.parse_args()
    if args.demo and args.data:
        p.error("--demo and --data are mutually exclusive")
    if args.demo:
        from tests.fixtures.synthetic import make_synthetic_pitches
        raw = make_synthetic_pitches()
    else:
        raw = load_raw(path=args.data)  # Missing official input must fail, never fall back.
    cleaned = schema.clean(raw)
    # build_features assigns families once, preserving the original fallback flag.
    frame = build_features(prepare(cleaned))
    maps = build_maps(cleaned)["park_map"]
    frame["park_id"] = frame.game_anon_id.map(maps.set_index("game_anon_id").franchise).astype("string")
    result = run_all(frame, args.out, demo_data=args.demo, fast=args.fast,
                     n_boot=30 if args.fast else 300, min_n=15 if args.fast else 150,
                     sample_sizes=(10, 25, 50) if args.fast else (50, 100, 200, 400))
    print(f"Aggregate diagnostics: {args.out}; demo_data={args.demo}; evidence=exploratory_transductive")
    print(result["status"].query("status != 'evaluated'").to_string(index=False))


if __name__ == "__main__":
    main()
