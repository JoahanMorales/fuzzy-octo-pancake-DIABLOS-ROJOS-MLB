"""RK4 pitch flight: the same release thrown in any air (HACK-041; ported to TypeScript in HACK-042).

Coordinates (Trackman, feet): x toward the catcher's right, y from home plate toward the mound, z up. Forces:
gravity; drag −½ρA·C_D·|v|v/m; Magnus as an acceleration perpendicular to v whose direction and sea-level size
are calibrated so that the pitch shows the requested induced vertical break (IVB) and arm-side break (HB) at
sea level. In air of relative density ρ, drag scales with ρ and Magnus with ρ**elasticity (1 = textbook physics;
``coefficients.magnus_elasticity`` measures it). Breaks are measured as Trackman does: displacement at the front of
the plate against the same pitch thrown with no spin.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .constants import BALL_AREA_M2, BALL_MASS_KG, FT_TO_M, G_FT_S2, MPH_TO_FPS, RHO_SI_SEA_LEVEL

PLATE_FRONT_FT = 17.0 / 12.0
MOUND_FT = 60.5
DT = 1.0 / 240.0
K_SEA = 0.5 * RHO_SI_SEA_LEVEL * BALL_AREA_M2 / BALL_MASS_KG * FT_TO_M  # a[ft/s²] = K·C·v²[ft/s] at ρ = 1


@dataclass
class Release:
    velo_mph: float = 94.0
    ivb_in: float = 17.0          # at sea level (ρ = 1)
    hb_in: float = 8.0            # arm side, at sea level
    rel_height_ft: float = 6.0
    rel_side_ft: float = 1.8      # arm side
    extension_ft: float = 6.3
    target_z_ft: float = 2.6      # where the sea-level pitch crosses the plate
    target_x_ft: float = 0.0      # arm side
    cd: float = 0.29


@dataclass
class Flight:
    t: np.ndarray
    pos: np.ndarray               # (n, 3) x arm side, y, z
    plate_x: float
    plate_z: float
    ivb_in: float
    hb_in: float
    flight_time: float
    plate_mph: float


def _integrate(v0, r0, mag_acc, rho, cd, spin=True):
    """RK4 until the ball reaches the front of the plate. ``mag_acc``: (x, z) Magnus acceleration at ρ=1 (ft/s²)."""
    k = K_SEA * rho * cd
    mx, mz = (mag_acc if spin else (0.0, 0.0))

    def acc(v):
        s = np.linalg.norm(v)
        a = -k * s * v
        a[2] -= G_FT_S2
        if spin:  # keep the Magnus vector perpendicular to the velocity
            m = np.array([mx, 0.0, mz])
            vh = v / s
            m = m - np.dot(m, vh) * vh
            a = a + m
        return a

    r, v = np.array(r0, float), np.array(v0, float)
    ts, ps, t = [0.0], [r.copy()], 0.0
    for _ in range(2000):
        k1v, k1r = acc(v), v
        k2v, k2r = acc(v + 0.5 * DT * k1v), v + 0.5 * DT * k1v
        k3v, k3r = acc(v + 0.5 * DT * k2v), v + 0.5 * DT * k2v
        k4v, k4r = acc(v + DT * k3v), v + DT * k3v
        r_new = r + DT / 6 * (k1r + 2 * k2r + 2 * k3r + k4r)
        v_new = v + DT / 6 * (k1v + 2 * k2v + 2 * k3v + k4v)
        if r_new[1] <= PLATE_FRONT_FT:  # interpolate the crossing
            f = (r[1] - PLATE_FRONT_FT) / (r[1] - r_new[1])
            r_end, v_end = r + f * (r_new - r), v + f * (v_new - v)
            t += f * DT
            ts.append(t); ps.append(r_end)
            return np.array(ts), np.array(ps), v_end
        r, v, t = r_new, v_new, t + DT
        ts.append(t); ps.append(r.copy())
    raise RuntimeError("the pitch never reached the plate")


def _launch(rel: Release, angles):
    speed = rel.velo_mph * MPH_TO_FPS
    yaw, pitch = angles
    v0 = speed * np.array([np.sin(yaw) * np.cos(pitch), -np.cos(yaw) * np.cos(pitch), np.sin(pitch)])
    r0 = (rel.rel_side_ft, MOUND_FT - rel.extension_ft, rel.rel_height_ft)
    return v0, r0


def fly(rel: Release, rho: float = 1.0, elasticity: float = 1.0) -> Flight:
    """Calibrate Magnus and the launch angles at sea level, then throw the same release in air ``rho``."""
    angles, mag = np.array([0.0, -0.03]), np.zeros(2)
    for _ in range(6):  # alternate: Magnus size from the requested breaks, launch angles from the target
        v0, r0 = _launch(rel, angles)
        t_, p_spin, _ = _integrate(v0, r0, tuple(mag), 1.0, rel.cd)
        _, p_nos, _ = _integrate(v0, r0, (0, 0), 1.0, rel.cd, spin=False)
        T = t_[-1]
        mag = mag + 2 * (np.array([rel.hb_in, rel.ivb_in]) / 12 - (p_spin[-1][[0, 2]] - p_nos[-1][[0, 2]])) / T**2
        err = np.array([rel.target_x_ft, rel.target_z_ft]) - p_spin[-1][[0, 2]]
        dist = r0[1] - PLATE_FRONT_FT
        angles = angles + np.array([err[0] / dist, err[1] / dist])
    v0, r0 = _launch(rel, angles)
    scale = rho ** elasticity
    t, pos, v_end = _integrate(v0, r0, tuple(mag * scale), rho, rel.cd)
    _, nos, _ = _integrate(v0, r0, (0, 0), rho, rel.cd, spin=False)
    brk = (pos[-1] - nos[-1]) * 12
    return Flight(t=t, pos=pos, plate_x=float(pos[-1][0]), plate_z=float(pos[-1][2]), ivb_in=float(brk[2]),
                  hb_in=float(brk[0]), flight_time=float(t[-1]), plate_mph=float(np.linalg.norm(v_end) / MPH_TO_FPS))
