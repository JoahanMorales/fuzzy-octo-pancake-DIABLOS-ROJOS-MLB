"""Constantes físicas. Único lugar donde vive la densidad de Harp Helú (nunca hardcodear 2240)."""
from __future__ import annotations

import math

G_FT_S2 = 32.174  # gravedad, ft/s^2
FT_TO_M = 0.3048
MPH_TO_FPS = 5280.0 / 3600.0
RPM_TO_RADS = 2.0 * math.pi / 60.0

# Pelota MLB/LMB
BALL_MASS_KG = 0.145
BALL_RADIUS_M = 9.125 * 0.0254 / (2.0 * math.pi)  # circunferencia 9.125 in
BALL_AREA_M2 = math.pi * BALL_RADIUS_M**2

# Atmósfera
RHO_SI_SEA_LEVEL = 1.225  # kg/m^3 (ISA, 15 °C)
RHO_SEA_LEVEL = 1.0  # unidad relativa: 100 = park-neutral

HARP_HELU_ALTITUDE_M = 2240.0
PUEBLA_ALTITUDE_M = 2135.0
COORS_ALTITUDE_M = 1580.0
_TEMP_LAPSE_K_M = 0.0065
_BAROMETRIC_EXP = 5.2559  # g*M/(R*L)


def barometric_density_ratio(altitude_m: float, temp_c: float = 15.0) -> float:
    """ρ(altitud)/ρ(nivel del mar ISA) con barómetro ISA y temperatura de superficie `temp_c`.

    Presión por atmósfera estándar; densidad = p/(R T) con T la temperatura dada
    a esa altitud (temp_c es la temperatura típica *en el parque*).
    """
    p_ratio = (1.0 - _TEMP_LAPSE_K_M * altitude_m / 288.15) ** _BAROMETRIC_EXP
    return p_ratio * 288.15 / (temp_c + 273.15)


# Barométrico: CDMX 2,240 m con ~20 °C típicos de tarde/noche de partido (documentado, a sustituir
# por el empírico de HACK-003 cuando exista).
RHO_HARP_HELU_BAROMETRIC = barometric_density_ratio(HARP_HELU_ALTITUDE_M, temp_c=20.0)
# Empírico (HACK-003, ρ̂ de Cd-proxy relativo a nivel del mar). None hasta que HACK-003 integre.
RHO_HARP_HELU_EMPIRICAL: float | None = None
RHO_HARP_HELU = RHO_HARP_HELU_EMPIRICAL if RHO_HARP_HELU_EMPIRICAL is not None else RHO_HARP_HELU_BAROMETRIC
RHO_COORS = barometric_density_ratio(COORS_ALTITUDE_M, temp_c=20.0)
