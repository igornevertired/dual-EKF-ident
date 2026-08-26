"""
Параметры ошибок датчиков и начальные ковариации ОФК (табл. 2–6 методички).

Единицы приведены к СИ для использования в симуляторе.
"""

from __future__ import annotations

import numpy as np

G0 = 9.80665
_DEG_HR = np.pi / 180.0 / 3600.0
_R_EARTH = 6378245.0

# --- Табл. 2: GPS ---
GPS_SIGMA_PSEUDORANGE_M = 6.6
GPS_SIGMA_PSEUDORANGE_RATE_MPS = 0.05
GPS_CLOCK_BIAS_PSD_M2_HZ = 0.009
GPS_CLOCK_DRIFT_PSD_MPS2_HZ = 0.0355

# --- Табл. 3: INS ---
INS_SIGMA_GYRO_BIAS_DEG_HR = 0.003
INS_SQRT_Q_GYRO_BIAS_DEG_HR_SQRT_HZ = 0.0015
INS_SIGMA_ACCEL_BIAS_G = 25.0e-6
INS_SQRT_Q_ACCEL_BIAS_G_SQRT_HZ = 50.0e-6

# --- Табл. 5: начальные СКО ошибок ОФК ---
OFK_INIT_ATTITUDE_RAD = np.array([0.0001, 0.0001, 0.002], dtype=float)
OFK_INIT_VELOCITY_MPS = np.array([0.02, 0.02, 0.02], dtype=float)
OFK_INIT_LAT_LON_RAD = np.array([1.57e-7, 1.57e-7], dtype=float)
OFK_INIT_ALTITUDE_M = 1.0


def deg_hr_to_rad_s(value: float | np.ndarray) -> float | np.ndarray:
    return np.asarray(value, dtype=float) * _DEG_HR


def g_to_mps2(value: float | np.ndarray) -> float | np.ndarray:
    return np.asarray(value, dtype=float) * G0


def ins_gyro_bias_sigma_rad_s() -> float:
    return float(deg_hr_to_rad_s(INS_SIGMA_GYRO_BIAS_DEG_HR))


def ins_accel_bias_sigma_mps2() -> float:
    return float(g_to_mps2(INS_SIGMA_ACCEL_BIAS_G))


def ins_gyro_bias_rw_variance_per_hz() -> float:
    """``Q_ω`` в (рад/с)²/Гц из ``√Q_ω`` табл. 3."""
    sqrt_q_rad_s = INS_SQRT_Q_GYRO_BIAS_DEG_HR_SQRT_HZ * _DEG_HR
    return float(sqrt_q_rad_s**2)


def ins_accel_bias_rw_variance_per_hz() -> float:
    """``Q_a`` в (м/с²)²/Гц из ``√Q_a`` табл. 3."""
    sqrt_q_mps2 = INS_SQRT_Q_ACCEL_BIAS_G_SQRT_HZ * G0
    return float(sqrt_q_mps2**2)


def gnss_measurement_sigma() -> np.ndarray:
    """
    СКО измерений ГНСС ``[Fi, Lm, H, Vn, Ve, Vh]`` из табл. 2.

    Горизонтальные координаты: ``σ_ρ / R`` (рад); высота — ``σ_ρ`` (м);
    скорости — ``σ_{ρ̇}`` (м/с).
    """
    sigma_horiz_rad = GPS_SIGMA_PSEUDORANGE_M / _R_EARTH
    return np.array(
        [
            sigma_horiz_rad,
            sigma_horiz_rad,
            GPS_SIGMA_PSEUDORANGE_M,
            GPS_SIGMA_PSEUDORANGE_RATE_MPS,
            GPS_SIGMA_PSEUDORANGE_RATE_MPS,
            GPS_SIGMA_PSEUDORANGE_RATE_MPS,
        ],
        dtype=float,
    )


def gnss_measurement_covariance(dt: float = 1e-3) -> np.ndarray:
    """
    Диагональ ``R`` для одного такта ОФК: ``diag(σ²/dt)`` как в ``MODELING_1.m``.

    ``dt`` — базовый шаг интегрирования (1 мс), не период ОФК.
    """
    sig = gnss_measurement_sigma()
    var = sig**2 / float(dt)
    var_floor = np.array([1e-14, 1e-14, 1e-2, 1e-4, 1e-4, 1e-4], dtype=float)
    return np.diag(np.maximum(var, var_floor))


def ofk_initial_covariance_diagonal() -> np.ndarray:
    """
    Диагональ ``P₀`` (15 состояний) по табл. 5–6 и порядку ``BINS_OFK_2ch`` + Vh, H.

    Индексы: 0–2 углы; 3–4 Vn, Ve; 5–6 Fi, Lm; 7–9 байасы ДУС; 10–12 байасы ДЛУ;
    13 — ошибка Vh; 14 — ошибка H.
    """
    sig_w = ins_gyro_bias_sigma_rad_s()
    sig_a = ins_accel_bias_sigma_mps2()
    return np.array(
        [
            OFK_INIT_ATTITUDE_RAD[0] ** 2,
            OFK_INIT_ATTITUDE_RAD[1] ** 2,
            OFK_INIT_ATTITUDE_RAD[2] ** 2,
            OFK_INIT_VELOCITY_MPS[0] ** 2,
            OFK_INIT_VELOCITY_MPS[1] ** 2,
            OFK_INIT_LAT_LON_RAD[0] ** 2,
            OFK_INIT_LAT_LON_RAD[1] ** 2,
            sig_w**2,
            sig_w**2,
            sig_w**2,
            sig_a**2,
            sig_a**2,
            sig_a**2,
            OFK_INIT_VELOCITY_MPS[2] ** 2,
            OFK_INIT_ALTITUDE_M**2,
        ],
        dtype=float,
    )
