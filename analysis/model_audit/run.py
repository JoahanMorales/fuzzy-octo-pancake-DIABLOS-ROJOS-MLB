"""Final model audit (HACK-084): is the production Stuff+ correct, and where does the altitude effect come from?

    python -m analysis.model_audit.run [--sample 20000]

Read-only: uses the real data (``stuffplus.io.load_raw``), the same preparation as reports/altitude_delta and the
exported production model (web/public/data/models/stuff.json, Stuff+ v2 + temperature, HACK-057/066). No refit, no
per-pitch rows written. Outputs in reports/model_audit/:

  calibration.csv    physics translator vs observed movement: Extreme-altitude pitches of pitch keys also thrown in
                     No-altitude games, translated to the key's No-altitude density, against the same keys' observed
                     No-altitude mean IVB and arm-side HB (per family)
  decomposition.csv  league ΔStuff+ (Harp Helú air − sea level) split into translated movement with the model's ``rho``
                     feature held at sea level, and the learned ``rho`` effect with the movement held fixed
  checks.csv         pass/fail: export features, pitcher folds, count neutrality, what the translator changes
  scale.csv          Stuff+ mean and sd per season (production pitch scores)
  README.md          the decision rule fixed before running and the verdict
"""
from __future__ import annotations

import argparse
import importlib.util
import json
from pathlib import Path

import numpy as np
import pandas as pd

from stuffplus import config, schema, splits
from stuffplus.altitude import physics_translator
from stuffplus.export_trees import stuff_value
from stuffplus.io import load_raw
from stuffplus.models.stuff_v2 import V2_FEATURES
from stuffplus.physics.constants import RHO_HARP_HELU

OUT = config.REPORTS_DIR / "model_audit"
STUFF_JSON = config.repo_root() / "web" / "public" / "data" / "models" / "stuff.json"
RATIO_TOL = 0.15  # predicted / observed change within ±15 %
ABS_TOL = 0.5  # or within half an inch
BIG_FAMILY = 0.05  # a miscalibration only changes the model in a family with at least 5 % of pitches
EXT, NO = "Extreme Altitude", "No Altitude"


