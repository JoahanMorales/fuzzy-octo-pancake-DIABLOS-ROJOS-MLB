"""Contrato web (HACK-038): agregados JSON para el producto React.

``python stuffplus/export_web.py --mock`` regenera ``web/public/data/mock/``.
Las cifras salen de ``reports/`` y ``deploy/bundle/tables/``. No se lee el parquet
y no se fija el ΔStuff+ de liga: HACK-050 sustituye este mock por el bundle real.

Cada archivo lleva ``model_version``, el modelo y la traducción que usa la web
(el compuesto Stuff+ por ``pitch_family`` con ``physics_translator``).
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

if __name__ == "__main__" and __package__ is None:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from stuffplus.altitude import STUFF_FEATURES_INVARIANT
from stuffplus.config import repo_root
from stuffplus.models.location import LOCATION_FEATURES
from stuffplus.models.pitching import PITCHING_FEATURES

MODEL_VERSION = "stuff_v2"
MODEL_NAME = "pitch_family Stuff+ composite"
TRANSLATION = "physics_translator"
MAX_MB = 25.0
MAX_PITCH_ROWS = 1000

ROOT_FILES = (
    "parks.json",
    "shapes.json",
    "leaderboard.json",
    "staff.json",
    "validation.json",
    "physics.json",
    "models/stuff.json",
    "models/location.json",
    "models/pitching.json",
)


class LeakError(ValueError):
    """El export trae filas de lanzamiento o se pasa del presupuesto de tamaño."""


def _checker():
    import importlib.util

    path = repo_root() / "scripts" / "check_no_raw_data.py"
    spec = importlib.util.spec_from_file_location("check_no_raw_data", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _clean(value):
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return None
        return round(value, 5)
    if isinstance(value, dict):
        return {str(k): _clean(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_clean(v) for v in value]
    if hasattr(value, "item"):
        return _clean(value.item())
    return value


def _records(df: pd.DataFrame) -> list[dict]:
    if df.empty:
        return []
    out = df.copy()
    for col in out.columns:
        if str(out[col].dtype).startswith("int"):
            out[col] = out[col].astype(int)
    return _clean(json.loads(out.to_json(orient="records", double_precision=5)))


def envelope(sources: list[str]) -> dict:
    return {
        "model_version": MODEL_VERSION,
        "model": MODEL_NAME,
        "translation": TRANSLATION,
        "demo_data": True,
        "sources": sources,
    }


def _read(root: Path, rel: str) -> pd.DataFrame:
    path = root / rel
    if not path.is_file():
        raise FileNotFoundError(f"falta el agregado {rel}")
    return pd.read_csv(path)


def _lists(obj) -> list[list[dict]]:
    found: list[list[dict]] = []
    if isinstance(obj, list) and obj and all(isinstance(row, dict) for row in obj):
        found.append(obj)
    elif isinstance(obj, dict):
        for value in obj.values():
            found.extend(_lists(value))
    return found


def assert_aggregate(doc: dict) -> None:
    """Aplica las reglas de ``scripts/check_no_raw_data.py`` a cada tabla del JSON."""
    check = _checker()
    for rows in _lists(doc):
        if len(rows) <= MAX_PITCH_ROWS:
            continue
        header = {str(k).lower() for k in rows[0]}
        ids = check.PITCH_ID & header
        raw = check.RAW_COLUMNS & header
        if ids or len(raw) >= 3:
            why = f"pitch id {sorted(ids)}" if ids else f"raw per-pitch columns {sorted(raw)[:6]}"
            raise LeakError(f"{len(rows)} filas con {why} (> {MAX_PITCH_ROWS})")


def _parks(root: Path) -> dict:
    src = "deploy/bundle/tables/by_park.csv"
    frame = _read(root, src).sort_values("park_id")
    parks = []
    for row in frame.itertuples(index=False):
        label = str(row.altitude)
        parks.append({
            "id": str(int(row.park_id)),
            "rho": round(float(row.rho), 5),
            "bucket": label,
            "air_effect": round(float(row.air_effect), 5),
            "altitude": label,
        })
    return {**envelope([src]), "parks": parks}


def _shapes(root: Path) -> dict:
    src = "reports/altitude_delta/delta_by_shape.csv"
    cols = [
        "shape", "pitches", "pitchers", "stuff_sea_level", "stuff_harp_helu", "delta_stuff",
        "delta_lo", "delta_hi", "delta_ivb_in", "delta_hb_arm_in", "delta_whiff_pct",
        "delta_called_strike_pct", "delta_in_play_pct", "delta_contact_runs",
        "delta_hard_contact_pct", "delta_hr_per_fb_pct", "relative_to_league", "verdict", "physics",
    ]
    return {**envelope([src]), "shapes": _records(_read(root, src)[cols])}


def _leaderboard(root: Path) -> dict:
    src = "reports/leaderboards/pitcher_season.csv"
    cols = [
        "pitcher_anon_id", "year", "pitches", "throws", "stuff_plus", "stuff_plus_harp_helu",
        "stuff_plus_own_air", "location_plus", "pitching_plus", "delta_cdmx", "arsenal",
        "stuff_plus_percentile",
    ]
    rows = _records(_read(root, src)[cols].sort_values(["stuff_plus", "pitcher_anon_id"], ascending=[False, True]))
    return {**envelope([src]), "rows": rows}


def _staff_pitcher(row: pd.Series) -> dict:
    def num(name: str):
        value = row[name]
        if pd.isna(value):
            return None
        return round(float(value), 5)

    return {
        "pitcher_anon_id": str(row.pitcher_anon_id),
        "throws": str(row.throws),
        "role": str(row.role),
        "pitches": int(row.pitches),
        "home_pitches": int(row.home_pitches),
        "stuff_plus": num("stuff_plus"),
        "stuff_plus_harp_helu": num("stuff_plus_harp_helu"),
        "pitching_plus": num("pitching_plus"),
        "location_plus": num("location_plus"),
        "delta_cdmx": num("delta_cdmx"),
        "altitude_resilience": num("altitude_resilience"),
        "own_air_home": num("own_air_home"),
        "own_air_road": num("own_air_road"),
    }


def _staff(root: Path) -> dict:
    src = "reports/staff_audit/staff_pitchers.csv"
    frame = _read(root, src)
    franchises = []
    for franchise, group in frame.groupby("franchise", sort=True):
        franchises.append({
            "id": str(int(franchise)),
            "pitchers": [_staff_pitcher(row) for _, row in group.sort_values("pitcher_anon_id").iterrows()],
        })
    return {
        **envelope([src]),
        "pooled": False,
        "note": "Las franquicias 5 y 11 se identifican por separado y no se juntan.",
        "franchises": franchises,
    }


PRODUCTION_MODEL = "Stuff+ v2 de producción (conteo neutral)"


def _highlights(shapes: pd.DataFrame) -> dict:
    """ΔStuff+ CDMX de la liga y formas extremas del modelo de producción (HACK-087).

    ``relative_to_league`` es ``delta_stuff`` menos el promedio de la liga, así que la resta
    devuelve ese promedio en cada fila.
    """
    league = float((shapes["delta_stuff"] - shapes["relative_to_league"]).mean())
    best = shapes.loc[shapes["delta_stuff"].idxmax()]
    worst = shapes.loc[shapes["delta_stuff"].idxmin()]
    return {
        "league_delta_cdmx": round(league, 4),
        "best_shape": str(best["shape"]),
        "best_delta": float(best["delta_stuff"]),
        "worst_shape": str(worst["shape"]),
        "worst_delta": float(worst["delta_stuff"]),
        "source_model": PRODUCTION_MODEL,
    }


def _validation(root: Path) -> dict:
    table_src = "reports/validation/official_full/validation_table.csv"
    shape_src = "reports/altitude_delta/delta_by_shape.csv"
    alt_src = "reports/stuff_v2/altitude.csv"
    decision_src = "reports/stuff_v2/decision.csv"
    table = _read(root, table_src)
    altitude = _records(_read(root, alt_src))
    decision = _records(_read(root, decision_src))
    return {
        **envelope([table_src, shape_src, alt_src, decision_src]),
        "highlights": _highlights(_read(root, shape_src)),
        "altitude_models": altitude,
        "adoption": decision,
        "rows": _records(table),
    }


def _physics(root: Path) -> dict:
    coef_src = "reports/physics_v2/coefficients_by_bucket.csv"
    elast_src = "reports/physics_v2/magnus_elasticity.csv"
    coef = _read(root, coef_src)
    elast = _read(root, elast_src).set_index("pitch_family")
    families = []
    for family, group in coef.groupby("pitch_family", sort=True):
        if family not in elast.index:
            raise FileNotFoundError(f"{family} no está en {elast_src}")
        sea = group[group["bucket"] == "No Altitude"].iloc[0]
        extreme = group[group["bucket"] == "Extreme Altitude"].iloc[0]
        e = elast.loc[family]
        families.append({
            "pitch_family": str(family),
            "cd_sea": round(float(sea.cd), 5),
            "cl_sea": round(float(sea.cl), 5),
            "cl_lo": round(float(sea.cl_lo), 5),
            "cl_hi": round(float(sea.cl_hi), 5),
            "cd_extreme": round(float(extreme.cd), 5),
            "cl_extreme": round(float(extreme.cl), 5),
            "elasticity": round(float(e.elasticity), 5),
            "elasticity_lo": round(float(e.lo), 5),
            "elasticity_hi": round(float(e.hi), 5),
        })
    return {**envelope([coef_src, elast_src]), "families": families}


def _class_values(root: Path) -> list[dict]:
    frame = _read(root, "deploy/bundle/tables/class_values.csv")
    return [{"outcome": str(row.outcome), "rv": round(float(row.rv_x_mean), 5)} for row in frame.itertuples(index=False)]


def _stub_split(left: float, right: float) -> dict:
    return {
        "split_feature": 0,
        "threshold": 0.0,
        "decision_type": "<=",
        "default_left": True,
        "missing_type": "None",
        "left_child": {"leaf_index": 0, "leaf_value": left},
        "right_child": {"leaf_index": 1, "leaf_value": right},
    }


def _model(root: Path, name: str, features: list[str], families: list[str]) -> dict:
    src = "deploy/bundle/tables/class_values.csv"
    classes = _class_values(root)
    outcome_trees = [
        {"tree_index": i, "tree_structure": _stub_split(0.0, 0.0)} for i in range(len(classes))
    ]
    return {
        **envelope([src]),
        "name": name,
        "features": list(features),
        "categories": {"pitch_family": families},
        "class_values": classes,
        "plus": {"center": 100.0, "spread": 10.0, "reference": "park-neutral"},
        "outcome": {"num_class": len(classes), "trees": outcome_trees},
        "contact": {"trees": [{"tree_index": 0, "tree_structure": {"leaf_index": 0, "leaf_value": 0.0}}]},
    }


def _pitcher_docs(root: Path, staff_ids: set[str]) -> dict[str, dict]:
    season_src = "reports/leaderboards/pitcher_season.csv"
    pitch_src = "reports/leaderboards/pitcher_pitch.csv"
    seasons = _read(root, season_src)
    pitches = _read(root, pitch_src)
    seasons = seasons[seasons["pitcher_anon_id"].isin(staff_ids)]
    pitches = pitches[pitches["pitcher_anon_id"].isin(staff_ids)]
    docs = {}
    pitch_cols = [
        "pitch_id", "pitch_family", "shape", "pitches", "usage", "velo", "ivb", "hb", "spin",
        "stuff_plus", "stuff_plus_harp_helu", "stuff_plus_own_air", "location_plus", "pitching_plus",
        "delta_cdmx",
    ]
    for pitcher_id, group in seasons.groupby("pitcher_anon_id", sort=True):
        season_rows = []
        for row in group.sort_values("year").itertuples(index=False):
            arsenal = pitches[(pitches["pitcher_anon_id"] == pitcher_id) & (pitches["year"] == row.year)]
            season_rows.append({
                "year": int(row.year),
                "pitches": int(row.pitches),
                "throws": str(row.throws),
                "stuff_plus": round(float(row.stuff_plus), 5),
                "stuff_plus_harp_helu": round(float(row.stuff_plus_harp_helu), 5),
                "stuff_plus_own_air": round(float(row.stuff_plus_own_air), 5),
                "location_plus": round(float(row.location_plus), 5),
                "pitching_plus": round(float(row.pitching_plus), 5),
                "delta_cdmx": round(float(row.delta_cdmx), 5),
                "arsenal": str(row.arsenal),
                "stuff_plus_percentile": round(float(row.stuff_plus_percentile), 5),
                "arsenal_pitches": _records(arsenal[pitch_cols].sort_values("pitch_id")),
            })
        docs[f"pitcher/{pitcher_id}.json"] = {
            **envelope([season_src, pitch_src]),
            "id": str(pitcher_id),
            "seasons": season_rows,
        }
    return docs


def build_mock(root: Path | None = None) -> dict[str, dict]:
    root = root or repo_root()
    physics = _physics(root)
    families = [row["pitch_family"] for row in physics["families"]]
    staff = _staff(root)
    staff_ids = {p["pitcher_anon_id"] for franchise in staff["franchises"] for p in franchise["pitchers"]}
    docs = {
        "parks.json": _parks(root),
        "shapes.json": _shapes(root),
        "leaderboard.json": _leaderboard(root),
        "staff.json": staff,
        "validation.json": _validation(root),
        "physics.json": physics,
        "models/stuff.json": _model(root, "stuff", STUFF_FEATURES_INVARIANT, families),
        "models/location.json": _model(root, "location", LOCATION_FEATURES, families),
        "models/pitching.json": _model(root, "pitching", list(PITCHING_FEATURES), families),
    }
    docs.update(_pitcher_docs(root, staff_ids))
    for doc in docs.values():
        assert_aggregate(doc)
    return docs


def dir_mb(path: Path) -> float:
    return sum(p.stat().st_size for p in path.rglob("*") if p.is_file()) / 1e6


def write_mock(out: Path, root: Path | None = None) -> dict[str, dict]:
    docs = build_mock(root)
    for rel, doc in docs.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    size = dir_mb(out)
    if size > MAX_MB:
        raise LeakError(f"{out} pesa {size:.1f} MB > {MAX_MB:.0f} MB")
    public = out.parent if out.name == "mock" else None
    if public is not None and public.name == "data":
        total = dir_mb(public)
        if total > MAX_MB:
            raise LeakError(f"{public} pesa {total:.1f} MB > {MAX_MB:.0f} MB")
    return docs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exporta el contrato web (mocks agregados).")
    parser.add_argument("--mock", action="store_true", help="escribe web/public/data/mock desde reports/")
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args(argv)
    if not args.mock:
        parser.error("pasa --mock; el export real es HACK-050")
    out = args.out or (repo_root() / "web" / "public" / "data" / "mock")
    docs = write_mock(out)
    print(f"WEB_MOCK_OK files={len(docs)} dir={out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
