"""
Теоретические L*, M* для ОФК-2 (короткопериодическое движение).

Численный якобиан FX1 в точке балансировки::

    [ α̇ ]   [ L_α   L_q   L_δe ] [ δα  ]
    [ q̇ ] = [ M_α   M_q   M_δe ] [  q  ]
                                 [ δδe ]
"""

from __future__ import annotations

import numpy as np

from ..dynamics.fx1 import fx1 as fx1_func

PARAM_NAMES = ("Lα", "Lq", "Lδe", "Mα", "Mq", "Mδe")


def _alpha_from_x(x: np.ndarray) -> float:
    vx, vy = float(x[0]), float(x[1])
    return float(-np.arctan2(vy, vx if abs(vx) > 1e-12 else 1e-12))


def _set_alpha(x: np.ndarray, alpha: float, thetatr: float = 0.0) -> None:
    v = float(np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2))
    v = max(v, 1e-9)
    beta = float(np.arcsin(np.clip(x[2] / v, -1.0, 1.0)))
    x[0] = v * np.cos(beta) * np.cos(alpha)
    x[1] = -v * np.cos(beta) * np.sin(alpha)
    x[2] = v * np.sin(beta)
    x[8] = alpha + thetatr


def _alpha_q_dot(x: np.ndarray, u: np.ndarray, la: dict, t: float = 0.0) -> tuple[float, float]:
    dx, _af, _w = fx1_func(x, u, t, la)
    vx, vy = float(x[0]), float(x[1])
    dvx, dvy = float(dx[0]), float(dx[1])
    den = max(vx * vx + vy * vy, 1e-12)
    alpha_dot = -(vx * dvy - vy * dvx) / den
    q_dot = float(dx[5])
    return alpha_dot, q_dot


def ofk2_jacobian_at_trim(
    x0: np.ndarray,
    u0: np.ndarray,
    la: dict,
    *,
    thetatr: float = 0.0,
    d_alpha: float = 1.0e-4,
    d_q: float = 1.0e-4,
    d_de_rad: float = 1.0e-4,
) -> dict[str, float]:
    x_base = np.asarray(x0, dtype=float).copy()
    u_base = np.asarray(u0, dtype=float).copy()

    a0 = _alpha_from_x(x_base)
    q0 = float(x_base[5])
    de0_rad = float(x_base[16]) * np.pi / 180.0

    def eval_at(alpha: float, q: float, de_rad: float) -> tuple[float, float]:
        x = x_base.copy()
        u = u_base.copy()
        _set_alpha(x, alpha, thetatr)
        x[5] = q
        de_deg = de_rad * 180.0 / np.pi
        x[16] = de_deg
        u[1] = de_deg
        return _alpha_q_dot(x, u, la)

    adot_p, qdot_p = eval_at(a0 + d_alpha, q0, de0_rad)
    adot_m, qdot_m = eval_at(a0 - d_alpha, q0, de0_rad)
    la_ = (adot_p - adot_m) / (2.0 * d_alpha)
    ma_ = (qdot_p - qdot_m) / (2.0 * d_alpha)

    adot_p, qdot_p = eval_at(a0, q0 + d_q, de0_rad)
    adot_m, qdot_m = eval_at(a0, q0 - d_q, de0_rad)
    lq_ = (adot_p - adot_m) / (2.0 * d_q)
    mq_ = (qdot_p - qdot_m) / (2.0 * d_q)

    adot_p, qdot_p = eval_at(a0, q0, de0_rad + d_de_rad)
    adot_m, qdot_m = eval_at(a0, q0, de0_rad - d_de_rad)
    lde_ = (adot_p - adot_m) / (2.0 * d_de_rad)
    mde_ = (qdot_p - qdot_m) / (2.0 * d_de_rad)

    adot0, qdot0 = eval_at(a0, q0, de0_rad)

    return {
        "alpha0": a0,
        "q0": q0,
        "delta_e0": de0_rad,
        "alpha_dot0": adot0,
        "q_dot0": qdot0,
        "L_alpha": float(la_),
        "L_q": float(lq_),
        "L_de": float(lde_),
        "M_alpha": float(ma_),
        "M_q": float(mq_),
        "M_de": float(mde_),
    }


def theory_vector(th: dict[str, float]) -> np.ndarray:
    return np.array(
        [
            th["L_alpha"],
            th["L_q"],
            th["L_de"],
            th["M_alpha"],
            th["M_q"],
            th["M_de"],
        ],
        dtype=float,
    )


def coeff_delta_ekf_minus_theory(x_sp: np.ndarray, th_vec: np.ndarray) -> np.ndarray:
    return np.asarray(x_sp[:6], dtype=float) - np.asarray(th_vec, dtype=float)
