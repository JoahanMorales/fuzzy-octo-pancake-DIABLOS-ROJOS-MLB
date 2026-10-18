"""Parity golden for the in-browser prospect profiler (HACK-048), built from the Python pieces it ports.

Parsing and aggregation: ``stuffplus.prospect`` (``_parse``, ``_with_fastball``: primary fastball by usage).
Arm-side frame: ``stuffplus.models.common.add_arm_side_features``; arm angle as in ``models.stuff``.
Air: ``stuffplus.altitude.physics_translator`` with the paper's k (reports/physics_v2/physics.json, the same
shape model stuff.json was trained with). Score: ``stuffplus.export_trees.evaluate`` on the exported stuff.json
and the Plus scaler stored in it. The CSVs are synthetic (random vectors in observed ranges), never data rows.
Run from the repo root: python web/src/features/prospecto/make_golden.py
"""
from __future__ import annotations

import io
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pandas as pd

from stuffplus import export_trees as et
from stuffplus import prospect
from stuffplus.altitude import physics_translator
from stuffplus.models.common import add_arm_side_features

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).with_name("golden.json")


def _pitch_level_csv(rng) -> str:
    rows = []
    for ptype, n, velo, ivb, hb, spin, axis in (("Four-Seam", 40, 94, 17, 9, 2350, 212), ("Slider", 25, 85, 1, -6, 2500, 95),
                                                ("Changeup", 15, 86, 7, 13, 1700, 240), ("Sweeper", 10, 81, -2, -14, 2600, 80),
                                                ("Knuckleball", 3, 75, 0, 0, 300, 0)):
        for _ in range(n):
            rows.append(dict(AutoPitchType=ptype, PitcherThrows="Right", RelSpeed=round(rng.normal(velo, 1.0), 2),
                             SpinRate=round(rng.normal(spin, 60), 1), SpinAxis=round((axis + rng.normal(0, 8)) % 360, 1),
                             InducedVertBreak=round(rng.normal(ivb, 1.5), 2), HorzBreak=round(rng.normal(hb, 1.5), 2),
                             RelHeight=round(rng.normal(5.9, 0.08), 3), RelSide=round(rng.normal(2.1, 0.08), 3),
                             Extension=round(rng.normal(6.4, 0.1), 3)))
    return pd.DataFrame(rows).to_csv(index=False)


SUMMARY_LHP = """pitch_type,throws,velo,spin_rate,spin_axis,ivb,hb,RelHeight,RelSide,Extension,usage
Cutter,Left,89.5,2450,170,9.5,2.5,6.1,-2.3,6.0,0.45
Curveball,Left,78.2,2700,20,-11.0,6.0,6.1,-2.3,5.9,0.25
Splitter,Left,84.0,1400,250,3.0,-9.0,6.1,-2.3,6.1,0.30
"""

SUMMARY_NO_FASTBALL = """AutoPitchType,PitcherThrows,RelSpeed,SpinRate,SpinAxis,InducedVertBreak,HorzBreak,rho_measured
Slider,Right,86.0,2550,100,2.0,-5.0,0.84
Curveball,Right,79.0,2800,30,-13.0,7.0,0.84
"""


def score(csv_text: str, payload: dict, translator, rho_hh: float) -> dict:
    parsed = prospect._parse(pd.read_csv(io.StringIO(csv_text)))
    rows = prospect._with_fastball(parsed)
    df = pd.DataFrame([dict(pitch_family=p.pitch_type, PitcherThrows=p.throws, RelSpeed=p.velo, SpinRate=p.spin_rate,
                            SpinAxis=p.spin_axis, InducedVertBreak=p.ivb, HorzBreak=p.hb, RelHeight=p.rel_height,
                            RelSide=p.rel_side, Extension=p.extension, rho=p.rho_measured,
                            fb_velo=p.arsenal.get("fb_velo", np.nan), fb_ivb=p.arsenal.get("fb_ivb", np.nan),
                            fb_hb=p.arsenal.get("fb_hb", np.nan)) for p, _ in rows])
    df = add_arm_side_features(df)
    sign = np.where(df.PitcherThrows.eq("Right"), 1.0, -1.0)
    df["arm_angle"] = np.degrees(np.arctan2(df.RelHeight - 5.0, df.rel_side_arm.abs()))
    df["velo_diff_fb"] = df.RelSpeed - df.fb_velo
    df["ivb_diff_fb"] = df.InducedVertBreak - df.fb_ivb
    df["hb_diff_fb"] = df.hb_arm - df.fb_hb * sign
    st = payload["plus"]["stats"]["__all__"]
    out = {"pitches": []}
    usage = np.array([u for _, u in rows])
    for name, rho_to in (("neutral", 1.0), ("cdmx", rho_hh)):
        moved = translator(df, rho_to, df["rho"].to_numpy(float))
        xrv = et.evaluate(payload, moved)["xrv"].to_numpy()
        plus = 100 + 10 * payload["plus"]["sign"] * (xrv - st["mean"]) / st["sd"]
        out[f"arsenal_{name}"] = float(np.sum(plus * usage))
        for i, (p, u) in enumerate(rows):
            if len(out["pitches"]) <= i:
                out["pitches"].append({"pitch_type": p.pitch_type, "usage": float(u),
                                       "features": {f: (None if pd.isna(df.loc[i, f]) else float(df.loc[i, f]))
                                                    for f in payload["features"] if f != "pitch_family" and f in df}})
            out["pitches"][i][f"stuff_{name}"] = float(plus[i])
            out["pitches"][i][f"xrv_{name}"] = float(xrv[i])
    return out


def main() -> None:
    payload = json.loads((ROOT / "web/public/data/models/stuff.json").read_text())
    phys = json.loads((ROOT / "reports/physics_v2/physics.json").read_text())
    translator = physics_translator(SimpleNamespace(rho_effect=phys["translator"]["k"], rho_ref=phys["translator"]["rho_ref"]))
    rho_hh = phys["rho"]["harp_helu"]
    cases = {"pitch_level_rhp": _pitch_level_csv(np.random.default_rng(7)), "summary_lhp": SUMMARY_LHP,
             "no_fastball_measured_air": SUMMARY_NO_FASTBALL}
    golden = {"rho_hh": rho_hh, "model_version": payload["model_version"],
              "cases": [{"name": n, "csv": c, **score(c, payload, translator, rho_hh)} for n, c in cases.items()]}
    OUT.write_text(json.dumps(golden, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
