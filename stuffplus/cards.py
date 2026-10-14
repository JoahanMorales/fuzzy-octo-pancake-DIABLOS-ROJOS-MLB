"""Ficha de lanzador (una por pitcher-temporada) a partir de agregados. HACK-034.

No lee el parquet crudo ni dibuja scatters de pitcheos. Los números salen de
``reports/leaderboards/`` (HACK-016), ``reports/pitcher_sensitivity/`` (HACK-018)
y ``reports/altitude_delta/delta_by_shape.csv`` (HACK-015). El texto de las
recomendaciones sigue el tono de HACK-019 (una frase en español con su fuente).
"""
from __future__ import annotations

import hashlib
import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import font_manager
from matplotlib.patches import FancyArrowPatch

from stuffplus import config
from stuffplus.physics.constants import RHO_HARP_HELU

CARD_W, CARD_H, DPI = 1600, 900, 100
DECK_ROLES = (
    ("deck_mayor_indice", "altitude_proof_index", False),
    ("deck_menor_indice", "altitude_proof_index", True),
    ("deck_mayor_stuff_harp", "stuff_plus_harp_helu", False),
)
DIABLOS_FRANCHISES = (5, 11)
MAX_PITCHES = 7

_SEASON = ["pitcher_anon_id", "year", "throws", "pitches", "stuff_plus_harp_helu"]
_PITCH = ["pitcher_anon_id", "year", "pitch_id", "pitch_family", "shape", "usage", "velo", "ivb", "hb",
          "stuff_plus", "stuff_plus_harp_helu", "location_plus", "pitching_plus", "delta_cdmx"]
_SENS_P = ["pitcher_anon_id", "year", "altitude_proof_index", "driver_family", "physical_reason"]
_SENS_K = ["pitcher_anon_id", "year", "pitch_key", "pitch_family", "delta_ivb_in", "delta_hb_arm_in"]
_SHAPE = ["shape", "delta_ivb_in", "delta_hb_arm_in", "physics"]


def hb_arm(hb: float, throws: str) -> float:
    """HorzBreak crudo al marco del brazo: positivo = hacia el lado del brazo.

    El leaderboard guarda ``HorzBreak`` sin firmar por mano. Los Δ de HACK-015/018
    (``delta_hb_arm_in``) ya están en ese marco. Un zurdo se refleja.
    """
    sign = -1.0 if str(throws).lower().startswith("l") else 1.0
    return float(hb) * sign


def pitch_key(pitcher_anon_id: str, year: int, pitch_id) -> str:
    """Llave completa. No se usa el sufijo: ``…_1`` y ``…_11`` no deben colisionar."""
    return f"{pitcher_anon_id}_{int(year)}_{int(pitch_id)}"


def _need(frame: pd.DataFrame, cols: list[str], name: str) -> pd.DataFrame:
    missing = [c for c in cols if c not in frame.columns]
    if missing:
        raise ValueError(f"{name} sin columnas {missing}")
    return frame


def _font() -> str:
    have = {f.name for f in font_manager.fontManager.ttflist}
    for name in ("Arial Narrow", "Arial", "DejaVu Sans"):
        if name in have:
            return name
    return "DejaVu Sans"


def _tokens(tokens: dict | None) -> dict:
    if tokens is not None:
        return tokens
    from app.theme import TOKENS
    return TOKENS


def load_tables(reports: Path | None = None) -> dict[str, pd.DataFrame]:
    """Lee solo CSV agregados. Falla con FileNotFoundError si falta alguno."""
    root = Path(reports) if reports is not None else config.REPORTS_DIR
    paths = {
        "pitcher_season": root / "leaderboards" / "pitcher_season.csv",
        "pitcher_pitch": root / "leaderboards" / "pitcher_pitch.csv",
        "sensitivity_pitchers": root / "pitcher_sensitivity" / "pitchers.csv",
        "sensitivity_pitches": root / "pitcher_sensitivity" / "pitches.csv",
        "shapes": root / "altitude_delta" / "delta_by_shape.csv",
    }
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError("Faltan agregados: " + ", ".join(missing))
    tables = {name: pd.read_csv(path) for name, path in paths.items()}
    tables["paths"] = paths
    return tables


