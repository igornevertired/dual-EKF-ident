"""
ОФК-1: error-state КФ БИНС/ГНСС, 15 состояний, 10 Гц.

Вход шага: a_m (ДЛУ), Cbn, NP БИНС, z = БИНС−ГНСС, σ ГНСС.
Выход шага: x̂, P. В механизацию БИНС не пишется.

Состояние x (0-based)::

    0–2   углы платформы δϑ
    3, 4  δVn, δVe
    5, 6  δφ, δλ
    7–9   смещение ДЛУ Δa
    10–12 смещение ДУС Δω
    13    δVh
    14    δh

Поправки потребителю (ОФК-2): ``consumer_outputs`` = NP−δV/δr и ω−Δω̂.
"""

from __future__ import annotations

import numpy as np

from .bins_ofk_2ch import build_bins_ofk_6ch_matrices

N_STATE = 15

# Порядок z согласован с ``H`` из ``build_bins_ofk_6ch_matrices``:
# [δφ, δλ, δVn, δVe, δVh, δh]
_VAR_FLOOR = np.array([1e-14, 1e-14, 1e-4, 1e-4, 1e-4, 1e-2], dtype=float)

# P₀: σ² из табл. 5; смещения — σ из табл. 3. Без часов приёмника.
_DEG_HR = np.pi / 180.0 / 3600.0
_SIG_ATT = (1.0e-5, 1.0e-5, 2.0e-5)  # рад
_SIG_V = 0.02  # м/с
_SIG_LL = 1.57e-7  # рад
_SIG_H = 1.0  # м
_SIG_GYRO = 0.003 * _DEG_HR  # 0.003 °/ч
_SIG_ACCEL = 25.0e-6 * 9.80665  # 25 µg


def initial_state() -> np.ndarray:
    return np.zeros(N_STATE, dtype=float)


def initial_covariance() -> np.ndarray:
    sig2 = np.array(
        [
            _SIG_ATT[0] ** 2,
            _SIG_ATT[1] ** 2,
            _SIG_ATT[2] ** 2,
            _SIG_V ** 2,
            _SIG_V ** 2,
            _SIG_LL ** 2,
            _SIG_LL ** 2,
            _SIG_ACCEL ** 2,
            _SIG_ACCEL ** 2,
            _SIG_ACCEL ** 2,
            _SIG_GYRO ** 2,
            _SIG_GYRO ** 2,
            _SIG_GYRO ** 2,
            _SIG_V ** 2,
            _SIG_H ** 2,
        ],
        dtype=float,
    )
    return np.diag(sig2)


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
    """Один такт ОФК-1: predict + update. Возвращает (x̂, P)."""
    f, g, h, q = ofk_matrices(a_body, cbn, np_bins, dt_gnss)
    r = build_measurement_covariance(v_gnss)
    x_pred, p_pred = kf_predict(f, g, q, x, p, dt_gnss)
    return kf_update(h, r, x_pred, p_pred, z)


def correct_nav_output(np_bins: np.ndarray, x_corr: np.ndarray) -> np.ndarray:
    """NP для потребителей: счисление БИНС минус δV, δφ, δλ, δh ОФК-1."""
    x = np.asarray(x_corr, dtype=float).reshape(-1)
    out = np.asarray(np_bins, dtype=float).reshape(-1).copy()
    out[0] -= x[3]
    out[2] -= x[4]
    out[4] -= x[5]
    out[5] -= x[6]
    out[1] -= x[13]
    out[3] -= x[14]
    return out


def correct_gyro_output(w_m: np.ndarray, x_corr: np.ndarray) -> np.ndarray:
    """ω для потребителей: ДУС минус оценка смещения ОФК-1. В БИНС не идёт."""
    return np.asarray(w_m, dtype=float).reshape(3) - np.asarray(
        x_corr[10:13], dtype=float
    )


def consumer_outputs(
    np_bins: np.ndarray,
    w_m: np.ndarray,
    x_ofk: np.ndarray,
    *,
    feedback: bool,
) -> tuple[np.ndarray, np.ndarray]:
    """NP и ω, которые видит ОФК-2. БИНС не меняется."""
    if feedback:
        return correct_nav_output(np_bins, x_ofk), correct_gyro_output(w_m, x_ofk)
    return np.asarray(np_bins, dtype=float).copy(), np.asarray(w_m, dtype=float).reshape(3)
