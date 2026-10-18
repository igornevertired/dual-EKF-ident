"""
ОФК-2 — в точности система (15).

    ΔV̇  = −a11 ΔV − a12 Δα − a13 Δθ − b11 δB
    Δα̇  = −a21 ΔV − a22 Δα − a23 Δθ + Δωz + b21 δB
    Δθ̇  =  a31 ΔV + a32 Δα + a33 Δθ + b31 δB
    Δω̇z = −(a41−a′42 a31) ΔV − (a42−a′42 a32) Δα
          + a′42 a33 Δθ − (a44+a′42) Δωz
          + (b41−a′42 b31) δB + b′41 δ̇B

Дополнительно в 1-й строке — известный вход тяги: + Xδt ΔδT.
Автомат тяги во время дублета сдвигает РУД на ~0.3, без этого
члена уравнение ΔV̇ не сходится с FX1 и портит все X* (а через связи — и L*, M*).
Lδt ≈ −0,0054, Θδt = −Lδt, Mδt ≈ 0,001 (основной режим) в модель не входят: по протоколу
РУД на время манёвра фиксируется (Maneuver.hold_throttle), и ΔδT = 0. Если автомат тяги
работает, вклад Lδt·ΔδT в Δα̇ сравним с вкладом руля и смещает оценку Lδe.

Переобозначения (то, что оценивает EKF)::

    Xv=−a11, Xα=−a12, Xθ=−a13, Xδe=−b11
    Lv=−a21, Lα=−a22, Lθ=−a23, Lq=+1, Lδe=b21
    Θv=a31, Θα=a32, Θθ=a33, Θδe=b31
    Mv=−(a41−a′42 a31), Mα=−(a42−a′42 a32),
    Mθ=a′42 a33, Mq=−(a44+a′42),
    Mδe=(b41−a′42 b31), Mδė=b′41, Xδt — тяга

θ — угол наклона траектории, tgθ = Vy/√(Vx²+Vz²) из ОФК-1.
Xq в (15) нет. p в 3-й строке поглощён в b31.
"""

from __future__ import annotations

import numpy as np

from ..dynamics.fx1 import c_gb
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
    "Mδė",
    "Xα",
    "Xδe",
    "Xv",
    "Xθ",
    "Θα",
    "Θδe",
    "Θv",
    "Θθ",
    "Xδt",
)
# Научрук: мелкие игнорировать; Xα — с хорошей точностью.
# Lq ≡ 1 (член +Δωz). Xθ ≈ −g — известная тяжесть, иначе путается с Xα.
# Lv, Lθ, Mv, Mθ, Mδė, Xv, Θδe, Θv, Θθ — малы в trim, константы.
FROZEN_PARAM_INDICES = (1, 3, 4, 8, 9, 10, 13, 14, 16, 17, 18)
ESTIMATED_PARAM_INDICES = tuple(
    i for i in range(len(PARAM_NAMES)) if i not in FROZEN_PARAM_INDICES
)
REPORT_PARAM_INDICES = ESTIMATED_PARAM_INDICES
REPORT_PARAM_NAMES = tuple(PARAM_NAMES[i] for i in REPORT_PARAM_INDICES)

N_L = 5
N_M = 6
N_X = 4
N_TH = 4


def path_angle_from_nav(vn: float, vh: float, ve: float) -> float:
    """Угол наклона траектории: tgθ = Vy / √(Vx²+Vz²) (≡ sinθ = Vy/|V|). NP: Vx=Vn, Vy=Vh, Vz=Ve.

    В письме — sinθ = Vy/√(Vx²+Vz²): для малых θ то же самое, но при наборе
    аргумент arcsin может выйти за 1, поэтому берём точную формулу.
    """
    horiz = float(np.sqrt(vn * vn + ve * ve))
    return float(np.arctan2(vh, horiz))


def path_angle_from_x(x: np.ndarray) -> float:
    cgb = c_gb(float(x[8]), float(x[6]), float(x[7]))
    vg = cgb.T @ np.array([x[0], x[1], x[2]], dtype=float)
    return path_angle_from_nav(float(vg[0]), float(vg[1]), float(vg[2]))


def _alpha_from_x(x: np.ndarray) -> float:
    vx, vy = float(x[0]), float(x[1])
    return float(-np.arctan2(vy, vx if abs(vx) > 1e-12 else 1e-12))


def _set_alpha(x: np.ndarray, alpha: float) -> None:
    v = float(np.sqrt(x[0] ** 2 + x[1] ** 2 + x[2] ** 2))
    v = max(v, 1e-9)
    beta = float(np.arcsin(np.clip(x[2] / v, -1.0, 1.0)))
    x[0] = v * np.cos(beta) * np.cos(alpha)
    x[1] = -v * np.cos(beta) * np.sin(alpha)
    x[2] = v * np.sin(beta)


