"""
ОФК-2: короткопериодическая продольная модель, L* и M*.

Уравнения (приращения от trim)::

    α̇ = Lα·δα + Lq·q + Lδe·δδe
    q̇ = Mα·δα + Mq·q + Mδe·δδe
    az ≈ az0 − (V/g)·(Lα·δα + (Lq−1)·q + Lδe·δδe)

Состояние: x = [Lα, Lq, Lδe, Mα, Mq, Mδe]
Регрессоры δα, q, δδe — из БНК (α, ДУС, привод); без theory-anchor.
Z = [α̇_fd, q̇_fd, az]  (equation-error + перегрузка)
"""

from __future__ import annotations

import numpy as np

from .ofk2_theory import PARAM_NAMES

N_PARAM = len(PARAM_NAMES)
N_STATE = N_PARAM
N_MEAS = 3
G0 = 9.80665

_EXC_DDE = 0.003
_EXC_Q = 0.005
_EXC_DA = 0.008


def initial_state(param0: np.ndarray) -> np.ndarray:
    return np.asarray(param0, dtype=float).reshape(N_STATE).copy()


def initial_covariance() -> np.ndarray:
    # Lq≈1 — узкий априор (почти кинематика); остальные шире
    return np.diag(np.array([0.30, 0.08, 0.20, 0.30, 0.30, 0.30], dtype=float) ** 2)


def process_noise(dt: float, *, adapt: bool) -> np.ndarray:
    if not adapt:
        return np.zeros((N_STATE, N_STATE), dtype=float)
    q = np.array([3e-6, 5e-7, 2e-6, 3e-6, 3e-6, 3e-6], dtype=float) * float(dt)
    return np.diag(q)


def measurement_covariance(
    sigma_adot: float = 0.06,
    sigma_qdot: float = 0.04,
    sigma_az: float = 0.08,
) -> np.ndarray:
    return np.diag(np.array([sigma_adot, sigma_qdot, sigma_az], dtype=float) ** 2)


def _has_excitation(da: float, q: float, dde: float) -> bool:
    return (
        abs(float(dde)) >= _EXC_DDE
        or abs(float(q)) >= _EXC_Q
        or abs(float(da)) >= _EXC_DA
    )


def reconstruct_alpha_from_nav(np_bins: np.ndarray, cbn: np.ndarray) -> tuple[float, float]:
    v_n = np.array([np_bins[0], np_bins[1], np_bins[2]], dtype=float)
    v_b = np.asarray(cbn, dtype=float).T @ v_n
    vx, vy = float(v_b[0]), float(v_b[1])
    v = float(np.linalg.norm(v_b))
    v = max(v, 1.0)
    alpha = -np.arctan2(vy, vx if abs(vx) > 1e-9 else 1e-9)
    return float(alpha), v


def build_z_kinematics(
    alpha: float,
    q: float,
    delta_e: float,
    az: float,
    trim: dict[str, float],
) -> np.ndarray:
    """[δα, q, δδe, az] для лога и регрессоров."""
    return np.array(
        [
            float(alpha) - trim["alpha0"],
            float(q),
            float(delta_e) - trim["delta_e0"],
            float(az),
        ],
        dtype=float,
    )


def ekf_step(
    x: np.ndarray,
    p: np.ndarray,
    *,
    da: float,
    q: float,
    dde: float,
    az: float,
    v: float,
    az0: float,
    dt: float,
    alpha_smooth: float | None,
    alpha_smooth_prev: float | None,
    q_smooth: float | None,
    q_smooth_prev: float | None,
    ema_alpha: float = 0.35,
    r: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float, float, float, float]:
    """
    Returns
    -------
    x_new, p_new, innov[3], a_s, a_s (prev next), q_s, q_s (prev next)
    """
    x = np.asarray(x, dtype=float).reshape(N_STATE)
    p = np.asarray(p, dtype=float)
    da, q, dde, az = float(da), float(q), float(dde), float(az)
    v = max(float(v), 1.0)
    dt = float(dt)
    if r is None:
        r = measurement_covariance()

    a_raw = float(da)  # сглаживаем δα как прокси α (trim const)
    if alpha_smooth is None:
        a_s = a_raw
    else:
        ea = float(ema_alpha)
        a_s = ea * a_raw + (1.0 - ea) * float(alpha_smooth)

    if q_smooth is None:
        q_s = q
    else:
        ea = float(ema_alpha)
        q_s = ea * q + (1.0 - ea) * float(q_smooth)

    adapt = _has_excitation(a_s, q_s, dde)
    p_pred = p + process_noise(dt, adapt=adapt)
    p_pred = 0.5 * (p_pred + p_pred.T)
    x_pred = x.copy()
    innov = np.zeros(N_MEAS, dtype=float)

    if (
        alpha_smooth_prev is None
        or q_smooth_prev is None
        or dt <= 0.0
        or not adapt
    ):
        return x_pred, p_pred, innov, a_s, a_s, q_s, q_s

    adot = (a_s - float(alpha_smooth_prev)) / dt
    qdot = (q_s - float(q_smooth_prev)) / dt
    # регрессоры на текущем шаге
    phi = np.array([a_s, q_s, dde], dtype=float)

    la, lq, lde, ma, mq, mde = x_pred
    z_pred = np.array(
        [
            la * phi[0] + lq * phi[1] + lde * phi[2],
            ma * phi[0] + mq * phi[1] + mde * phi[2],
            float(az0) - (v / G0) * (la * phi[0] + (lq - 1.0) * phi[1] + lde * phi[2]),
        ],
        dtype=float,
    )
    z = np.array([adot, qdot, az], dtype=float)

    H = np.zeros((N_MEAS, N_STATE), dtype=float)
    H[0, 0:3] = phi
    H[1, 3:6] = phi
    k_az = -(v / G0)
    H[2, 0] = k_az * phi[0]
    H[2, 1] = k_az * phi[1]
    H[2, 2] = k_az * phi[2]

    delta = z - z_pred
    ph_t = p_pred @ H.T
    s = H @ ph_t + r
    s = 0.5 * (s + s.T)
    try:
        k = np.linalg.solve(s, ph_t.T).T
    except np.linalg.LinAlgError:
        return x_pred, p_pred, innov, a_s, a_s, q_s, q_s

    x_new = x_pred + k @ delta
    ik = np.eye(N_STATE) - k @ H
    p_new = 0.5 * (
        (ik @ p_pred @ ik.T + k @ r @ k.T) + (ik @ p_pred @ ik.T + k @ r @ k.T).T
    )

    la, lq, lde, ma, mq, mde = x_new
    z_hat = np.array(
        [
            la * phi[0] + lq * phi[1] + lde * phi[2],
            ma * phi[0] + mq * phi[1] + mde * phi[2],
            float(az0) - (v / G0) * (la * phi[0] + (lq - 1.0) * phi[1] + lde * phi[2]),
        ],
        dtype=float,
    )
    innov = z - z_hat
    return x_new, p_new, innov, a_s, a_s, q_s, q_s
