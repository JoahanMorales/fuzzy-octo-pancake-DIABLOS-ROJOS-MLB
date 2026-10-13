import numpy as np
import pandas as pd

from stuffplus.features.identity import assign_pitch_id, usage_shift


def _two_pitch_pitcher(rng, n=400):
    """Un pitcher con recta (95 mph, 2300 rpm) y slider (86 mph, 2600 rpm) en dos ambientes.

    En altitud Trackman etiqueta como Slider parte de los Cutter/rectas lentas (etiqueta inestable).
    """
    rows = []
    for alt in ("No Altitude", "Extreme Altitude"):
        for _ in range(n):
            fb = rng.random() < 0.6
            rows.append(dict(
                pitcher_anon_id=1, year=2023, altitude_category=alt,
                RelSpeed=rng.normal(95 if fb else 86, 1.0), SpinRate=rng.normal(2300 if fb else 2600, 60),
                RelHeight=rng.normal(5.8, 0.05), RelSide=rng.normal(-1.5, 0.05), Extension=rng.normal(6.2, 0.05),
                AutoPitchType="Four-Seam" if fb else ("Slider" if alt == "No Altitude" or rng.random() < 0.7 else "Changeup"),
            ))
    return pd.DataFrame(rows)


def test_pitch_id_finds_two_pitches_and_is_altitude_stable():
    df = _two_pitch_pitcher(np.random.default_rng(0))
    out = assign_pitch_id(df)
    assert out["pitch_id"].nunique() == 2 and (out["pitch_id"] >= 0).all()
    assert set(out["pitch_family"]) == {"Four-Seam", "Slider"}
    # id 0 = más rápido; uso por pitch_id igual en ambos ambientes
    assert abs(usage_shift(out, "pitch_id").abs().max()) < 3.0
    assert usage_shift(out, "AutoPitchType").abs().max() > 5.0  # la etiqueta sí se mueve


def test_synthetic_fixture_runs(synthetic_pitches):
    out = assign_pitch_id(synthetic_pitches)
    assert {"pitch_id", "pitch_family", "pitch_key"} <= set(out.columns)
    assert len(out) == len(synthetic_pitches)
    assert (out["pitch_id"] >= 0).mean() > 0.5
