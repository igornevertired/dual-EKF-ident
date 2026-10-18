"""
Автопилот номинальной траектории (порты VHHOLD.m, HEADINGHOLD.m, AUTOPILOT.m)
и подмешивание программы идентификационного манёвра.

На интервале манёвра рулём канал руля высоты автопилота отключён — он не гасит
вход; на интервале манёвра РУД (или фиксации РУД) отключён автомат тяги.
Сами программы манёвров описаны в ``maneuvers.py``.
"""

from __future__ import annotations

import numpy as np

from .maneuvers import Maneuver

UMAX = np.array([0.85, 30.0, 25.0, 25.0])  # [δT, δв (°), δн (°), δэ (°)]
UMIN = np.array([0.1, -25.0, -25.0, -25.0])


def vh_hold(x, dx, htr, vtr, tettr):
    """Удержание высоты и скорости: приращения РУД и руля высоты."""
    V = np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2)
    DV = np.sqrt(dx[0] ** 2 + dx[1] ** 2 + dx[2] ** 2)
    H = x[10]
    Wz = x[5]
    TET = x[8]

    DdeltaT = 0.145670 * (vtr - V) - 0.307940 * DV + 0.006174 * (htr - H)
    DdeltaV = (
        1.339591 * Wz * 57.3
        - 1.332765 * (tettr - TET) * 57.3
        - 0.127573 * (htr - H)
        - 0.148772 * (vtr - V)
    )
    return DdeltaT, DdeltaV


def heading_hold(x, time):
    """Удержание курса: приращения руля направления и элеронов."""
    Wx, Wy = x[3], x[4]
    GAM, PSI = x[6], x[7]

    PSITR = PSI
    if 100.0 < time < 300:
        PSITR = 45.0 * Wy / 180.0 - 45.0 * Wy / 180.0 * (time - 100.0) / 300.0
    elif 400.0 <= time < 550:
        PSITR = 45.0 * Wy / 180.0 * (time - 400.0) / 300.0
    elif 700 <= time < 900:
        PSITR = 45.0 * Wy / 180.0 + 45.0 * Wy / 180.0 * (time - 700.0) / 300.0

    dn = -1.5 * (-4.501701) * Wx + (-0.295147) * GAM
    de = -1.5 * (2.706971) * Wy + (-0.124876) * (PSI - PSITR)
    return dn, de


def autopilot(x, dx, time, u0, htr, vtr, tettr, maneuver: Maneuver | None = None):
    """
    Управление u = [δT, δв, δн, δэ] = балансировка u0 + автопилот (+ программа манёвра).

    На интервале манёвра рулём: δв = u0[1] + программа (канал δв автопилота отключён).
    На интервале манёвра РУД / фиксации РУД: δT = u0[0] + программа (автомат тяги отключён).
    """
    DdeltaT, DdeltaV = vh_hold(x, dx, htr, vtr, tettr)
    DdeltaN, DdeltaE = heading_hold(x, time)

    U = np.asarray(u0, dtype=float).copy() + np.array(
        [DdeltaT, DdeltaV, DdeltaN, DdeltaE], dtype=float
    )

    if maneuver is not None:
        if maneuver.elevator_active(time):
            U[1] = float(u0[1]) + maneuver.elevator_deg(time)
        dthr = maneuver.throttle_offset(time)
        if dthr is not None:
            U[0] = float(u0[0]) + dthr

    return np.clip(U, UMIN, UMAX)
