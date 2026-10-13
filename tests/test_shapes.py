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


def test_shape_rules_and_single_pitch():
    import numpy as np
    from stuffplus.features.shapes import ShapeModel, assign_shape, shape_rule

    out = shape_rule(["Four-Seam", "Four-Seam", "Slider", "Slider", "Curveball", "Changeup", "Sinker"],
                     [19, 14, 2, 3, -10, 6, 8], [8, 8, -11, -2, 1, 12, 15], [95, 92, 84, 85, 78, 88, 93])
    assert list(out) == ["riding 4S", "4S", "sweeper", "gyro slider", "12-6 CB", "power CH", "sinking 2S"]
    cen = pd.DataFrame({"RelSpeed": [92.0, 84.0], "ivb": [16.0, 3.0], "hb": [9.0, -4.0]}, index=["Four-Seam", "Slider"])
    m = ShapeModel(rho_effect={"Four-Seam": {"ivb": 22.0, "hb": 8.0}, "Slider": {"ivb": 5.0, "hb": 4.0}},
                   centroids=cen, scale=pd.Series({"RelSpeed": 5.0, "ivb": 6.0, "hb": 8.0}))
    # misma recta: en CDMX (ρ=0.84) mide 12.5" de IVB; a nivel del mar son 16" → "4S", no "riding"
    assert assign_shape(m, 93, 12.5, 9.0, "Right", rho=0.84) == "4S"
    assert assign_shape(m, 96, 18.5, 9.0, "Right", rho=1.0) == "riding 4S"
    assert assign_shape(m, 84, 3.0, 4.0, "Left", rho=1.0) in {"slider", "gyro slider", "sweeper"}
