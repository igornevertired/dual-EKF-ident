"""
Теоретические L*, M*, X* для ОФК-2 (продольная модель, 5 ДУ).

Линеаризация FX1 в точке балансировки::

    α̇ = Lα·δα + Lq·q + Lδe·δδe + Lv·δV + Lθ·δθ
    q̇ = Mα·δα + Mq·q + Mδe·δδe + Mv·δV + Mθ·δθ
    V̇ = Xα·δα + Xq·q + Xδe·δδe + Xv·δV + Xθ·δθ
    θ̇ = q
    ḣ = V sin(θ−α)
"""

from __future__ import annotations

import numpy as np

from ..dynamics.fx1 import fx1 as fx1_func

PARAM_NAMES = (
    "Lα",
    "Lq",
    "Lδe",
    "Lv",
    "Lθ",
    "Mα",
    "Mq",
    "Mδe",
    "Mv",
    "Mθ",
    "Xα",
    "Xq",
    "Xδe",
    "Xv",
    "Xθ",
)
# Слабонаблюдаемые Lθ, Mθ, Xθ в модели остаются, на отчётных графиках не жмут
REPORT_PARAM_NAMES = (
    "Lα",
    "Lq",
    "Lδe",
    "Lv",
    "Mα",
    "Mq",
    "Mδe",
    "Mv",
    "Xα",
    "Xq",
    "Xδe",
    "Xv",
)
REPORT_PARAM_INDICES = tuple(PARAM_NAMES.index(n) for n in REPORT_PARAM_NAMES)
N_REG = 5


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


def _set_speed(x: np.ndarray, v_new: float) -> None:
    v_old = float(np.linalg.norm(x[0:3]))
    v_old = max(v_old, 1e-9)
    x[0:3] *= float(v_new) / v_old


def _long_rates(x: np.ndarray, u: np.ndarray, la: dict, t: float = 0.0) -> tuple[float, float, float]:
    dx, _af, _w = fx1_func(x, u, t, la)
    vx, vy, vz = float(x[0]), float(x[1]), float(x[2])
    dvx, dvy, dvz = float(dx[0]), float(dx[1]), float(dx[2])
    den = max(vx * vx + vy * vy, 1e-12)
    alpha_dot = -(vx * dvy - vy * dvx) / den
    q_dot = float(dx[5])
    v = max(float(np.sqrt(vx * vx + vy * vy + vz * vz)), 1e-9)
    v_dot = (vx * dvx + vy * dvy + vz * dvz) / v
    return alpha_dot, q_dot, v_dot


