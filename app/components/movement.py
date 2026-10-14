"""Centroids of pitch shapes at sea level and at Harp Helú, from published aggregates only."""
from __future__ import annotations

import pandas as pd

SIGMA_IN = 1.8  # schematic contour width; the published tables have no within-shape spread


def shape_points(shapes: pd.DataFrame, deltas: pd.DataFrame, air: str) -> pd.DataFrame:
    """One row per shape: ``hb`` / ``ivb`` in the requested air and the Stuff+ scored there.

    ``air`` is ``sea`` or ``cdmx``. CDMX movement is the sea-level centroid plus the
    within-pitcher deltas from ``delta_by_shape`` (IVB and arm-side HB, inches).
    """
    if air not in ("sea", "cdmx"):
        raise ValueError("air must be 'sea' or 'cdmx'")
    cols = ["shape", "delta_ivb_in", "delta_hb_arm_in", "stuff_sea_level", "stuff_harp_helu"]
    merged = shapes.merge(deltas[cols], on="shape", how="inner")
    out = pd.DataFrame({
        "shape": merged["shape"],
        "n": merged["n"],
        "hb": merged["hb_sl"] + (merged["delta_hb_arm_in"] if air == "cdmx" else 0.0),
        "ivb": merged["ivb_sl"] + (merged["delta_ivb_in"] if air == "cdmx" else 0.0),
        "stuff": merged["stuff_harp_helu"] if air == "cdmx" else merged["stuff_sea_level"],
    })
    return out.dropna(subset=["stuff", "hb", "ivb"]).reset_index(drop=True)


def extremes(frame: pd.DataFrame) -> tuple[str, str]:
    """Shape with the highest Stuff+ and the shape with the lowest, in this air."""
    return str(frame.loc[frame["stuff"].idxmax(), "shape"]), str(frame.loc[frame["stuff"].idxmin(), "shape"])