def _as_bool(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    return series.astype(str).str.lower().isin(("true", "1", "yes"))


def deck_example_keys(tables: dict[str, pd.DataFrame]) -> list[tuple[str, int, str]]:
    """Tres pitcher-temporadas para el deck: mayor índice, menor índice, mayor Stuff+ en Harp Helú."""
    season = _need(tables["pitcher_season"], _SEASON, "pitcher_season")
    sens = _need(tables["sensitivity_pitchers"], _SENS_P, "sensitivity_pitchers")
    both = season.merge(sens, on=["pitcher_anon_id", "year"], how="inner")
    if "eligible" in both.columns:
        both = both[_as_bool(both["eligible"])]
    both = both[np.isfinite(both["altitude_proof_index"]) & np.isfinite(both["stuff_plus_harp_helu"])]
    if both.empty:
        raise ValueError("No hay pitcher-temporadas en común entre leaderboard y sensibilidad")
    picked: list[tuple[str, int]] = []
    out: list[tuple[str, int, str]] = []
    for role, col, ascending in DECK_ROLES:
        ordered = both.sort_values([col, "pitcher_anon_id", "year"], ascending=[ascending, True, True])
        chosen = None
        for row in ordered.itertuples(index=False):
            key = (str(row.pitcher_anon_id), int(row.year))
            if key not in picked:
                chosen = key
                break
        if chosen is None:
            raise ValueError(f"No hay un ejemplo distinto para {role}")
        picked.append(chosen)
        out.append((chosen[0], chosen[1], role))
    return out


def _shape_delta(shapes: pd.DataFrame, shape: str) -> tuple[float, float, str] | None:
    hit = shapes[shapes["shape"].astype(str) == str(shape)]
    if hit.empty:
        return None
    row = hit.iloc[0]
    if not (np.isfinite(row["delta_ivb_in"]) and np.isfinite(row["delta_hb_arm_in"])):
        return None
    return float(row["delta_ivb_in"]), float(row["delta_hb_arm_in"]), str(row.get("physics", ""))


def build_card(pitcher_anon_id: str, year: int, tables: dict[str, pd.DataFrame]) -> dict:
    """Arsenal, flechas hacia la CDMX, índice y tres recomendaciones. Sin PitchUID."""
    season = _need(tables["pitcher_season"], _SEASON, "pitcher_season")
    pitches = _need(tables["pitcher_pitch"], _PITCH, "pitcher_pitch")
    sens_p = _need(tables["sensitivity_pitchers"], _SENS_P, "sensitivity_pitchers")
    sens_k = _need(tables["sensitivity_pitches"], _SENS_K, "sensitivity_pitches")
    shapes = _need(tables["shapes"], _SHAPE, "shapes")
    pid, yr = str(pitcher_anon_id), int(year)
    who = season[(season["pitcher_anon_id"].astype(str) == pid) & (season["year"].astype(int) == yr)]
    if who.empty:
        raise KeyError(f"Sin fila de temporada para {pid} {yr}")
    arm = pitches[(pitches["pitcher_anon_id"].astype(str) == pid) & (pitches["year"].astype(int) == yr)]
    if arm.empty:
        raise KeyError(f"Sin arsenal agregado para {pid} {yr}")
    arm = arm.sort_values("usage", ascending=False)
    truncated = int(len(arm) > MAX_PITCHES)
    arm = arm.head(MAX_PITCHES)
    throws = str(who.iloc[0]["throws"])
    sens_row = sens_p[(sens_p["pitcher_anon_id"].astype(str) == pid) & (sens_p["year"].astype(int) == yr)]
    index = driver = reason = None
    if not sens_row.empty and np.isfinite(sens_row.iloc[0]["altitude_proof_index"]):
        index = float(sens_row.iloc[0]["altitude_proof_index"])
        driver = str(sens_row.iloc[0]["driver_family"])
        reason = str(sens_row.iloc[0]["physical_reason"])
    keys = sens_k[(sens_k["pitcher_anon_id"].astype(str) == pid) & (sens_k["year"].astype(int) == yr)]
    rows = []
    for rec in arm.itertuples(index=False):
        key = pitch_key(pid, yr, rec.pitch_id)
        match = keys[keys["pitch_key"].astype(str) == key]
        delta = None
        delta_source = ""
        physics = ""
        same_family = (len(match) == 1 and str(match.iloc[0]["pitch_family"]) == str(rec.pitch_family))
        if same_family and np.isfinite(match.iloc[0]["delta_ivb_in"]) and np.isfinite(match.iloc[0]["delta_hb_arm_in"]):
            delta = (float(match.iloc[0]["delta_ivb_in"]), float(match.iloc[0]["delta_hb_arm_in"]))
            delta_source = "reports/pitcher_sensitivity/pitches.csv · delta_ivb_in, delta_hb_arm_in"
        else:
            shaped = _shape_delta(shapes, rec.shape)
            if shaped is not None:
                delta = (shaped[0], shaped[1])
                physics = shaped[2]
                delta_source = "reports/altitude_delta/delta_by_shape.csv · delta_ivb_in, delta_hb_arm_in"
        x0 = hb_arm(rec.hb, throws)
        y0 = float(rec.ivb)
        rows.append({
            "pitch_id": int(rec.pitch_id),
            "pitch_key": key,
            "shape": str(rec.shape),
            "pitch_family": str(rec.pitch_family),
            "usage": float(rec.usage),
            "velo": float(rec.velo),
            "ivb": y0,
            "hb_arm": x0,
            "stuff_plus": float(rec.stuff_plus),
            "stuff_plus_harp_helu": float(rec.stuff_plus_harp_helu),
            "location_plus": float(rec.location_plus),
            "pitching_plus": float(rec.pitching_plus),
            "delta_cdmx": float(rec.delta_cdmx),
            "delta_ivb": None if delta is None else delta[0],
            "delta_hb_arm": None if delta is None else delta[1],
            "arrow": delta is not None,
            "delta_source": delta_source or "sin Δ de movimiento en los agregados",
            "physics": physics,
            "x0": x0, "y0": y0,
            "x1": None if delta is None else x0 + delta[1],
            "y1": None if delta is None else y0 + delta[0],
        })
    recommendations = _recommendations(rows, index, driver, reason)
    return {
        "pitcher_anon_id": pid,
        "year": yr,
        "throws": throws,
        "season_pitches": int(who.iloc[0]["pitches"]),
        "truncated": truncated,
        "rho": float(RHO_HARP_HELU),
        "altitude_proof_index": index,
        "driver_family": driver,
        "physical_reason": reason,
        "arsenal": rows,
        "recommendations": recommendations,
        "sources": {
            "arsenal": "reports/leaderboards/pitcher_pitch.csv (uso, velo, IVB, HB, Stuff+ neutral, Stuff+ Harp Helú, Location+, Pitching+; encogido hacia 100)",
            "index": "reports/pitcher_sensitivity/pitchers.csv · altitude_proof_index = 100 + delta EB − media de la liga",
            "rho": "stuffplus/physics/constants.py · RHO_HARP_HELU",
        },
    }


def _label(row: dict, rows: list[dict]) -> str:
    """Si hay dos pitches con la misma forma, el uso los distingue."""
    if sum(r["shape"] == row["shape"] for r in rows) > 1:
        return f"{row['shape']} · {row['usage'] * 100:.0f}%"
    return row["shape"]


def _recommendations(rows: list[dict], index: float | None, driver: str | None, reason: str | None) -> list[dict]:
    best = max(rows, key=lambda r: (r["stuff_plus_harp_helu"], -r["usage"]))
    worst = min(rows, key=lambda r: (r["delta_cdmx"], -r["usage"]))
    # La frase física es la del pitch que se recorta, no la del pitch que mueve el índice.
    if worst["delta_ivb"] is not None and worst["delta_hb_arm"] is not None:
        physics = (f"En ese pitch el movimiento cambia IVB {worst['delta_ivb']:+.1f} pulgadas "
                   f"y HB lado del brazo {worst['delta_hb_arm']:+.1f} pulgadas.")
        physics_source = worst["delta_source"]
    else:
        physics = worst["physics"] or "Sin Δ de movimiento para ese pitch en los agregados."
        physics_source = worst["delta_source"]
    third_text = (
        f"Índice a prueba de altitud {index:.0f}. 100 es la media de la liga; lo mueve {driver}."
        if index is not None else
        "Sin índice a prueba de altitud en el agregado de sensibilidad."
    )
    if index is not None and reason:
        short = " ".join(str(reason).split())
        if len(short) > 90:
            short = short[:87] + "…"
        third_text += " " + short
    third_source = (
        "reports/pitcher_sensitivity/pitchers.csv · altitude_proof_index, physical_reason"
        if index is not None else
        "reports/pitcher_sensitivity/pitchers.csv (sin fila para este lanzador)"
    )
    return [
        {"text": (f"Apóyate en {_label(best, rows)} ({best['usage'] * 100:.0f}% de uso): "
                  f"Stuff+ Harp Helú {best['stuff_plus_harp_helu']:.0f} (neutral {best['stuff_plus']:.0f})."),
         "source": "reports/leaderboards/pitcher_pitch.csv · stuff_plus_harp_helu, stuff_plus"},
        {"text": (f"Recorta en casa {_label(worst, rows)}: Δ {worst['delta_cdmx']:+.1f} "
                  f"(Harp Helú − neutral). {physics}"),
         "source": f"reports/leaderboards/pitcher_pitch.csv · delta_cdmx; {physics_source}"},
        {"text": third_text, "source": third_source},
    ]


def _paint(fig, card: dict, tokens: dict, font: str) -> None:
    bg, panel, line, text, muted = tokens["bg"], tokens["panel"], tokens["line"], tokens["text"], tokens["muted"]
    red, white = tokens["red"], tokens["white"]
    fig.patch.set_facecolor(bg)
    gs = fig.add_gridspec(
        3, 2, height_ratios=[1.35, 1.25, 0.62], width_ratios=[1.22, 1.0],
        left=0.04, right=0.97, top=0.78, bottom=0.04, wspace=0.18, hspace=0.42,
    )
    ax_table = fig.add_subplot(gs[0, 0])
    ax_move = fig.add_subplot(gs[0:2, 1])
    ax_recs = fig.add_subplot(gs[1, 0])
    ax_foot = fig.add_subplot(gs[2, :])
    for ax in (ax_table, ax_recs, ax_foot):
        ax.set_facecolor(bg)
        ax.axis("off")
    ax_move.set_facecolor(panel)
    hand = "zurdo" if str(card["throws"]).lower().startswith("l") else "derecho"
    idx = "—" if card["altitude_proof_index"] is None else f"{card['altitude_proof_index']:.0f}"
    fig.text(0.04, 0.955, "FICHA DEL LANZADOR", color=red, fontsize=18, fontname=font, fontweight="bold")
    fig.text(0.04, 0.915, f"{card['pitcher_anon_id']}   ·   {card['year']}   ·   {hand}",
             color=text, fontsize=13, fontname=font)
    fig.text(0.04, 0.875, f"Stuff+ neutral (nivel del mar)   ·   Stuff+ Harp Helú (entorno, ρ={card['rho']:.3f})",
             color=muted, fontsize=9, fontname=font)
    fig.text(0.97, 0.95, idx, color=white, fontsize=26, fontname=font, fontweight="bold", ha="right", va="top")
    fig.text(0.97, 0.885, "a prueba de altitud", color=muted, fontsize=9, fontname=font, ha="right", va="top")

    headers = ["Pitch", "Uso", "Velo", "IVB", "HB brazo", "Stuff+\nneutral", "Stuff+\nHarp Helú", "Location+", "Pitching+"]
    cells = []
    for row in card["arsenal"]:
        cells.append([
            _label(row, card["arsenal"]), f"{row['usage'] * 100:.0f}%", f"{row['velo']:.1f}", f"{row['ivb']:.1f}",
            f"{row['hb_arm']:.1f}", f"{row['stuff_plus']:.0f}", f"{row['stuff_plus_harp_helu']:.0f}",
            f"{row['location_plus']:.0f}", f"{row['pitching_plus']:.0f}",
        ])
    ax_table.text(0, 1.02, "Arsenal agregado", transform=ax_table.transAxes, color=text, fontsize=11,
                  fontname=font, va="bottom", clip_on=False)
    table = ax_table.table(cellText=cells, colLabels=headers, loc="upper left", cellLoc="center",
                           bbox=[0, 0, 1, 0.96])
    table.auto_set_font_size(False)
    table.set_fontsize(7.5)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor(line)
        cell.set_linewidth(0.4)
        cell.get_text().set_fontname(font)
        if r == 0:
            cell.set_facecolor(red)
            cell.get_text().set_color(white)
            cell.get_text().set_fontweight("bold")
        else:
            cell.set_facecolor(panel)
            cell.get_text().set_color(text)

    xs, ys = [], []
    for row in card["arsenal"]:
        xs.append(row["x0"])
        ys.append(row["y0"])
        if row["arrow"]:
            xs.append(row["x1"])
            ys.append(row["y1"])
            ax_move.add_patch(FancyArrowPatch(
                (row["x0"], row["y0"]), (row["x1"], row["y1"]),
                arrowstyle="-|>", mutation_scale=18, linewidth=2.0, color=red,
                shrinkA=2, shrinkB=0, zorder=2,
            ))
            ax_move.annotate(
                _label(row, card["arsenal"]), (row["x0"], row["y0"]),
                textcoords="offset points", xytext=(7, 6), color=text, fontsize=8, fontname=font, zorder=4,
            )
        else:
            ax_move.annotate(
                _label(row, card["arsenal"]) + " · sin Δ", (row["x0"], row["y0"]),
                textcoords="offset points", xytext=(7, 6), color=muted, fontsize=8, fontname=font, zorder=4,
            )
    ax_move.scatter([r["x0"] for r in card["arsenal"]], [r["y0"] for r in card["arsenal"]],
                    s=28, color=white, zorder=3)
    pad = 1.5
    ax_move.set_xlim(min(xs) - pad, max(xs) + pad + 2)
    ax_move.set_ylim(min(ys) - pad, max(ys) + pad)
    ax_move.set_aspect("equal", adjustable="box")
    ax_move.set_xlabel("HB lado del brazo (pulg.)", color=text, fontsize=9, fontname=font)
    ax_move.set_ylabel("IVB (pulg.)", color=text, fontsize=9, fontname=font)
    ax_move.set_title("Flecha hacia la CDMX\npunto blanco = nivel del mar · punta = CDMX", color=text, fontsize=11,
                      fontname=font, loc="left", pad=8)
    ax_move.tick_params(colors=muted, labelsize=8)
    for spine in ax_move.spines.values():
        spine.set_color(line)
    ax_move.grid(color=line, linewidth=0.4)

    ax_recs.text(0, 1.02, "Tres recomendaciones", transform=ax_recs.transAxes, color=text, fontsize=11,
                 fontname=font, va="bottom", clip_on=False)
    ax_recs.set_xlim(0, 1)
    ax_recs.set_ylim(0, 1)
    y = 0.98
    for i, rec in enumerate(card["recommendations"], start=1):
        body = textwrap.fill(f"{i}. {rec['text']}", width=62)
        ax_recs.text(0.0, y, body, color=text, fontsize=8, fontname=font, va="top")
        src = textwrap.shorten(f"Fuente: {rec['source']}", width=78, placeholder="…")
        ax_recs.text(0.0, y - 0.22, src, color=muted, fontsize=6.5, fontname=font, va="top")
        y -= 0.33

    missing = " Hay pitches sin Δ: no tenían fila de pitch ni de forma." if any(not r["arrow"] for r in card["arsenal"]) else ""
    foot = (
        f"Fuentes. Arsenal: {card['sources']['arsenal']}. "
        f"Índice: {card['sources']['index']}. ρ: {card['sources']['rho']}. "
        f"Flecha: origen blanco = nivel del mar; punta roja = ese punto más el Δ hacia Harp Helú "
        f"(HB del lado del brazo, {hand}). Temporada agregada: {card['season_pitches']} pitcheos.{missing}"
    )
    if card["truncated"]:
        foot += f" Se listan los {MAX_PITCHES} pitches de mayor uso."
    ax_foot.set_xlim(0, 1)
    ax_foot.set_ylim(0, 1)
    ax_foot.text(0.0, 0.98, "\n".join(textwrap.wrap(foot, width=148)), color=muted, fontsize=7.5,
                 fontname=font, va="top", clip_on=False)


def render_card(card: dict, tokens: dict | None = None):
    """Figura de exactamente 16×9 in a 100 dpi → 1600×900. Sin bbox_inches='tight'."""
    tokens = _tokens(tokens)
    font = _font()
    fig = plt.figure(figsize=(CARD_W / DPI, CARD_H / DPI), dpi=DPI, facecolor=tokens["bg"])
    _paint(fig, card, tokens, font)
    return fig


def _savefig(fig, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=DPI, facecolor=fig.get_facecolor())
    plt.close(fig)


def export_card(card: dict, directory: Path, tokens: dict | None = None) -> dict[str, Path]:
    directory = Path(directory)
    stem = f"{card['pitcher_anon_id']}_{card['year']}"
    png, pdf = directory / f"{stem}.png", directory / f"{stem}.pdf"
    _savefig(render_card(card, tokens), png)
    _savefig(render_card(card, tokens), pdf)
    return {"png": png, "pdf": pdf}


def _sha_tables(tables: dict[str, pd.DataFrame]) -> str:
    paths = tables.get("paths") or {}
    parts = []
    for name in ("pitcher_season", "pitcher_pitch", "sensitivity_pitchers", "sensitivity_pitches", "shapes"):
        path = paths.get(name)
        if isinstance(path, Path) and path.exists():
            digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
        else:
            digest = hashlib.sha256(tables[name].to_csv(index=False).encode()).hexdigest()[:12]
        parts.append(f"{name}:{digest}")
    return " ".join(parts)


def _staff_frame(loader) -> tuple[pd.DataFrame | None, str | None]:
    try:
        frame = loader() if loader is not None else _default_staff()
    except Exception as exc:  # noqa: BLE001 — sin mapa local el lote del staff no puede armarse
        return None, type(exc).__name__
    if frame is None or frame.empty:
        return None, "el staff candidato volvió vacío"
    return frame, None


def _default_staff() -> pd.DataFrame:
    from stuffplus.physics.parks import candidate_staff, load_maps

    return candidate_staff(load_maps(), list(DIABLOS_FRANCHISES))


def batch_export(out_dir: Path, tables: dict | None = None, tokens: dict | None = None,
                 staff_loader=None) -> pd.DataFrame:
    """Exporta PNG y PDF de los ejemplos del deck y, si hay mapa, del staff candidato.

    ``manifest.csv`` solo lista los ejemplos del deck. El staff no se escribe como CSV
    (``candidate_staff`` es de nivel de fila). Si el mapa no está, queda ``staff_missing.txt``.
    """
    out_dir = Path(out_dir)
    tables = tables if tables is not None else load_tables()
    digest = _sha_tables(tables)
    rows = []
    deck_dir = out_dir / "deck"
    for pid, year, role in deck_example_keys(tables):
        paths = export_card(build_card(pid, year, tables), deck_dir, tokens)
        rows.append({"role": role, "pitcher_anon_id": pid, "year": year,
                     "png": str(paths["png"].name), "pdf": str(paths["pdf"].name), "sources": digest})
    manifest = pd.DataFrame(rows)
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest.to_csv(out_dir / "manifest.csv", index=False)

    staff, err = _staff_frame(staff_loader)
    if err is not None:
        (out_dir / "staff_missing.txt").write_text(
            "No se exportó el staff candidato de Diablos (franquicias de menor densidad, "
            "reports/park_id/harp_helu.md). Falta el mapa local de equipos; no se usa el parquet "
            f"en esta corrida. Detalle: {err}\n",
            encoding="utf-8",
        )
        return manifest
    if (out_dir / "staff_missing.txt").exists():
        (out_dir / "staff_missing.txt").unlink()
    season_col = "season" if "season" in staff.columns else "year"
    staff_dir = out_dir / "staff"
    n = 0
    for rec in staff.itertuples(index=False):
        pid, year = str(rec.pitcher_anon_id), int(getattr(rec, season_col))
        try:
            export_card(build_card(pid, year, tables), staff_dir, tokens)
            n += 1
        except KeyError:
            continue
    (out_dir / "staff_export.txt").write_text(
        f"Fichas de staff escritas: {n}. Sin lista de ids en CSV.\n", encoding="utf-8",
    )
    return manifest


def prepare_page(reports: Path | None = None) -> dict:
    """Estado de la página. Nunca levanta: la UI muestra el mensaje."""
    try:
        tables = load_tables(reports)
        keys = deck_example_keys(tables)
    except (FileNotFoundError, ValueError, KeyError) as exc:
        return {"ok": False, "message": f"No se puede armar la ficha. {exc}"}
    options = [f"{pid} · {year}" for pid, year, _ in keys]
    season = tables["pitcher_season"].sort_values(["year", "pitcher_anon_id"], ascending=[False, True])
    seen = set(options)
    for rec in season.itertuples(index=False):
        label = f"{rec.pitcher_anon_id} · {int(rec.year)}"
        if label not in seen:
            options.append(label)
            seen.add(label)
    return {"ok": True, "tables": tables, "options": options, "message": ""}


def main() -> None:
    out = config.REPORTS_DIR / "cards"
    manifest = batch_export(out)
    print(manifest.to_string(index=False))
    missing = out / "staff_missing.txt"
    print(missing.read_text(encoding="utf-8") if missing.exists() else (out / "staff_export.txt").read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
