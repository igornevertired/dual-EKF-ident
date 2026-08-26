"""
Порт ``BINS1.m``: один канал БИНС (ДУС + ДЛУ → навигация + ориентация).

Структура как в MATLAB:
``bins1`` → ``_dus`` / ``_dlu`` → ``_navigation`` / ``_orientation``.
"""

from __future__ import annotations

import numpy as np

from .earthmodel import earthmodel
from .sensor_error_params import (
    ins_accel_bias_rw_variance_per_hz,
    ins_accel_bias_sigma_mps2,
    ins_gyro_bias_rw_variance_per_hz,
    ins_gyro_bias_sigma_rad_s,
)


class Bins1Sensors:
    """ДУС/ДЛУ с ошибками по табл. 3 (bias + random walk)."""

    def __init__(self, seed: int = 42):
        rng = np.random.default_rng(seed)
        sig_w = ins_gyro_bias_sigma_rad_s()
        sig_a = ins_accel_bias_sigma_mps2()
        self.dw = rng.normal(0.0, sig_w, 3)
        self.da = rng.normal(0.0, sig_a, 3)
        self.rng = np.random.default_rng(seed + 1)
        self._q_w = ins_gyro_bias_rw_variance_per_hz()
        self._q_a = ins_accel_bias_rw_variance_per_hz()

    def propagate(self, dt: float) -> None:
        """Случайное блуждание смещений нуля между шагами интегрирования."""
        self.dw += np.sqrt(self._q_w * dt) * self.rng.standard_normal(3)
        self.da += np.sqrt(self._q_a * dt) * self.rng.standard_normal(3)

    def dus(self, w: np.ndarray) -> np.ndarray:
        return np.asarray(w, dtype=float) + self.dw

    def dlu(self, a: np.ndarray) -> np.ndarray:
        return np.asarray(a, dtype=float) + self.da


def _quat_to_cbn(q: np.ndarray) -> np.ndarray:
    q0, q1, q2, q3 = q
    cnb = np.array(
        [
            [1 - 2 * (q2 * q2 + q3 * q3), 2 * q1 * q2 + 2 * q3 * q0, 2 * q1 * q3 - 2 * q2 * q0],
            [2 * q1 * q2 - 2 * q3 * q0, 1 - 2 * (q1 * q1 + q3 * q3), 2 * q2 * q3 + 2 * q1 * q0],
            [2 * q1 * q3 + 2 * q2 * q0, 2 * q2 * q3 - 2 * q1 * q0, 1 - 2 * (q1 * q1 + q2 * q2)],
        ],
        dtype=float,
    )
    return cnb.T


def _navigation(a_dlu: np.ndarray, cbn: np.ndarray, np_prev: np.ndarray, dt: float, h_et: float, dh_et: float) -> np.ndarray:
    ue = 7292115.0e-11
    vbe_n = np.array([np_prev[0], np_prev[1], np_prev[2]], dtype=float)
    fi = float(np_prev[4])
    lm = float(np_prev[5])
    h = float(h_et)

    wei_n = np.array([ue * np.cos(fi), ue * np.sin(fi), 0.0], dtype=float)
    gg, r1, r2, _gtg = earthmodel(h, fi, lm)
    a_earth = 6378245.0
    b_earth = 6356856.0
    e2 = (a_earth**2 - b_earth**2) / a_earth**2
    rn = np.array([-r1 * e2 * np.sin(fi) * np.cos(fi), r1 * (1 - e2 * (np.sin(fi) ** 2)), 0.0], dtype=float)
    ap_n = -np.cross(wei_n, np.cross(wei_n, rn))
    ak_n = -2.0 * np.cross(wei_n, vbe_n)
    wge_n = np.array([vbe_n[2] / r1, vbe_n[2] * np.tan(fi) / r1, -vbe_n[0] / r2], dtype=float)
    at_n = -np.cross(wge_n, vbe_n)
    a_nav = cbn @ np.asarray(a_dlu, dtype=float)
    dvbe_n = a_nav + ap_n + ak_n + at_n + gg
    dnp = np.array([dvbe_n[0], dvbe_n[1], dvbe_n[2], vbe_n[1], vbe_n[0] / r2, vbe_n[2] / (r1 * np.cos(fi))], dtype=float)
    np_new = np_prev + dnp * dt
    np_new[3] = h_et
    np_new[1] = dh_et
    return np_new


def _orientation(w_dus: np.ndarray, q_prev: np.ndarray, cbn_prev: np.ndarray, np_prev: np.ndarray, dt: float, h_et: float, dh_et: float) -> tuple[np.ndarray, np.ndarray]:
    ue = 7292115.0e-11
    vbe_n = np.array([np_prev[0], dh_et, np_prev[2]], dtype=float)
    fi = float(np_prev[4])
    lm = float(np_prev[5])
    h = float(h_et)

    wei_n = np.array([ue * np.cos(fi), ue * np.sin(fi), 0.0], dtype=float)
    _gg, r1, r2, _gtg = earthmodel(h, fi, lm)
    wne_n = np.array([vbe_n[2] / r1, vbe_n[2] * np.tan(fi) / r1, -vbe_n[0] / r2], dtype=float)
    wni_n = wne_n + wei_n
    wni_b = cbn_prev.T @ wni_n
    wbnb = np.asarray(w_dus, dtype=float) - wni_b

    q = np.asarray(q_prev, dtype=float)
    qqq = float(np.dot(q, q))
    dq0 = 0.5 * (-q[1] * wbnb[0] - q[2] * wbnb[1] - q[3] * wbnb[2] + q[0] * (1 - qqq))
    dq1 = 0.5 * (q[0] * wbnb[0] - q[3] * wbnb[1] + q[2] * wbnb[2] + q[1] * (1 - qqq))
    dq2 = 0.5 * (q[3] * wbnb[0] + q[0] * wbnb[1] - q[1] * wbnb[2] + q[2] * (1 - qqq))
    dq3 = 0.5 * (-q[2] * wbnb[0] + q[1] * wbnb[1] + q[0] * wbnb[2] + q[3] * (1 - qqq))
    q_new = q + np.array([dq0, dq1, dq2, dq3], dtype=float) * dt
    cbn_new = _quat_to_cbn(q_new)
    return cbn_new, q_new


def bins1(
    a: np.ndarray,
    w: np.ndarray,
    np_prev: np.ndarray,
    cbn_prev: np.ndarray,
    q_prev: np.ndarray,
    dt: float,
    h_et: float,
    dh_et: float,
    sensors: Bins1Sensors,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Один шаг БИНС 1 (``BINS1.m``).

    ``np_prev`` — ``[Vn, Vh, Ve, H, Fi, Lm]``.
    Возвращает ``(Q_new, Cbn_new, NP_new, A_dlu)``.
    """
    sensors.propagate(dt)
    w_dus = sensors.dus(w)
    a_dlu = sensors.dlu(a)
    np_new = _navigation(a_dlu, cbn_prev, np_prev, dt, h_et, dh_et)
    cbn_new, q_new = _orientation(w_dus, q_prev, cbn_prev, np_prev, dt, h_et, dh_et)
    return q_new, cbn_new, np_new, a_dlu
