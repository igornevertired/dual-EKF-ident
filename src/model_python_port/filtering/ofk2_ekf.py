"""
ОФК-2: продольная модель, 5 ДУ. Идентификация L*, M*, X*.

    α̇ = Lα·δα + Lq·q + Lδe·δδe + Lv·δV + Lθ·δθ
    q̇ = Mα·δα + Mq·q + Mδe·δδe + Mv·δV + Mθ·δθ
    V̇ = Xα·δα + Xq·q + Xδe·δδe + Xv·δV + Xθ·δθ
    θ̇ = q
    ḣ = V sin(θ−α)

    az ≈ az0 − (V/g)·(Lα·δα + (Lq−1)·q + Lδe·δδe + Lv·δV + Lθ·δθ)

Состояние: x = [Lα…Lθ, Mα…Mθ, Xα…Xθ]  (15 коэфф.)
Z = [α̇_fd, q̇_fd, V̇_fd, az]
θ̇ и ḣ — кинематика (известны), в оценку коэффициентов не входят.
"""

from __future__ import annotations

import numpy as np

from ..common.c_ang import c_ang
from .ofk2_theory import N_REG, PARAM_NAMES

N_PARAM = len(PARAM_NAMES)
N_STATE = N_PARAM
N_MEAS = 4
N_L = N_REG
N_M = N_REG
N_X = N_REG
G0 = 9.80665

_EXC_DDE = 0.003
_EXC_Q = 0.005
_EXC_DA = 0.008
_EXC_DV = 0.05
_EXC_DTH = 0.003


def initial_state(param0: np.ndarray) -> np.ndarray:
    return np.asarray(param0, dtype=float).reshape(N_STATE).copy()


def initial_covariance(
    param0: np.ndarray | None = None,
    *,
    coeff_start_err: float = 0.3,
    scale_ref: np.ndarray | None = None,
) -> np.ndarray:
    """P₀: 3σ покрывает ``coeff_start_err·|scale_ref|``.

    ``scale_ref`` — масштаб истинных коэффициентов (эталон балансировки),
    не стартовая догадка: иначе при малом θ̂(0) полоса схлопывается.
    """
    abs_floor = np.array(
        [
            0.05, 0.05, 0.02, 0.01, 0.01,
            0.05, 0.05, 0.05, 0.01, 0.01,
            0.05, 0.05, 0.02, 0.01, 0.01,
        ],
        dtype=float,
    )
    if param0 is None and scale_ref is None:
        sig = np.array(
            [
                0.30, 0.10, 0.20, 0.05, 0.05,
                0.30, 0.30, 0.30, 0.05, 0.05,
                0.30, 0.10, 0.20, 0.05, 0.05,
            ],
            dtype=float,
        )
    else:
        ref = scale_ref if scale_ref is not None else param0
        ref = np.asarray(ref, dtype=float).reshape(N_STATE)
        sig = np.maximum(np.abs(ref) * float(coeff_start_err) / 3.0, abs_floor * 0.2)
    return np.diag(sig**2)


def process_noise(dt: float, *, adapt: bool, q_std: float = 0.0) -> np.ndarray:
    """Дискретная Q. q_std=0 — постоянные коэффициенты (P только сжимается)."""
    q = float(q_std)
    if q <= 0.0:
        return np.zeros((N_STATE, N_STATE), dtype=float)
    return np.eye(N_STATE, dtype=float) * (q * q)


def measurement_covariance(
    sigma_adot: float = 0.025,
    sigma_qdot: float = 0.002,
    sigma_vdot: float = 0.15,
    sigma_az: float = 0.023,
) -> np.ndarray:
    return np.diag(
        np.array([sigma_adot, sigma_qdot, sigma_vdot, sigma_az], dtype=float) ** 2
    )