def ofk2_jacobian_at_trim(
    x0: np.ndarray,
    u0: np.ndarray,
    la: dict,
    *,
    thetatr: float = 0.0,
    d_alpha: float = 1.0e-4,
    d_q: float = 1.0e-4,
    d_de_rad: float = 1.0e-4,
    d_v: float = 0.05,
    d_theta: float = 1.0e-4,
) -> dict[str, float]:
    x_base = np.asarray(x0, dtype=float).copy()
    u_base = np.asarray(u0, dtype=float).copy()

    a0 = _alpha_from_x(x_base)
    q0 = float(x_base[5])
    de0_rad = float(x_base[16]) * np.pi / 180.0
    v0 = float(np.linalg.norm(x_base[0:3]))
    v0 = max(v0, 1.0)
    theta0 = float(x_base[8])

    def eval_at(
        alpha: float,
        q: float,
        de_rad: float,
        v_mag: float,
        theta: float,
    ) -> tuple[float, float, float]:
        x = x_base.copy()
        u = u_base.copy()
        _set_alpha(x, alpha, thetatr)
        _set_speed(x, v_mag)
        x[8] = theta
        x[5] = q
        de_deg = de_rad * 180.0 / np.pi
        x[16] = de_deg
        u[1] = de_deg
        return _long_rates(x, u, la)

    def deriv_wrt(
        arg: str,
        da_: float,
        dq_: float,
        dde_: float,
        dv_: float,
        dth_: float,
    ) -> tuple[float, float, float]:
        if arg == "alpha":
            hi = (a0 + da_, q0, de0_rad, v0, theta0)
            lo = (a0 - da_, q0, de0_rad, v0, theta0)
            step = d_alpha
        elif arg == "q":
            hi = (a0, q0 + dq_, de0_rad, v0, theta0)
            lo = (a0, q0 - dq_, de0_rad, v0, theta0)
            step = d_q
        elif arg == "de":
            hi = (a0, q0, de0_rad + dde_, v0, theta0)
            lo = (a0, q0, de0_rad - dde_, v0, theta0)
            step = d_de_rad
        elif arg == "v":
            hi = (a0, q0, de0_rad, v0 + dv_, theta0)
            lo = (a0, q0, de0_rad, v0 - dv_, theta0)
            step = d_v
        elif arg == "theta":
            hi = (a0, q0, de0_rad, v0, theta0 + dth_)
            lo = (a0, q0, de0_rad, v0, theta0 - dth_)
            step = d_theta
        else:
            raise ValueError(arg)
        adot_p, qdot_p, vdot_p = eval_at(*hi)
        adot_m, qdot_m, vdot_m = eval_at(*lo)
        den = 2.0 * step
        return (
            (adot_p - adot_m) / den,
            (qdot_p - qdot_m) / den,
            (vdot_p - vdot_m) / den,
        )

    la_, ma_, xa_ = deriv_wrt("alpha", d_alpha, d_q, d_de_rad, d_v, d_theta)
    lq_, mq_, xq_ = deriv_wrt("q", d_alpha, d_q, d_de_rad, d_v, d_theta)
    lde_, mde_, xde_ = deriv_wrt("de", d_alpha, d_q, d_de_rad, d_v, d_theta)
    lv_, mv_, xv_ = deriv_wrt("v", d_alpha, d_q, d_de_rad, d_v, d_theta)
    lth_, mth_, xth_ = deriv_wrt("theta", d_alpha, d_q, d_de_rad, d_v, d_theta)

    adot0, qdot0, vdot0 = eval_at(a0, q0, de0_rad, v0, theta0)
    gamma0 = theta0 - a0

    return {
        "alpha0": a0,
        "q0": q0,
        "delta_e0": de0_rad,
        "v0": v0,
        "theta0": theta0,
        "h0": float(x_base[10]),
        "alpha_dot0": adot0,
        "q_dot0": qdot0,
        "v_dot0": vdot0,
        "L_alpha": float(la_),
        "L_q": float(lq_),
        "L_de": float(lde_),
        "L_v": float(lv_),
        "L_theta": float(lth_),
        "M_alpha": float(ma_),
        "M_q": float(mq_),
        "M_de": float(mde_),
        "M_v": float(mv_),
        "M_theta": float(mth_),
        "X_alpha": float(xa_),
        "X_q": float(xq_),
        "X_de": float(xde_),
        "X_v": float(xv_),
        "X_theta": float(xth_),
        "Theta_q": 1.0,
        "H_alpha": float(-v0 * np.cos(gamma0)),
        "H_theta": float(v0 * np.cos(gamma0)),
        "H_v": float(np.sin(gamma0)),
    }


def theory_vector(th: dict[str, float]) -> np.ndarray:
    return np.array(
        [
            th["L_alpha"],
            th["L_q"],
            th["L_de"],
            th["L_v"],
            th["L_theta"],
            th["M_alpha"],
            th["M_q"],
            th["M_de"],
            th["M_v"],
            th["M_theta"],
            th["X_alpha"],
            th["X_q"],
            th["X_de"],
            th["X_v"],
            th["X_theta"],
        ],
        dtype=float,
    )


def coeff_delta_ekf_minus_theory(x_sp: np.ndarray, th_vec: np.ndarray) -> np.ndarray:
    n = len(PARAM_NAMES)
    return np.asarray(x_sp[:n], dtype=float) - np.asarray(th_vec[:n], dtype=float)
