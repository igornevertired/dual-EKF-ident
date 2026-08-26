"""
Базовые численные и измерительные примитивы порта MATLAB-модели.

Содержит шаг Рунге–Кутты 4-го порядка, модель ГНСС и обёртку над моделью Земли.
"""

import numpy as np

from ..common.c_ang import c_ang
from ..common.earthmodel import earthmodel

__all__ = [
    "rk4_step",
    "earth_model",
    "c_ang",
    "gnss",
]


def rk4_step(fx1, time, dt, x, u):
    """
    Один шаг интегрирования методом Рунге–Кутты 4-го порядка (аналог RK4.m).

    Интегрирует систему ``dx/dt = f(x, u, t)``. Правая часть ``fx1`` может возвращать
    либо только вектор производных ``xd``, либо кортеж ``(xd, ...)``; в кортеже
    первая компонента — производная состояния, остальное пробрасывается в ответ
    без изменения (как в FX1: ускорения и угловая скорость для БИНС).

    Параметры
    ---------
    fx1 : callable
        ``f(x, u, t)`` — правая часть ОДУ.
    time : float
        Начальный момент шага.
    dt : float
        Длина шага по времени.
    x : ndarray
        Вектор состояния.
    u : ndarray или None
        Вектор управления (передаётся в ``fx1`` как есть).

    Возвращает
    ----------
    tuple
        ``(x_new, xd_last, *extras)`` — новое состояние, производная на конце шага
        и необязательные дополнительные массивы из последнего вызова ``fx1``.
    """
    out = fx1(x, u, time)
    xd = out[0] if isinstance(out, tuple) else out
    xa = xd * dt
    x_mid = x + 0.5 * xa
    t_mid = time + 0.5 * dt

    out = fx1(x_mid, u, t_mid)
    xd = out[0] if isinstance(out, tuple) else out
    q = xd * dt
    x_mid = x + 0.5 * q
    xa = xa + 2.0 * q

    out = fx1(x_mid, u, t_mid)
    xd = out[0] if isinstance(out, tuple) else out
    q = xd * dt
    x_end = x + q
    xa = xa + 2.0 * q

    t_end = time + dt
    result = fx1(x_end, u, t_end)
    if isinstance(result, tuple):
        xd = result[0]
        extras = result[1:]
    else:
        xd = result
        extras = tuple()

    xnew = x + (xa + xd * dt) / 6.0
    return (xnew, xd, *extras)


def earth_model(fi, h):
    """
    Упрощённый доступ к радиусам и силе тяжести через полную модель :func:`earthmodel.earthmodel`.

    Вызывает ``earthmodel(h, fi, 0)`` и возвращает словарь с полями ``RN``, ``RM`` (радиусы
    ``R1``, ``R2`` из EARTHMODEL.m) и скаляром ``G`` — нормой вектора истинной гравитации
    ``Gg`` для совместимости со старым кодом, где требовался один скаляр ускорения.

    Параметры
    ---------
    fi : float
        Широта, рад.
    h : float
        Высота, м.
    """
    gg, r1, r2, _gtg = earthmodel(float(h), float(fi), 0.0)
    g = float(np.linalg.norm(gg))
    return {"RN": r1, "RM": r2, "G": g}


def gnss(
    fi: float,
    lm: float,
    h: float,
    vn: float,
    ve: float,
    vh: float,
    sigma_fi: float = 5.0e-6,
    sigma_lm: float = 5.0e-6,
    sigma_h: float = 1.0,
    sigma_vn: float = 0.2,
    sigma_ve: float = 0.2,
    sigma_vh: float = 0.2,
    rng=None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Зашумлённые измерения ГНСС ``[Fi, Lm, H, Vn, Ve, Vh]``.

    Возвращает ``(np_gnss, v_gnss)`` — вектор измерений и СКО по каналам.
    """
    rng = rng or np.random.default_rng()
    sig = np.array(
        [sigma_fi, sigma_lm, sigma_h, sigma_vn, sigma_ve, sigma_vh],
        dtype=float,
    )
    truth = np.array([fi, lm, h, vn, ve, vh], dtype=float)
    np_gnss = truth + sig * rng.standard_normal(6)
    return np_gnss, sig.copy()
