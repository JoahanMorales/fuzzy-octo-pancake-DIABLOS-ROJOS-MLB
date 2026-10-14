"""Perfil de prospecto o agente libre: arsenal → Stuff+ en Harp Helú, comparables y veredicto.

La puntuación sale solo de ``api.predict_pitch`` (que delega en ``serving`` cuando hay bundle).
El índice a prueba de altura de un prospecto no es el índice EB de ``sensitivity.py``: ese exige
splits observados que un brazo de afuera no tiene. Aquí el índice es el Δ del modelo recentrado
en la media de la liga (``reports/leaderboards/pitcher_season.csv``).
"""
from __future__ import annotations

from dataclasses import replace
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from stuffplus import config
from stuffplus.api import PitchInput, predict_pitch
from stuffplus.features.shapes import shape_rule
from stuffplus.schema import FASTBALL_TYPES, PITCH_TYPES

VERDICTS = ("Firmar", "Desarrollar", "Evitar para casa")
# Mitad del supuesto de temporada de abridor (2,500 lanzamientos) en
# reports/business_value/summary.md. No es una carga medida en casa.
HOME_PITCHES = 1250
_MIN_PITCHES = 2
_MAX_PITCHES = 5

_TRACKMAN = {
    "AutoPitchType": "pitch_type",
    "PitcherThrows": "throws",
    "RelSpeed": "velo",
    "SpinRate": "spin_rate",
    "SpinAxis": "spin_axis",
    "InducedVertBreak": "ivb",
    "HorzBreak": "hb",
    "RelHeight": "rel_height",
    "RelSide": "rel_side",
    "Extension": "extension",
}


def evaluate_arsenal(
    pitches,
    *,
    home_pitches: int = HOME_PITCHES,
    seasons: pd.DataFrame | None = None,
    pitch_table: pd.DataFrame | None = None,
    shapes: pd.DataFrame | None = None,
    per_point: float | None = None,
    runs_per_win_home: float | None = None,
) -> dict[str, Any]:
    """Evalúa 2–5 lanzamientos, o un CSV/DataFrame en formato Trackman.

    Devuelve Stuff+ por lanzamiento y del arsenal en Harp Helú y a nivel del mar (neutral),
    el índice a prueba de altura, la bandera de riesgo de HR, 5 comparables LMB anonimizados,
    carreras esperadas en una temporada en casa y un veredicto de ``VERDICTS``.
    """
    parsed = _parse(pitches)
    league = _league(seasons, pitch_table, shapes, per_point, runs_per_win_home)
    scored = [_score(p, usage) for p, usage in _with_fastball(parsed)]
    arsenal = _aggregate(scored)
    index = 100.0 + arsenal["delta_cdmx"] - league["mean_delta"]
    hr_risk, hr_shape, hr_delta = _hr_risk(scored, league["shapes"])
    primary = max(scored, key=lambda row: (row["usage"], row["velo"]))
    comps = _comparables(primary, league["pitches"], league["seasons"])
    runs = (arsenal["stuff_plus_harp_helu"] - 100.0) * league["per_point"] * int(home_pitches)
    verdict = _verdict(
        arsenal["stuff_plus_harp_helu"], index, hr_risk, league["p25"], league["p75"],
    )
    demo = any(row["demo_data"] for row in scored)
    return {
        "pitches": scored,
        "arsenal": arsenal,
        "altitude_proof_index": round(index, 1),
        "index_kind": "model_delta_vs_league",
        "league_mean_delta": round(league["mean_delta"], 3),
        "hr_risk": hr_risk,
        "hr_risk_shape": hr_shape,
        "hr_delta": None if hr_delta is None else round(hr_delta, 3),
        "league_hr_delta": None if league["hr_league"] is None else round(league["hr_league"], 3),
        "comparables": comps,
        "comparable_pitch": {"pitch_type": primary["pitch_type"], "shape": primary["shape"]},
        "runs_saved_home": round(runs, 2),
        "wins_saved_home": round(runs / league["rpw_home"], 3),
        "home_pitches": int(home_pitches),
        "runs_per_point": league["per_point"],
        "runs_per_win_home": league["rpw_home"],
        "verdict": verdict,
        "thresholds": {"p25": round(league["p25"], 2), "p75": round(league["p75"], 2)},
        "demo_data": demo,
        "sources": {
            "stuff": "stuffplus.api.predict_pitch",
            "index": "reports/leaderboards/pitcher_season.csv (delta_cdmx, ponderado por lanzamientos)",
            "hr": "reports/altitude_delta/delta_by_shape.csv (delta_hr_per_fb_pct)",
            "runs": "reports/business_value/runs_per_point_direct.csv (Stuff+, rv_x)",
            "wins": "reports/business_value/runs_per_win.csv (Extreme Altitude)",
            "comparables": "reports/leaderboards/pitcher_pitch.csv + pitcher_season.csv",
            "home_pitches": "supuesto: 1,250 = mitad de 2,500 lanzamientos de temporada (reports/business_value/summary.md)",
        },
    }


