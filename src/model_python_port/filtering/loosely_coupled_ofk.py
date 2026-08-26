"""
Разомкнутая связка БИНС/ГНСС: predict/update ОФК и обратная связь в ``np_bins``.
"""

from __future__ import annotations

import numpy as np

from .bins_ofk_2ch import build_bins_ofk_6ch_matrices

# Порядок z согласован с ``H`` из ``build_bins_ofk_6ch_matrices``:
# [δφ, δλ, δVn, δVe, δVh, δh]
_VAR_FLOOR = np.array([1e-14, 1e-14, 1e-4, 1e-4, 1e-4, 1e-2], dtype=float)


def build_measurement_covariance(v_gnss: np.ndarray) -> np.ndarray:
    """``R = diag(max(σ², floor))`` с перестановкой под порядок строк ``H``."""
    sig = np.asarray(v_gnss, dtype=float).reshape(6)
    var = sig**2
    ordered = np.array([var[0], var[1], var[3], var[4], var[5], var[2]], dtype=float)
    return np.diag(np.maximum(ordered, _VAR_FLOOR))


def build_innovation(np_bins: np.ndarray, np_gnss: np.ndarray) -> np.ndarray:
    return np.array(
        [
            np_bins[4] - np_gnss[0],
            np_bins[5] - np_gnss[1],
            np_bins[0] - np_gnss[3],
            np_bins[2] - np_gnss[4],
            np_bins[1] - np_gnss[5],
            np_bins[3] - np_gnss[2],
        ],
        dtype=float,
    )


def kf_predict(
    f: np.ndarray,
    g: np.ndarray,
    q: np.ndarray,
    x: np.ndarray,
    p: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    phi = np.eye(f.shape[0]) + f * dt + ((f * dt) @ (f * dt)) / 2.0
    g_rus = g * dt
    x_pred = phi @ np.asarray(x, dtype=float).reshape(-1)
    p_pred = phi @ p @ phi.T + g_rus @ q @ g_rus.T
    return x_pred, 0.5 * (p_pred + p_pred.T)


def kf_update(
    h: np.ndarray,
    r: np.ndarray,
    x_pred: np.ndarray,
    p_pred: np.ndarray,
    z: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    ph_t = p_pred @ h.T
    s = h @ ph_t + r
    s = 0.5 * (s + s.T)
    k = np.linalg.solve(s, ph_t.T).T
    innovation = np.asarray(z, dtype=float).reshape(-1) - h @ x_pred
    x = x_pred + k @ innovation
    ik = np.eye(x_pred.shape[0]) - k @ h
    p = ik @ p_pred @ ik.T + k @ r @ k.T
    return x, 0.5 * (p + p.T)


def ofk_matrices(
    a_body: np.ndarray,
    cbn: np.ndarray,
    np_bins: np.ndarray,
    dt_gnss: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    return build_bins_ofk_6ch_matrices(a_body, cbn, np_bins, dt_gnss)


def ofk_step(
    a_body: np.ndarray,
    cbn: np.ndarray,
    np_bins: np.ndarray,
    z: np.ndarray,
    x: np.ndarray,
    p: np.ndarray,
    v_gnss: np.ndarray,
    dt_gnss: float,
) -> tuple[np.ndarray, np.ndarray]:
    f, g, h, q = ofk_matrices(a_body, cbn, np_bins, dt_gnss)
    r = build_measurement_covariance(v_gnss)
    x_pred, p_pred = kf_predict(f, g, q, x, p, dt_gnss)
    return kf_update(h, r, x_pred, p_pred, z)


def apply_bins_feedback(np_bins: np.ndarray, x_corr: np.ndarray) -> None:
    np_bins[0] -= x_corr[3]
    np_bins[2] -= x_corr[4]
    np_bins[4] -= x_corr[5]
    np_bins[5] -= x_corr[6]
    np_bins[1] -= x_corr[13]
    np_bins[3] -= x_corr[14]