def _has_excitation(
    da: float,
    q: float,
    dde: float,
    dv: float,
    dtheta: float,
) -> bool:
    return (
        abs(float(dde)) >= _EXC_DDE
        or abs(float(q)) >= _EXC_Q
        or abs(float(da)) >= _EXC_DA
        or abs(float(dv)) >= _EXC_DV
        or abs(float(dtheta)) >= _EXC_DTH
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


def build_regressors(
    alpha: float,
    q: float,
    delta_e: float,
    v: float,
    theta: float,
    trim: dict[str, float],
) -> np.ndarray:
    """[δα, q, δδe, δV, δθ]."""
    return np.array(
        [
            float(alpha) - trim["alpha0"],
            float(q),
            float(delta_e) - trim["delta_e0"],
            float(v) - trim["v0"],
            float(theta) - trim["theta0"],
        ],
        dtype=float,
    )


def build_z_kinematics(
    alpha: float,
    q: float,
    delta_e: float,
    v: float,
    theta: float,
    az: float,
    trim: dict[str, float],
) -> np.ndarray:
    """[δα, q, δδe, δV, δθ, az] для лога."""
    reg = build_regressors(alpha, q, delta_e, v, theta, trim)
    return np.array([*reg, float(az)], dtype=float)


def long_kinematics(
    da: float,
    q: float,
    dv: float,
    dtheta: float,
    *,
    v0: float,
    gamma0: float,
) -> tuple[float, float]:
    """θ̇ = q,  ḣ = V sin(θ−α) в приращениях от trim."""
    theta_dot = float(q)
    h_dot = float(v0 * np.cos(gamma0) * (dtheta - da) + np.sin(gamma0) * dv)
    return theta_dot, h_dot


def _predict_z(
    coeffs: np.ndarray,
    phi: np.ndarray,
    *,
    v: float,
    az0: float,
) -> np.ndarray:
    l = coeffs[:N_L]
    m = coeffs[N_L : N_L + N_M]
    xx = coeffs[N_L + N_M :]
    alpha_dot = float(l @ phi)
    qdot = float(m @ phi)
    vdot = float(xx @ phi)
    az = float(az0) - (v / G0) * (
        l[0] * phi[0] + (l[1] - 1.0) * phi[1] + l[2] * phi[2] + l[3] * phi[3] + l[4] * phi[4]
    )
    return np.array([alpha_dot, qdot, vdot, az], dtype=float)


def ekf_step(
    x: np.ndarray,
    p: np.ndarray,
    *,
    da: float,
    q: float,
    dde: float,
    dv: float,
    dtheta: float,
    az: float,
    v: float,
    az0: float,
    dt: float,
    da_prev: float | None,
    q_prev: float | None,
    v_prev: float | None = None,
    r: np.ndarray | None = None,
    q_std: float = 0.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float]:
    x = np.asarray(x, dtype=float).reshape(N_STATE)
    p = np.asarray(p, dtype=float)
    da, q, dde = float(da), float(q), float(dde)
    dv, dtheta, az = float(dv), float(dtheta), float(az)
    v = max(float(v), 1.0)
    dt = float(dt)
    if r is None:
        r = measurement_covariance()

    adapt = _has_excitation(da, q, dde, dv, dtheta)
    p_pred = p + process_noise(dt, adapt=adapt, q_std=q_std)
    p_pred = 0.5 * (p_pred + p_pred.T)
    x_pred = x.copy()
    innov_post = np.zeros(N_MEAS, dtype=float)
    innov_prior = np.full(N_MEAS, np.nan, dtype=float)
    sqrt_s = np.full(N_MEAS, np.nan, dtype=float)

    if da_prev is None or q_prev is None or v_prev is None or dt <= 0.0 or not adapt:
        return x_pred, p_pred, innov_post, innov_prior, sqrt_s, da, q

    adot = (da - float(da_prev)) / dt
    qdot = (q - float(q_prev)) / dt
    vdot = (v - float(v_prev)) / dt
    phi = np.array([da, q, dde, dv, dtheta], dtype=float)

    z_pred = _predict_z(x_pred, phi, v=v, az0=az0)
    z = np.array([adot, qdot, vdot, az], dtype=float)

    h = np.zeros((N_MEAS, N_STATE), dtype=float)
    h[0, :N_L] = phi
    h[1, N_L : N_L + N_M] = phi
    h[2, N_L + N_M :] = phi
    k_az = -(v / G0)
    h[3, :N_L] = k_az * phi

    delta = z - z_pred
    ph_t = p_pred @ h.T
    s = h @ ph_t + r
    s = 0.5 * (s + s.T)
    try:
        k = np.linalg.solve(s, ph_t.T).T
    except np.linalg.LinAlgError:
        return x_pred, p_pred, innov_post, innov_prior, sqrt_s, da, q

    innov_prior = delta.copy()
    sqrt_s = np.sqrt(np.maximum(np.diag(s), 1e-30))

    x_new = x_pred + k @ delta
    ik = np.eye(N_STATE) - k @ h
    p_new = 0.5 * (
        (ik @ p_pred @ ik.T + k @ r @ k.T) + (ik @ p_pred @ ik.T + k @ r @ k.T).T
    )

    z_hat = _predict_z(x_new, phi, v=v, az0=az0)
    innov_post = z - z_hat
    return x_new, p_new, innov_post, innov_prior, sqrt_s, da, q