def _parse(pitches) -> list[tuple[PitchInput, float | None]]:
    if isinstance(pitches, (str, Path)):
        frame = pd.read_csv(pitches)
        rows = _from_frame(frame)
    elif isinstance(pitches, pd.DataFrame):
        rows = _from_frame(pitches)
    else:
        rows = [_one(item) for item in pitches]
    if not _MIN_PITCHES <= len(rows) <= _MAX_PITCHES:
        raise ValueError(f"el arsenal debe tener entre {_MIN_PITCHES} y {_MAX_PITCHES} lanzamientos (llegaron {len(rows)})")
    usages = _usages([u for _, u in rows])
    return [(p, u) for (p, _), u in zip(rows, usages)]


def _one(item) -> tuple[PitchInput, float | None]:
    if isinstance(item, PitchInput):
        usage = item.arsenal.get("usage") if item.arsenal else None
        return item, None if usage is None else float(usage)
    if not isinstance(item, Mapping):
        raise TypeError("cada lanzamiento debe ser PitchInput o un diccionario")
    if "AutoPitchType" in item or "RelSpeed" in item:
        return _from_mapping(item)
    data = dict(item)
    usage = data.pop("usage", None)
    arsenal = dict(data.get("arsenal") or {})
    if usage is None and "usage" in arsenal:
        usage = arsenal.get("usage")
    return PitchInput(**data), None if usage is None else float(usage)


def _from_mapping(row: Mapping[str, Any]) -> tuple[PitchInput, float | None]:
    values = {name: row[src] for src, name in _TRACKMAN.items() if src in row and pd.notna(row[src])}
    if "pitch_type" not in values and "pitch_type" in row:
        values["pitch_type"] = row["pitch_type"]
    for name in ("pitch_type", "throws", "velo", "spin_rate", "spin_axis", "ivb", "hb"):
        if name not in values and name in row and pd.notna(row[name]):
            values[name] = row[name]
    if "rho_measured" in row and pd.notna(row["rho_measured"]):
        values["rho_measured"] = float(row["rho_measured"])
    usage = row["usage"] if "usage" in row and pd.notna(row["usage"]) else None
    return _build(values), None if usage is None else float(usage)


def _from_frame(df: pd.DataFrame) -> list[tuple[PitchInput, float | None]]:
    if df.empty:
        raise ValueError("el CSV no trae lanzamientos")
    trackman = "AutoPitchType" in df.columns or "RelSpeed" in df.columns
    if trackman and (len(df) > _MAX_PITCHES or df.get("AutoPitchType", pd.Series(dtype=str)).nunique(dropna=True) < len(df)):
        return _aggregate_trackman(df)
    return [_from_mapping(row) for row in df.to_dict(orient="records")]


def _aggregate_trackman(df: pd.DataFrame) -> list[tuple[PitchInput, float | None]]:
    work = df.copy()
    if "AutoPitchType" not in work.columns:
        raise ValueError("el CSV Trackman necesita la columna AutoPitchType")
    work["AutoPitchType"] = work["AutoPitchType"].replace({"Sweeper": "Slider"})
    work = work[work["AutoPitchType"].isin(PITCH_TYPES)]
    if "PitcherThrows" not in work.columns:
        raise ValueError("el CSV Trackman necesita la columna PitcherThrows")
    grouped = []
    for ptype, sub in work.groupby("AutoPitchType", observed=True):
        throws = str(sub["PitcherThrows"].mode(dropna=True).iloc[0])
        values = {
            "pitch_type": str(ptype),
            "throws": throws,
            "velo": float(sub["RelSpeed"].mean()),
            "spin_rate": float(sub["SpinRate"].mean()),
            "spin_axis": _circular_mean(sub["SpinAxis"].to_numpy(float)),
            "ivb": float(sub["InducedVertBreak"].mean()),
            "hb": float(sub["HorzBreak"].mean()),
        }
        for src, name, default in (("RelHeight", "rel_height", None), ("RelSide", "rel_side", None), ("Extension", "extension", None)):
            if src in sub.columns and sub[src].notna().any():
                values[name] = float(sub[src].mean())
        grouped.append((_build(values), float(len(sub))))
    grouped.sort(key=lambda item: item[1], reverse=True)
    grouped = grouped[:_MAX_PITCHES]
    if len(grouped) < _MIN_PITCHES:
        raise ValueError(f"el CSV quedó con {len(grouped)} tipos de lanzamiento; hacen falta al menos {_MIN_PITCHES}")
    return grouped