def _set_speed(x: np.ndarray, v_new: float) -> None:
    v_old = float(np.linalg.norm(x[0:3]))
    v_old = max(v_old, 1e-9)
    x[0:3] *= float(v_new) / v_old


def _long_rates(
    x: np.ndarray, u: np.ndarray, la: dict, t: float = 0.0
) -> tuple[float, float, float, float]:
    dx, _af, _w = fx1_func(x, u, t, la)
    vx, vy, vz = float(x[0]), float(x[1]), float(x[2])
    dvx, dvy, dvz = float(dx[0]), float(dx[1]), float(dx[2])
    den = max(vx * vx + vy * vy, 1e-12)
    alpha_dot = -(vx * dvy - vy * dvx) / den
    q_dot = float(dx[5])
    v = max(float(np.sqrt(vx * vx + vy * vy + vz * vz)), 1e-9)
    v_dot = (vx * dvx + vy * dvy + vz * dvz) / v
    dt_fd = 1.0e-5
    x1 = np.asarray(x, dtype=float) + dt_fd * np.asarray(dx, dtype=float)
    th_dot = (path_angle_from_x(x1) - path_angle_from_x(x)) / dt_fd
    return alpha_dot, q_dot, v_dot, th_dot


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
    d_dt: float = 1.0e-3,
) -> dict[str, float]:
    del thetatr
    x_base = np.asarray(x0, dtype=float).copy()
    u_base = np.asarray(u0, dtype=float).copy()

    a0 = _alpha_from_x(x_base)
    q0 = float(x_base[5])
    de0_rad = float(x_base[16]) * np.pi / 180.0
    v0 = float(np.linalg.norm(x_base[0:3]))
    v0 = max(v0, 1.0)
    theta0 = path_angle_from_x(x_base)

    def eval_at(
        alpha: float,
        q: float,
        de_rad: float,
        v_mag: float,
        theta: float,
    ) -> tuple[float, float, float, float]:
        x = x_base.copy()
        u = u_base.copy()
        _set_alpha(x, alpha)
        _set_speed(x, v_mag)
        x[8] = alpha + theta
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
    ) -> tuple[float, float, float, float]:
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
        ap, qp, vp, tp = eval_at(*hi)
        am, qm, vm, tm = eval_at(*lo)
        den = 2.0 * step
        return (
            (ap - am) / den,
            (qp - qm) / den,
            (vp - vm) / den,
            (tp - tm) / den,
        )

    la_, ma_, xa_, ta_ = deriv_wrt("alpha", d_alpha, d_q, d_de_rad, d_v, d_theta)
    lq_, mq_, xq_, tq_ = deriv_wrt("q", d_alpha, d_q, d_de_rad, d_v, d_theta)
    lde_, mde_, xde_, tde_ = deriv_wrt("de", d_alpha, d_q, d_de_rad, d_v, d_theta)
    lv_, mv_, xv_, tv_ = deriv_wrt("v", d_alpha, d_q, d_de_rad, d_v, d_theta)
    lth_, mth_, xth_, tth_ = deriv_wrt("theta", d_alpha, d_q, d_de_rad, d_v, d_theta)

    # тяга: РУД x[15] и команда u[0] вместе
    xp, xm = x_base.copy(), x_base.copy()
    up, um = u_base.copy(), u_base.copy()
    xp[15] += d_dt
    xm[15] -= d_dt
    up[0] += d_dt
    um[0] -= d_dt
    xdt_ = (_long_rates(xp, up, la)[2] - _long_rates(xm, um, la)[2]) / (2.0 * d_dt)

    adot0, qdot0, vdot0, tdot0 = eval_at(a0, q0, de0_rad, v0, theta0)
    del xq_, tq_

    return {
        "alpha0": a0,
        "q0": q0,
        "delta_e0": de0_rad,
        "v0": v0,
        "theta0": theta0,
        "h0": float(x_base[10]),
        "delta_t0": float(x_base[15]),
        "alpha_dot0": adot0,
        "q_dot0": qdot0,
        "v_dot0": vdot0,
        "theta_dot0": tdot0,
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
        "M_dedot": 0.0,
        "X_alpha": float(xa_),
        "X_de": float(xde_),
        "X_v": float(xv_),
        "X_theta": float(xth_),
        "T_alpha": float(ta_),
        "T_de": float(tde_),
        "T_v": float(tv_),
        "T_theta": float(tth_),
        "X_dt": float(xdt_),
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
            th["M_dedot"],
            th["X_alpha"],
            th["X_de"],
            th["X_v"],
            th["X_theta"],
            th["T_alpha"],
            th["T_de"],
            th["T_v"],
            th["T_theta"],
            th["X_dt"],
        ],
        dtype=float,
    )


def coeff_delta_ekf_minus_theory(x_sp: np.ndarray, th_vec: np.ndarray) -> np.ndarray:
    n = len(PARAM_NAMES)
    return np.asarray(x_sp[:n], dtype=float) - np.asarray(th_vec[:n], dtype=float)
