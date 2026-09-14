"""
ОФК-2 (legacy): модель Hoff с 3 регрессорами и 6 коэффициентами.

    α̇ = Lα·δα + Lq·q + Lδe·δδe
    q̇ = Mα·δα + Mq·q + Mδe·δδe
    az ≈ az0 − (V/g)·(Lα·δα + (Lq−1)·q + Lδe·δδe)
"""

from __future__ import annotations

import numpy as np

LEGACY_PARAM_NAMES = ("Lα", "Lq", "Lδe", "Mα", "Mq", "Mδe")
N_PARAM = len(LEGACY_PARAM_NAMES)
N_STATE = N_PARAM
N_MEAS = 3
G0 = 9.80665

_EXC_DDE = 0.003
_EXC_Q = 0.005
_EXC_DA = 0.008


def initial_state(param0: np.ndarray) -> np.ndarray:
    return np.asarray(param0, dtype=float).reshape(N_STATE).copy()


def initial_covariance(
    param0: np.ndarray | None = None,
    *,
    coeff_start_err: float = 0.3,
    scale_ref: np.ndarray | None = None,
) -> np.ndarray:
    abs_floor = np.array([0.05, 0.05, 0.02, 0.05, 0.05, 0.05], dtype=float)
    if param0 is None and scale_ref is None:
        sig = np.array([0.30, 0.10, 0.20, 0.30, 0.30, 0.30], dtype=float)
    else:
        ref = scale_ref if scale_ref is not None else param0
        ref = np.asarray(ref, dtype=float).reshape(N_STATE)
        sig = np.maximum(np.abs(ref) * float(coeff_start_err) / 3.0, abs_floor * 0.2)
    return np.diag(sig**2)


def process_noise(dt: float, *, adapt: bool) -> np.ndarray:
    return np.zeros((N_STATE, N_STATE), dtype=float)


def measurement_covariance(
    sigma_adot: float = 0.025,
    sigma_qdot: float = 0.002,
    sigma_az: float = 0.023,
) -> np.ndarray:
    return np.diag(np.array([sigma_adot, sigma_qdot, sigma_az], dtype=float) ** 2)


def _has_excitation(da: float, q: float, dde: float) -> bool:
    return (
        abs(float(dde)) >= _EXC_DDE
        or abs(float(q)) >= _EXC_Q
        or abs(float(da)) >= _EXC_DA
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
    da_prev: float | None,
    q_prev: float | None,
    r: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float, float]:
    x = np.asarray(x, dtype=float).reshape(N_STATE)
    p = np.asarray(p, dtype=float)
    da, q, dde, az = float(da), float(q), float(dde), float(az)
    v = max(float(v), 1.0)
    dt = float(dt)
    if r is None:
        r = measurement_covariance()

    adapt = _has_excitation(da, q, dde)
    p_pred = p + process_noise(dt, adapt=adapt)
    p_pred = 0.5 * (p_pred + p_pred.T)
    x_pred = x.copy()
    innov_post = np.zeros(N_MEAS, dtype=float)
    innov_prior = np.full(N_MEAS, np.nan, dtype=float)
    sqrt_s = np.full(N_MEAS, np.nan, dtype=float)

    if da_prev is None or q_prev is None or dt <= 0.0 or not adapt:
        return x_pred, p_pred, innov_post, innov_prior, sqrt_s, da, q

    adot = (da - float(da_prev)) / dt
    qdot = (q - float(q_prev)) / dt
    phi = np.array([da, q, dde], dtype=float)

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

    h = np.zeros((N_MEAS, N_STATE), dtype=float)
    h[0, 0:3] = phi
    h[1, 3:6] = phi
    k_az = -(v / G0)
    h[2, 0] = k_az * phi[0]
    h[2, 1] = k_az * phi[1]
    h[2, 2] = k_az * phi[2]

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

    la, lq, lde, ma, mq, mde = x_new
    z_hat = np.array(
        [
            la * phi[0] + lq * phi[1] + lde * phi[2],
            ma * phi[0] + mq * phi[1] + mde * phi[2],
            float(az0) - (v / G0) * (la * phi[0] + (lq - 1.0) * phi[1] + lde * phi[2]),
        ],
        dtype=float,
    )
    innov_post = z - z_hat
    return x_new, p_new, innov_post, innov_prior, sqrt_s, da, q
