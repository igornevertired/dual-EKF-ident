"""
Порт ``OFK.m``: один шаг оптimalного фильтра Калмана для разомкнутой связки БИНС/ГНСС.
"""

from __future__ import annotations

import numpy as np


def ofk(
    F: np.ndarray,
    G: np.ndarray,
    H: np.ndarray,
    Q: np.ndarray,
    R: np.ndarray,
    Z: np.ndarray,
    x_est_prev: np.ndarray,
    P_est_prev: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Predict + update: ``Φ = I + FΔt + (FΔt)²/2`` — как в ``OFK.m``."""
    f_rus = np.eye(F.shape[0]) + F * dt + ((F * dt) @ (F * dt)) / 2.0
    g_rus = G * dt

    p_pred = f_rus @ P_est_prev @ f_rus.T + g_rus @ Q @ g_rus.T
    x_pred = f_rus @ np.asarray(x_est_prev, dtype=float).reshape(-1)

    ph_t = p_pred @ H.T
    s = H @ ph_t + R
    k = np.linalg.solve(s, ph_t.T).T

    innovation = np.asarray(Z, dtype=float).reshape(-1) - H @ x_pred
    x_est = x_pred + k @ innovation
    p_est = (np.eye(F.shape[0]) - k @ H) @ p_pred
    return x_est, p_est
