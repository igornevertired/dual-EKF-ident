"""
ОФК-2 — система (15) в обозначениях L/M/X/Θ.

    ΔV̇  = Xα δα + Xδe δδe + Xv δV + Xθ δθ
    Δα̇  = Lα δα + 1·δq + Lδe δδe + Lv δV + Lθ δθ
    Δθ̇  = Θα δα + Θδe δδe + Θv δV + Θθ δθ
    Δω̇z = Mα δα + Mq δq + Mδe δδe + Mv δV + Mθ δθ + Mδė δ̇e
    (+ Xδt ΔδT в 1-й строке — известный вход тяги)

Прогноз — RK4 с линейной интерполяцией δe, δT внутри шага.

θ из ОФК-1: tgθ = Vy/√(Vx²+Vz²). Z = [δα, δq, δV, δθ].
"""

from __future__ import annotations

from typing import NamedTuple

import numpy as np

from ..common.c_ang import c_ang
from .ofk2_theory import (
    ESTIMATED_PARAM_INDICES,
    FROZEN_PARAM_INDICES,
    N_L,
    N_M,
    N_TH,
    N_X,
    PARAM_NAMES,
    path_angle_from_nav,
)

N_PARAM = len(PARAM_NAMES)
N_MOTION = 4
N_STATE = N_PARAM + N_MOTION
N_MEAS = 4
I_DA = N_PARAM
I_DQ = N_PARAM + 1
I_DV = N_PARAM + 2
I_DTH = N_PARAM + 3
I_Q = I_DQ
G0 = 9.80665
_FROZEN = np.asarray(FROZEN_PARAM_INDICES, dtype=int)
_ESTIMATED = np.asarray(ESTIMATED_PARAM_INDICES, dtype=int)

_P0_DA = 0.03**2
_P0_Q = 0.03**2
_P0_DV = 1.0**2
_P0_DTH = 0.03**2
_Q_DA = 1.0e-8
_Q_Q = 1.0e-8
_Q_DV = 1.0e-4
_Q_DTH = 1.0e-8

_ABS_FLOOR = np.array(
    [
        0.05, 0.05, 0.02, 0.01, 0.05,
        0.05, 0.05, 0.05, 0.01, 0.05, 0.05,
        0.05, 0.02, 0.01, 0.50,
        0.05, 0.02, 0.01, 0.05,
        0.05,
    ],
    dtype=float,
)


def initial_state(
    param0: np.ndarray,
    da: float = 0.0,
    dq: float = 0.0,
    dv: float = 0.0,
    dth: float = 0.0,
    *,
    q: float | None = None,
) -> np.ndarray:
    x = np.zeros(N_STATE, dtype=float)
    x[:N_PARAM] = np.asarray(param0, dtype=float).reshape(N_PARAM)
    x[I_DA] = float(da)
    x[I_DQ] = float(dq if q is None else q)
    x[I_DV] = float(dv)
    x[I_DTH] = float(dth)
    return x


def initial_covariance(
    param0: np.ndarray | None = None,
    *,
    coeff_start_err: float = 0.3,
    scale_ref: np.ndarray | None = None,
) -> np.ndarray:
    if param0 is None and scale_ref is None:
        sig = np.array(
            [
                0.30, 0.10, 0.20, 0.05, 0.30,
                0.30, 0.30, 0.30, 0.05, 0.30, 0.20,
                0.30, 0.20, 0.05, 0.50,
                0.30, 0.20, 0.05, 0.30,
                0.30,
            ],
            dtype=float,
        )
    else:
        ref = scale_ref if scale_ref is not None else param0
        ref = np.asarray(ref, dtype=float).reshape(N_PARAM)
        # 1σ = ожидаемая стартовая ошибка. Раньше было /3: старт +30 % лежал на 3σ,
        # и фильтр почти не сдвигал параметры за короткий дублет.
        sig = np.maximum(np.abs(ref) * float(coeff_start_err), _ABS_FLOOR * 0.2)
    sig = np.asarray(sig, dtype=float).copy()
    sig[_FROZEN] = 0.0
    p = np.zeros((N_STATE, N_STATE), dtype=float)
    p[:N_PARAM, :N_PARAM] = np.diag(sig**2)
    p[I_DA, I_DA] = _P0_DA
    p[I_DQ, I_DQ] = _P0_Q
    p[I_DV, I_DV] = _P0_DV
    p[I_DTH, I_DTH] = _P0_DTH
    return p