def _build(values: Mapping[str, Any]) -> PitchInput:
    missing = [name for name in ("pitch_type", "throws", "velo", "spin_rate", "spin_axis", "ivb", "hb") if name not in values]
    if missing:
        raise ValueError(f"faltan columnas para armar el lanzamiento: {', '.join(missing)}")
    kwargs = dict(values)
    kwargs["spin_axis"] = float(kwargs["spin_axis"]) % 360
    return PitchInput(**kwargs)


def _circular_mean(degrees: np.ndarray) -> float:
    ang = np.deg2rad(np.asarray(degrees, float))
    ang = ang[np.isfinite(ang)]
    if len(ang) == 0:
        raise ValueError("SpinAxis vacío")
    return float(np.rad2deg(np.arctan2(np.sin(ang).mean(), np.cos(ang).mean())) % 360)


def _usages(raw: Sequence[float | None]) -> list[float]:
    if any(u is not None and u < 0 for u in raw):
        raise ValueError("el uso no puede ser negativo")
    if all(u is None for u in raw):
        return [1.0 / len(raw)] * len(raw)
    filled = [0.0 if u is None else float(u) for u in raw]
    total = sum(filled)
    if total <= 0:
        return [1.0 / len(raw)] * len(raw)
    return [u / total for u in filled]


def _with_fastball(rows: list[tuple[PitchInput, float]]) -> list[tuple[PitchInput, float]]:
    fastballs = [(p, u) for p, u in rows if p.pitch_type in FASTBALL_TYPES]
    if not fastballs:
        return rows
    primary = max(fastballs, key=lambda item: (item[1], item[0].velo))[0]
    ctx = {"fb_velo": primary.velo, "fb_ivb": primary.ivb, "fb_hb": primary.hb}
    out = []
    for pitch, usage in rows:
        arsenal = dict(pitch.arsenal)
        arsenal.update(ctx)
        arsenal["usage"] = usage
        out.append((replace(pitch, arsenal=arsenal), usage))
    return out


def _score(pitch: PitchInput, usage: float) -> dict[str, Any]:
    pred = predict_pitch(pitch, rho="harp_helu", flavour="environment")
    shape = _shape(pitch)
    stuff_hh = float(pred["stuff_plus"])
    stuff_n = float(pred["stuff_plus_neutral"])
    return {
        "pitch_type": pitch.pitch_type,
        "shape": shape,
        "throws": pitch.throws,
        "velo": pitch.velo,
        "ivb": pitch.ivb,
        "hb": pitch.hb,
        "usage": round(usage, 4),
        "stuff_plus_harp_helu": stuff_hh,
        "stuff_plus_neutral": stuff_n,
        "delta_cdmx": round(stuff_hh - stuff_n, 1),
        "location_plus": pred.get("location_plus"),
        "pitching_plus": pred.get("pitching_plus"),
        "demo_data": bool(pred.get("demo_data", True)),
    }


def _shape(pitch: PitchInput) -> str:
    rho = float(pitch.rho_measured)
    if rho <= 0:
        raise ValueError("rho_measured debe ser positivo")
    ivb_sea = pitch.ivb / rho
    hb_sea = pitch.hb / rho
    sign = 1.0 if pitch.throws == "Right" else -1.0
    label = shape_rule([pitch.pitch_type], [ivb_sea], [hb_sea * sign], [pitch.velo])
    return str(label[0])


def _aggregate(rows: Sequence[dict[str, Any]]) -> dict[str, Any]:
    def mean(key: str):
        vals = [(row["usage"], row[key]) for row in rows if row[key] is not None]
        if not vals:
            return None
        return round(sum(u * v for u, v in vals), 1)

    return {
        "stuff_plus_harp_helu": mean("stuff_plus_harp_helu"),
        "stuff_plus_neutral": mean("stuff_plus_neutral"),
        "delta_cdmx": mean("delta_cdmx"),
        "location_plus": mean("location_plus"),
        "pitching_plus": mean("pitching_plus"),
    }


def _hr_risk(rows: Sequence[dict[str, Any]], shapes: pd.DataFrame) -> tuple[bool, str | None, float | None]:
    table = shapes.set_index("shape")["delta_hr_per_fb_pct"]
    weights = shapes.set_index("shape")["pitches"]
    known = weights[weights.index.isin(table.index)]
    if known.sum() <= 0:
        return False, None, None
    league = float(np.average(table.loc[known.index].to_numpy(float), weights=known.to_numpy(float)))
    used = [(row["usage"], float(table[row["shape"]]), row["shape"]) for row in rows if row["shape"] in table.index]
    if not used:
        return False, None, None
    arsenal = sum(u * d for u, d, _ in used) / sum(u for u, _, _ in used)
    driver = max(used, key=lambda item: (item[1], item[0]))
    return bool(arsenal > league), (driver[2] if arsenal > league else None), float(arsenal)


