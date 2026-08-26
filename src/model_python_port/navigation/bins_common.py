"""
Механизация БИНС: один шаг интегрирования ИНС (``bins_step``).

Вход — уже зашумлённые показания датчиков (w_m, a_m из InsErrorGen).
Выход — навигационное решение np_bins и ориентация (q, Cbn).

np_bins = [Vn, Vh, Ve, h, φ, λ]  (индексы 0..5)
"""

from __future__ import annotations

import numpy as np

from ..common.earthmodel import earthmodel


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


def _navigation(
    a: np.ndarray, cbn: np.ndarray, np_prev: np.ndarray, dt: float
) -> np.ndarray:
    """
    Навигационный канал: интегрирование скорости и координат по ДЛУ (a_m).

    Прибор: акселерометр (ДЛУ) → a_nav = Cbn @ a_m → ускорение в NED/географической СК.
    Ошибки ДЛУ (bias + шум) уже внутри ``a``.

    Учитываются: g, вращение Земли, переносная и кориолисова составляющие.
    """
    ue = 7292115.0e-11
    vbe_n = np.array([np_prev[0], np_prev[1], np_prev[2]], dtype=float)
    fi = float(np_prev[4])
    lm = float(np_prev[5])
    h = float(np_prev[3])

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
    # ← здесь используется зашумлённое ускорение с ДЛУ
    a_nav = cbn @ np.asarray(a, dtype=float)
    dvbe_n = a_nav + ap_n + ak_n + at_n + gg
    dnp = np.array([dvbe_n[0], dvbe_n[1], dvbe_n[2], vbe_n[1], vbe_n[0] / r2, vbe_n[2] / (r1 * np.cos(fi))], dtype=float)
    return np_prev + dnp * dt


def _orientation(
    w: np.ndarray,
    q_prev: np.ndarray,
    cbn_prev: np.ndarray,
    np_prev: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Ориентационный канал: интегрирование кватерниона по ДУС (w_m).

    Прибор: гироскоп (ДУС) → ω_bnb = w_m − ω_ni (перенос NED в body).
    Ошибки ДУС (bias + шум) уже внутри ``w``.
    """
    ue = 7292115.0e-11
    vbe_n = np.array([np_prev[0], np_prev[1], np_prev[2]], dtype=float)
    fi = float(np_prev[4])
    lm = float(np_prev[5])
    h = float(np_prev[3])

    wei_n = np.array([ue * np.cos(fi), ue * np.sin(fi), 0.0], dtype=float)
    _gg, r1, r2, _gtg = earthmodel(h, fi, lm)
    wne_n = np.array([vbe_n[2] / r1, vbe_n[2] * np.tan(fi) / r1, -vbe_n[0] / r2], dtype=float)
    wni_n = wne_n + wei_n
    wni_b = cbn_prev.T @ wni_n
    # ← здесь используется зашумлённая угловая скорость с ДУС
    wbnb = np.asarray(w, dtype=float) - wni_b

    q = np.asarray(q_prev, dtype=float)
    qqq = float(np.dot(q, q))
    dq0 = 0.5 * (-q[1] * wbnb[0] - q[2] * wbnb[1] - q[3] * wbnb[2] + q[0] * (1 - qqq))
    dq1 = 0.5 * (q[0] * wbnb[0] - q[3] * wbnb[1] + q[2] * wbnb[2] + q[1] * (1 - qqq))
    dq2 = 0.5 * (q[3] * wbnb[0] + q[0] * wbnb[1] - q[1] * wbnb[2] + q[2] * (1 - qqq))
    dq3 = 0.5 * (-q[2] * wbnb[0] + q[1] * wbnb[1] + q[0] * wbnb[2] + q[3] * (1 - qqq))
    q_new = q + np.array([dq0, dq1, dq2, dq3], dtype=float) * dt
    cbn_new = _quat_to_cbn(q_new)
    return cbn_new, q_new


def bins_step(
    a: np.ndarray,
    w: np.ndarray,
    np_prev: np.ndarray,
    cbn_prev: np.ndarray,
    q_prev: np.ndarray,
    dt: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Один шаг механизации БИНС (аналог BINS1.m / Navigation + Orientation).

    Порядок внутри шага:
      1. _navigation(a_m)  — ДЛУ → Vn, Vh, Ve, h, φ, λ
      2. _orientation(w_m) — ДУС → q, Cbn

    Параметры
    ---------
    a, w     : зашумлённые показания ДЛУ и ДУС (после InsErrorGen)
    Возвращает
    ----------
    q_new, cbn_new, np_new, a — a пробрасывается в ОФК для матриц F,G,H
    """
    np_new = _navigation(a, cbn_prev, np_prev, dt)
    cbn_new, q_new = _orientation(w, q_prev, cbn_prev, np_prev, dt)
    return q_new, cbn_new, np_new, np.asarray(a, dtype=float)


bins = bins_step