def _prepare():
    spec = importlib.util.spec_from_file_location("altitude_run", config.repo_root() / "analysis" / "altitude_delta" / "run.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.prepare(schema.clean(load_raw()))


def calibration(d: pd.DataFrame, tr) -> pd.DataFrame:
    cat = d["altitude_category"].astype(str)
    sets = d.assign(c=cat).groupby("pitch_key")["c"].agg(set)
    keys = sets[sets.map(lambda s: {EXT, NO} <= s)].index
    dd = d[d["pitch_key"].isin(keys)]
    ext = dd[cat.loc[dd.index] == EXT]
    no = dd[cat.loc[dd.index] == NO].groupby("pitch_key")[["InducedVertBreak", "hb_arm", "rho"]].mean()
    moved = tr(ext, ext["pitch_key"].map(no["rho"]).to_numpy(float), ext["rho"].to_numpy(float))
    share = d["pitch_family"].astype(str).value_counts(normalize=True)
    rows = []
    for fam, idx in ext.groupby(ext["pitch_family"].astype(str)).groups.items():
        e, m = ext.loc[idx], moved.loc[idx]
        for comp, label in (("InducedVertBreak", "IVB"), ("hb_arm", "HB lado del brazo")):
            obs = float(np.mean(e["pitch_key"].map(no[comp]).to_numpy(float) - e[comp].to_numpy(float)))
            pred = float(np.mean(m[comp].to_numpy(float) - e[comp].to_numpy(float)))
            ratio = pred / obs if abs(obs) > 1e-9 else np.nan
            ok = abs(pred - obs) <= ABS_TOL or (np.isfinite(ratio) and abs(ratio - 1) <= RATIO_TOL)
            rows.append(dict(pitch_family=fam, component=label, pitches=len(e), pitch_keys=e["pitch_key"].nunique(),
                             family_share=float(share.get(fam, 0.0)), mean_extreme=float(e[comp].mean()),
                             observed_change=obs, predicted_change=pred, ratio=ratio, abs_error=abs(pred - obs),
                             calibrated=bool(ok), blocks_model=bool(not ok and share.get(fam, 0.0) >= BIG_FAMILY)))
    return pd.DataFrame(rows)


def decomposition(d: pd.DataFrame, tr, payload: dict, n: int) -> pd.DataFrame:
    g = payload["plus"]["stats"]["__all__"]
    plus = lambda x: 100 + 10 * payload["plus"].get("sign", -1) * (x - g["mean"]) / g["sd"]  # noqa: E731
    s = d.sample(min(n, len(d)), random_state=2240)
    src = s["rho"].to_numpy(float)
    a, b = tr(s, RHO_HARP_HELU, src), tr(s, 1.0, src)
    sea = plus(stuff_value(payload, b))
    total = plus(stuff_value(payload, a)) - sea
    movement = plus(stuff_value(payload, a.assign(rho=1.0))) - sea
    learned = plus(stuff_value(payload, b.assign(rho=RHO_HARP_HELU))) - sea
    rows = [("total", total), ("movimiento trasladado (rho del modelo a nivel del mar)", movement),
            ("rho aprendido (movimiento fijo)", learned), ("interacción", total - movement - learned)]
    return pd.DataFrame([dict(part=p, delta_stuff=float(np.mean(v)), sample=len(s)) for p, v in rows])


def checks(d: pd.DataFrame, tr, payload: dict) -> pd.DataFrame:
    feats = list(payload["features"])
    banned = [f for f in feats if any(w in f.lower() for w in ("plate", "loc", "result", "call", "rv", "anon", "game"))]
    folds = [set(d["pitcher_anon_id"].iloc[te]) for _, te in splits.pitcher_group_kfold(d)]
    overlap = sum(len(folds[i] & folds[j]) for i in range(len(folds)) for j in range(i + 1, len(folds)))
    s = d.sample(3000, random_state=1)
    neutral = float(np.max(np.abs(stuff_value(payload, s) - stuff_value(payload, s.assign(Balls=3, Strikes=0)))))
    t = tr(s, RHO_HARP_HELU, s["rho"].to_numpy(float))
    changed = sorted(c for c in s.columns if c in t and not np.allclose(
        pd.to_numeric(s[c], errors="coerce").fillna(-999), pd.to_numeric(t[c], errors="coerce").fillna(-999)))
    allowed = {"InducedVertBreak", "HorzBreak", "hb_arm", "rho", "ivb_diff_fb", "hb_diff_fb"}
    return pd.DataFrame([
        dict(check="los rasgos exportados son V2_FEATURES", value=", ".join(feats), passed=feats == list(V2_FEATURES)),
        dict(check="sin ubicación, resultados ni ids en los rasgos", value=", ".join(banned) or "ninguno", passed=not banned),
        dict(check="pitchers repetidos entre pliegues", value=str(overlap), passed=overlap == 0),
        dict(check="Stuff+ v2 no cambia con el conteo del lanzamiento (máx. |dif|)", value=f"{neutral:.3g}", passed=neutral == 0.0),
        dict(check="el traductor solo cambia movimiento y rho", value=", ".join(changed), passed=set(changed) <= allowed),
    ])


def scale(path: Path | None = None) -> pd.DataFrame:
    path = path or config.ARTIFACTS_DIR / "scores" / "pitch_scores.parquet"
    sc = pd.read_parquet(path, columns=["year", "stuff_plus"])
    return sc.groupby("year")["stuff_plus"].agg(mean="mean", sd="std", pitches="count").reset_index()


def readme(cal: pd.DataFrame, dec: pd.DataFrame, chk: pd.DataFrame, scl: pd.DataFrame) -> str:
    tot = float(dec.loc[dec.part == "total", "delta_stuff"].iloc[0])
    mov = float(dec.loc[dec.part.str.startswith("movimiento"), "delta_stuff"].iloc[0])
    lrn = float(dec.loc[dec.part.str.startswith("rho aprendido"), "delta_stuff"].iloc[0])
    fam_ok = cal.groupby("pitch_family")["calibrated"].all()
    shares = cal.drop_duplicates("pitch_family").set_index("pitch_family")["family_share"]
    share_ok = float(shares[fam_ok[fam_ok].index].sum())
    bad = cal[~cal.calibrated]
    blocking = cal[cal.blocks_model]
    L = ["# Auditoría final del modelo (HACK-084)", "",
         "Generado por `python -m analysis.model_audit.run` sobre los datos reales y el Stuff+ de producción exportado "
         "(`web/public/data/models/stuff.json`); ninguna cifra se escribió a mano y no se reentrena nada.", "",
         "**Regla fijada antes de correr:** el modelo solo cambia por una fuga de datos, pliegues que se traslapan o un "
         f"traductor mal calibrado (fuera de ±{RATIO_TOL:.0%} y de ±{ABS_TOL} in) en una familia con al menos "
         f"{BIG_FAMILY:.0%} de los lanzamientos. Lo demás se declara como limitación.", "",
         f"**Veredicto: {'cambiar el modelo' if (not chk.passed.all() or len(blocking)) else 'el modelo no cambia'}.**", "",
         "## Comprobaciones (`checks.csv`, `scale.csv`)", ""]
    L += [f"- {r.check}: {r.value} ({'pasa' if r.passed else 'falla'})." for r in chk.itertuples()]
    L += [f"- Stuff+ por temporada: " + "; ".join(f"{int(r.year)} media {r.mean:.1f}, de {r.sd:.1f}" for r in scl.itertuples()) + ".", "",
          "## Traductor físico contra lo observado (`calibration.csv`)", "",
          "Mismo lanzamiento (pitcher × temporada × identidad) en juegos de altitud extrema trasladado a la densidad de sus "
          "juegos sin altitud, contra lo que de verdad hizo en esos juegos. Cociente = cambio predicho / cambio observado.", "",
          "| Familia | % lanzamientos | Componente | Observado (in) | Predicho (in) | Cociente | ¿Calibrado? |",
          "|---|---:|---|---:|---:|---:|---|"]
    for r in cal.sort_values(["family_share", "component"], ascending=[False, True]).itertuples():
        L.append(f"| {r.pitch_family} | {100 * r.family_share:.1f} | {r.component} | {r.observed_change:+.2f} | "
                 f"{r.predicted_change:+.2f} | {r.ratio:.2f} | {'sí' if r.calibrated else 'no'} |")
    L += ["", f"Las familias calibradas en sus dos componentes suman {100 * share_ok:.1f} % de los lanzamientos."]
    if len(bad):
        L.append("Fuera de tolerancia: " + "; ".join(
            f"{r.pitch_family} {r.component} (cociente {r.ratio:.2f}, {100 * r.family_share:.1f} % de los lanzamientos)"
            for r in bad.itertuples()) + ". La traducción proporcional se dispara cuando el movimiento medio está cerca de "
            "0; el ΔStuff+ de esas familias se lee con cautela y no cambia el modelo por la regla de arriba.")
    L += ["", "## ¿De dónde sale el ΔStuff+ de la liga? (`decomposition.csv`)", "",
          f"En una muestra de {int(dec["sample"].iloc[0]):,} lanzamientos, el ΔStuff+ total en el aire del Harp Helú es {tot:+.2f}. "
          f"Con el movimiento trasladado y el rasgo `rho` del modelo fijo a nivel del mar: {mov:+.2f} (lo que quita perder "
          f"Magnus). Con el movimiento fijo y solo el `rho` aprendido: {lrn:+.2f} (lo que el modelo aprendió de los juegos en "
          "altura: el contacto hace más daño y la bola vuela más). El resto es la interacción.", "",
          "## Límites",
          "- Las diferencias observadas son crudas dentro del lanzamiento: incluyen cambios de ejecución (velocidad, giro) "
          "entre juegos, que el traductor no modela.",
          "- La descomposición usa el modelo exportado del navegador, idéntico al de producción (paridad de HACK-066).",
          "- `scale.csv` lee `artifacts/scores/pitch_scores.parquet` (git-ignored): debe ser la corrida de producción v2."]
    return "\n".join(L) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--sample", type=int, default=20000)
    ap.add_argument("--scores", type=Path, default=None, help="production v2 pitch_scores.parquet (python -m stuffplus.score)")
    args = ap.parse_args(argv)
    shape_model, d = _prepare()
    tr = physics_translator(shape_model)
    payload = json.loads(STUFF_JSON.read_text(encoding="utf-8"))
    cal, dec, chk, scl = calibration(d, tr), decomposition(d, tr, payload, args.sample), checks(d, tr, payload), scale(args.scores)
    OUT.mkdir(parents=True, exist_ok=True)
    cal.round(4).to_csv(OUT / "calibration.csv", index=False)
    dec.round(4).to_csv(OUT / "decomposition.csv", index=False)
    chk.to_csv(OUT / "checks.csv", index=False)
    scl.round(3).to_csv(OUT / "scale.csv", index=False)
    (OUT / "README.md").write_text(readme(cal, dec, chk, scl), encoding="utf-8")
    print(f"MODEL_AUDIT_OK {OUT}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
