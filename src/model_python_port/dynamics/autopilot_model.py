"""
Автопилот номинальной траектории (порты VHHOLD.m, HEADINGHOLD.m, AUTOPILOT.m).

Опционально: программа манёвра руля высоты для идентификации (ОФК-2).
На интервале манёвра канал δV автопилота замораживается — не гасит вход.
"""

from __future__ import annotations

import numpy as np

UMAX = np.array([0.85, 30.0, 25.0, 25.0])
UMIN = np.array([0.1, -25.0, -25.0, -25.0])


def vh_hold(x, dx, htr, vtr, tettr):
    """Удержание высоты и скорости."""
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
    """Удержание курса."""
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


def elevator_doublet_deg(
    time: float,
    *,
    t0: float = 10.0,
    pulse: float = 2.5,
    amp_deg: float = 5.0,
) -> float:
    """Doublet руля высоты, градусы: +amp / −amp."""
    t = float(time)
    if t0 <= t < t0 + pulse:
        return float(amp_deg)
    if t0 + pulse <= t < t0 + 2.0 * pulse:
        return float(-amp_deg)
    return 0.0


def elevator_3211_deg(
    time: float,
    *,
    t0: float = 15.0,
    unit: float = 1.0,
    amp_deg: float = 3.0,
) -> float:
    """Вход 3-2-1-1 по рулю высоты, градусы."""
    t = float(time) - float(t0)
    if t < 0.0:
        return 0.0
    edges = [0.0, 3 * unit, 5 * unit, 6 * unit, 7 * unit]
    signs = [+1.0, -1.0, +1.0, -1.0]
    for k in range(4):
        if edges[k] <= t < edges[k + 1]:
            return float(signs[k] * amp_deg)
    return 0.0


def elevator_maneuver_active(time: float, kind: str | None) -> bool:
    """True на интервале, где программа δV ненулевая (или только что была)."""
    if not kind:
        return False
    if kind == "doublet":
        return abs(elevator_doublet_deg(time)) > 0.0
    if kind == "3211":
        return abs(elevator_3211_deg(time)) > 0.0
    return False


def elevator_program_deg(
    time: float,
    kind: str | None,
    *,
    doublet_amp_deg: float = 5.0,
) -> float:
    if kind == "doublet":
        return elevator_doublet_deg(time, amp_deg=float(doublet_amp_deg))
    if kind == "3211":
        return elevator_3211_deg(time)
    return 0.0


def autopilot(
    x,
    dx,
    time,
    u0,
    htr,
    vtr,
    tettr,
    *,
    elevator_maneuver: str | None = None,
    elevator_doublet_amp_deg: float = 5.0,
):
    """
    Управление u = [δT, δV, δN, δE].

    ``elevator_maneuver``: None | \"doublet\" | \"3211\".
    На активном интервале манёвра:
      — канал δV автопилота (тангаж/высота) отключён;
      — δV = u0[1] + программа (градусы).
    Тяга и боковой канал работают как обычно.
    """
    DdeltaT, DdeltaV = vh_hold(x, dx, htr, vtr, tettr)
    DdeltaN, DdeltaE = heading_hold(x, time)

    U = np.asarray(u0, dtype=float).copy() + np.array(
        [DdeltaT, DdeltaV, DdeltaN, DdeltaE], dtype=float
    )

    if elevator_maneuver_active(time, elevator_maneuver):
        # не гасим вход: только trim + программа
        U[1] = float(u0[1]) + elevator_program_deg(
            time,
            elevator_maneuver,
            doublet_amp_deg=float(elevator_doublet_amp_deg),
        )

    return np.clip(U, UMIN, UMAX)