def _comparables(primary: dict[str, Any], pitches: pd.DataFrame, seasons: pd.DataFrame) -> list[dict[str, Any]]:
    pool = pitches.merge(
        seasons[["pitcher_anon_id", "year", "throws"]].drop_duplicates(),
        on=["pitcher_anon_id", "year"],
        how="left",
    )
    pool = pool[pool["pitch_family"].astype(str) == primary["pitch_type"]]
    same_hand = pool[pool["throws"].astype(str) == primary["throws"]]
    if len(same_hand) >= 5:
        pool = same_hand
    if pool.empty:
        return []
    cols = ["velo", "ivb", "hb"]
    mu = pool[cols].mean()
    sd = pool[cols].std(ddof=0).replace(0, np.nan).fillna(1.0)
    point = (np.array([primary["velo"], primary["ivb"], primary["hb"]], float) - mu.to_numpy(float)) / sd.to_numpy(float)
    z = (pool[cols] - mu) / sd
    dist = np.sqrt(((z.to_numpy(float) - point) ** 2).sum(axis=1))
    ranked = pool.assign(distance=dist).sort_values(["distance", "pitcher_anon_id", "year"]).head(5)
    out = []
    for row in ranked.itertuples(index=False):
        out.append({
            "pitcher_anon_id": str(row.pitcher_anon_id),
            "year": int(row.year),
            "shape": str(row.shape),
            "pitch_family": str(row.pitch_family),
            "distance": round(float(row.distance), 3),
            "stuff_plus_harp_helu": round(float(row.stuff_plus_harp_helu), 1),
            "velo": round(float(row.velo), 1),
        })
    return out


def _verdict(stuff_hh: float, index: float, hr_risk: bool, p25: float, p75: float) -> str:
    if stuff_hh >= p75 and index >= 100 and not hr_risk:
        return "Firmar"
    if stuff_hh < p25 or (hr_risk and index < 100):
        return "Evitar para casa"
    return "Desarrollar"


def _league(seasons, pitch_table, shapes, per_point, rpw) -> dict[str, Any]:
    seasons = _read_seasons() if seasons is None else seasons
    pitches = _read_pitches() if pitch_table is None else pitch_table
    shapes = _read_shapes() if shapes is None else shapes
    if per_point is None or rpw is None:
        loaded_point, loaded_rpw = _read_value()
        per_point = loaded_point if per_point is None else per_point
        rpw = loaded_rpw if rpw is None else rpw
    weights = seasons["pitches"].to_numpy(float)
    league_delta = float(np.average(seasons["delta_cdmx"].to_numpy(float), weights=weights))
    hr_weights = shapes["pitches"].to_numpy(float)
    hr_league = float(np.average(shapes["delta_hr_per_fb_pct"].to_numpy(float), weights=hr_weights))
    p25, p75 = (float(v) for v in seasons["stuff_plus_harp_helu"].quantile([0.25, 0.75]))
    return {
        "seasons": seasons, "pitches": pitches, "shapes": shapes,
        "mean_delta": league_delta, "hr_league": hr_league,
        "p25": p25, "p75": p75, "per_point": float(per_point), "rpw_home": float(rpw),
    }


def _reports(name: str) -> Path:
    path = config.repo_root() / "reports" / name
    if not path.is_file():
        raise FileNotFoundError(f"no está el reporte {path}")
    return path


def _read_seasons() -> pd.DataFrame:
    return pd.read_csv(_reports("leaderboards/pitcher_season.csv"))


def _read_pitches() -> pd.DataFrame:
    return pd.read_csv(_reports("leaderboards/pitcher_pitch.csv"))


def _read_shapes() -> pd.DataFrame:
    return pd.read_csv(_reports("altitude_delta/delta_by_shape.csv"))


def _read_value() -> tuple[float, float]:
    points = pd.read_csv(_reports("business_value/runs_per_point_direct.csv"))
    row = points[(points["escala"] == "Stuff+") & (points["objetivo"] == "rv_x")].iloc[0]
    wins = pd.read_csv(_reports("business_value/runs_per_win.csv"))
    home = wins[wins["entorno"] == "Extreme Altitude"].iloc[0]
    return float(row["carreras_por_punto_lanzamiento"]), float(home["carreras_por_victoria"])