def process_noise(dt: float, *, q_std: float = 0.0) -> np.ndarray:
    del dt
    q = np.zeros((N_STATE, N_STATE), dtype=float)
    q[I_DA, I_DA] = _Q_DA
    q[I_DQ, I_DQ] = _Q_Q
    q[I_DV, I_DV] = _Q_DV
    q[I_DTH, I_DTH] = _Q_DTH
    qc = float(q_std)
    if qc > 0.0:
        for i in _ESTIMATED:
            q[i, i] = qc * qc
    return q


def _pin_frozen(
    x: np.ndarray,
    p: np.ndarray,
    param_fixed: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Lv держится на trim; его P обнуляется."""
    if param_fixed is None:
        return x, p
    fixed = np.asarray(param_fixed, dtype=float).reshape(N_PARAM)
    x = x.copy()
    x[_FROZEN] = fixed[_FROZEN]
    p = p.copy()
    p[_FROZEN, :] = 0.0
    p[:, _FROZEN] = 0.0
    return x, p


def measurement_covariance(
    sigma_alpha: float = 1.0e-4,
    sigma_q: float = 5.0e-5,
    sigma_v: float = 0.01,
    sigma_theta: float = 1.0e-4,
) -> np.ndarray:
    """σ ≈ 3–5 × фактической ошибки измерений после ОФК-1.

    Факт (240 с, после 30 с): α 3e-5 рад, q 1e-5 рад/с, V 3e-3 м/с, θ 4e-5 рад.
    Прежние 0.01 / 0.003 / 0.4 / 0.01 были в 100–300 раз завышены — фильтр
    почти игнорировал измерения и не успевал ничего выучить за дублет.
    """
    return np.diag(
        np.array([sigma_alpha, sigma_q, sigma_v, sigma_theta], dtype=float) ** 2
    )


def reconstruct_alpha_from_nav(np_bins: np.ndarray, cbn: np.ndarray) -> tuple[float, float]:
    v_n = np.array([np_bins[0], np_bins[1], np_bins[2]], dtype=float)
    v_b = np.asarray(cbn, dtype=float).T @ v_n
    vx, vy = float(v_b[0]), float(v_b[1])
    v = float(np.linalg.norm(v_b))
    v = max(v, 1.0)
    alpha = -np.arctan2(vy, vx if abs(vx) > 1e-9 else 1e-9)
    return float(alpha), v


def reconstruct_theta_from_nav(cbn: np.ndarray) -> float:
    return float(c_ang(np.asarray(cbn, dtype=float))[1])


def reconstruct_path_angle_from_nav(np_cons: np.ndarray) -> float:
    """θ из ОФК-1: tgθ = Vh / √(Vn²+Ve²)."""
    npv = np.asarray(np_cons, dtype=float).reshape(-1)
    return path_angle_from_nav(float(npv[0]), float(npv[1]), float(npv[2]))


def reconstruct_theta_from_path(alpha: float, np_cons: np.ndarray) -> float:
    """Совместимость: раньше здесь был тангаж α+γ. Теперь — угол наклона траектории."""
    del alpha
    return reconstruct_path_angle_from_nav(np_cons)


class Ofk2Signals(NamedTuple):
    alpha: float
    v: float
    theta: float
    q: float
    az: float
    de: float
    da: float
    dq: float
    dde: float
    dv: float
    dtheta: float
    ddt: float = 0.0


def signals_from_sensors(
    np_cons: np.ndarray,
    cbn: np.ndarray,
    w_cons: np.ndarray,
    a_m: np.ndarray,
    de_deg: float,
    trim: dict[str, float],
    throttle: float | None = None,
) -> Ofk2Signals:
    """α, V из NP+Cbn; q из ДУС; θ из NP ОФК-1; δT — РУД; отклонения от балансировки."""
    alpha, v = reconstruct_alpha_from_nav(np_cons, cbn)
    theta = reconstruct_path_angle_from_nav(np_cons)
    q = float(np.asarray(w_cons, dtype=float).reshape(3)[2])
    az = float(np.asarray(a_m, dtype=float).reshape(3)[1]) / G0
    de = float(de_deg) * np.pi / 180.0
    return Ofk2Signals(
        alpha=alpha,
        v=v,
        theta=theta,
        q=q,
        az=az,
        de=de,
        da=alpha - trim["alpha0"],
        dq=q - trim["q0"],
        dde=de - trim["delta_e0"],
        dv=v - trim["v0"],
        dtheta=theta - trim["theta0"],
        ddt=0.0 if throttle is None else float(throttle) - trim.get("delta_t0", 0.0),
    )


def build_regressors(
    alpha: float,
    q: float,
    delta_e: float,
    v: float,
    theta: float,
    trim: dict[str, float],
) -> np.ndarray:
    """φ_L = [δα, δq, δδe, δV, δθ]."""
    return np.array(
        [
            float(alpha) - trim["alpha0"],
            float(q) - trim["q0"],
            float(delta_e) - trim["delta_e0"],
            float(v) - trim["v0"],
            float(theta) - trim["theta0"],
        ],
        dtype=float,
    )


def build_z_kinematics(
    alpha: float,
    q: float,
    v: float,
    theta: float,
    delta_e: float,
    trim: dict[str, float],
) -> np.ndarray:
    """Измерение Z = [δα, δq, δV, δθ]."""
    del delta_e
    return np.array(
        [
            float(alpha) - trim["alpha0"],
            float(q) - trim["q0"],
            float(v) - trim["v0"],
            float(theta) - trim["theta0"],
        ],
        dtype=float,
    )


_I_L = slice(0, N_L)
_I_M = slice(N_L, N_L + N_M)
_I_X = slice(N_L + N_M, N_L + N_M + N_X)
_I_T = slice(N_L + N_M + N_X, N_L + N_M + N_X + N_TH)
_I_XDT = PARAM_NAMES.index("Xδt")
_N_SUB = 4


def _predict_z(x: np.ndarray) -> np.ndarray:
    return np.array([x[I_DA], x[I_DQ], x[I_DV], x[I_DTH]], dtype=float)


def _meas_jacobian() -> np.ndarray:
    h = np.zeros((N_MEAS, N_STATE), dtype=float)
    h[0, I_DA] = 1.0
    h[1, I_DQ] = 1.0
    h[2, I_DV] = 1.0
    h[3, I_DTH] = 1.0
    return h


def _rhs(par: np.ndarray, s: np.ndarray, dde: float, dde_dot: float, ddt: float) -> np.ndarray:
    """Правая часть (15) + Xδt ΔδT. s = [δα, δq, δV, δθ]."""
    da, dq, dv, dth = s
    l, m, xx, tt = par[_I_L], par[_I_M], par[_I_X], par[_I_T]
    # (15) строка 2: δα, +Δωz, δB, ΔV, Δθ
    da_dot = l @ np.array([da, dq, dde, dv, dth])
    # (15) строка 4: δα, Δωz, δB, ΔV, Δθ, δ̇B
    dq_dot = m @ np.array([da, dq, dde, dv, dth, dde_dot])
    # (15) строка 1: нет Δωz; + тяга
    dv_dot = xx @ np.array([da, dde, dv, dth]) + par[_I_XDT] * ddt
    # (15) строка 3: нет Δωz
    dth_dot = tt @ np.array([da, dde, dv, dth])
    return np.array([da_dot, dq_dot, dv_dot, dth_dot], dtype=float)


def _propagate(
    x: np.ndarray,
    dt: float,
    dde0: float,
    dde1: float,
    ddt0: float,
    ddt1: float,
    dde_dot: float,
) -> np.ndarray:
    """RK4 на _N_SUB подшагах; δe, δT — линейно между отсчётами k−1 и k.

    Эйлер на dt=0.2 с при короткопериодическом движении (|λ|≈0.8 1/с)
    и δe, взятый на конце интервала, дают смещение M*, L* на 10–20 %.
    """
    par = x[:N_PARAM]
    s = x[N_PARAM:].copy()
    h = dt / _N_SUB
    for j in range(_N_SUB):
        ta, tm, tb = j / _N_SUB, (j + 0.5) / _N_SUB, (j + 1) / _N_SUB
        de_a, de_m, de_b = (dde0 + (dde1 - dde0) * c for c in (ta, tm, tb))
        dt_a, dt_m, dt_b = (ddt0 + (ddt1 - ddt0) * c for c in (ta, tm, tb))
        k1 = _rhs(par, s, de_a, dde_dot, dt_a)
        k2 = _rhs(par, s + 0.5 * h * k1, de_m, dde_dot, dt_m)
        k3 = _rhs(par, s + 0.5 * h * k2, de_m, dde_dot, dt_m)
        k4 = _rhs(par, s + h * k3, de_b, dde_dot, dt_b)
        s = s + h / 6.0 * (k1 + 2.0 * k2 + 2.0 * k3 + k4)
    x_pred = x.copy()
    x_pred[N_PARAM:] = s
    return x_pred


def _predict(
    x: np.ndarray,
    dt: float,
    dde: float,
    dde_dot: float = 0.0,
    *,
    dde_prev: float | None = None,
    ddt: float = 0.0,
    ddt_prev: float | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    dde0 = float(dde) if dde_prev is None else float(dde_prev)
    ddt0 = float(ddt) if ddt_prev is None else float(ddt_prev)
    args = (float(dt), dde0, float(dde), ddt0, float(ddt), float(dde_dot))
    x_pred = _propagate(x, *args)
    # F — численно (центральные разности) по оцениваемым и δα, δq, δV, δθ
    f = np.eye(N_STATE, dtype=float)
    cols = list(_ESTIMATED) + [I_DA, I_DQ, I_DV, I_DTH]
    for i in cols:
        e = 1.0e-6 * max(1.0, abs(float(x[i])))
        xp, xm = x.copy(), x.copy()
        xp[i] += e
        xm[i] -= e
        f[:, i] = (_propagate(xp, *args) - _propagate(xm, *args)) / (2.0 * e)
    return x_pred, f


def ekf_step(
    x: np.ndarray,
    p: np.ndarray,
    *,
    da: float,
    dq: float,
    dv: float,
    dde: float,
    dt: float,
    dtheta: float = 0.0,
    dde_dot: float = 0.0,
    dde_prev: float | None = None,
    ddt: float = 0.0,
    ddt_prev: float | None = None,
    x_theta: float = 0.0,
    param_fixed: np.ndarray | None = None,
    r: np.ndarray | None = None,
    q_std: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Шаг EKF. Измерение Z = [δα, δq, δV, δθ]. Lv — на trim, если передан param_fixed."""
    del x_theta
    x = np.asarray(x, dtype=float).reshape(N_STATE)
    p = np.asarray(p, dtype=float)
    x, p = _pin_frozen(x, p, param_fixed)
    dt = float(dt)
    if r is None:
        r = measurement_covariance()

    innov_post = np.zeros(N_MEAS, dtype=float)
    innov_prior = np.full(N_MEAS, np.nan, dtype=float)
    sqrt_s = np.full(N_MEAS, np.nan, dtype=float)
    if dt <= 0.0:
        return x.copy(), 0.5 * (p + p.T), innov_post, innov_prior, sqrt_s

    x_pred, f = _predict(
        x, dt, float(dde), dde_dot=float(dde_dot),
        dde_prev=dde_prev, ddt=float(ddt), ddt_prev=ddt_prev,
    )
    x_pred, _ = _pin_frozen(x_pred, p, param_fixed)
    p_pred = f @ p @ f.T + process_noise(dt, q_std=q_std)
    p_pred = 0.5 * (p_pred + p_pred.T)
    _, p_pred = _pin_frozen(x_pred, p_pred, param_fixed)

    z = np.array([float(da), float(dq), float(dv), float(dtheta)], dtype=float)
    z_pred = _predict_z(x_pred)
    h = _meas_jacobian()

    delta = z - z_pred
    ph_t = p_pred @ h.T
    s = h @ ph_t + r
    s = 0.5 * (s + s.T)
    try:
        k = np.linalg.solve(s, ph_t.T).T
    except np.linalg.LinAlgError:
        return x_pred, p_pred, innov_post, innov_prior, sqrt_s

    innov_prior = delta.copy()
    sqrt_s = np.sqrt(np.maximum(np.diag(s), 1e-30))
    x_new = x_pred + k @ delta
    ik = np.eye(N_STATE) - k @ h
    p_new = 0.5 * (
        (ik @ p_pred @ ik.T + k @ r @ k.T) + (ik @ p_pred @ ik.T + k @ r @ k.T).T
    )
    x_new, p_new = _pin_frozen(x_new, p_new, param_fixed)
    innov_post = z - _predict_z(x_new)
    return x_new, p_new, innov_post, innov_prior, sqrt_s
