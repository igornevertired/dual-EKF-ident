"""
Матрицы ОФК-1. Сюда не входят шаг КФ и поправки — только F, G, H, Q.

Поблочный перенос ``BINS_OFK_2ch.m`` (линеаризованная модель ошибок БИНС для ОФК).

Состояние ``X`` размерности **13** в порядке столбцов матрицы ``F`` из MATLAB (см. комментарии
внутри ``build_bins_ofk_2ch_matrices``). Измерений — **4** (φ, λ, Vn, Ve), как в ``MODELING_1.m``.
"""

from __future__ import annotations

import numpy as np

from ..common.c_ang import c_ang
from ..common.earthmodel import earthmodel


def _build_C2(psi: float, theta: float, gamma: float) -> np.ndarray:
    """Матрица ``C2`` как в строках 6–14 ``BINS_OFK_2ch.m``."""
    ct, st = np.cos(theta), np.sin(theta)
    cp, sp = np.cos(psi), np.sin(psi)
    cg, sg = np.cos(gamma), np.sin(gamma)
    return np.array(
        [
            [ct * cp, -cg * sp + sg * st * cp, sg * sp + cp * st * cg],
            [ct * sp, cg * cp + sg * st * sp, -sg * cp + cg * st * sp],
            [-st, sg * ct, cg * ct],
        ],
        dtype=float,
    )


def build_bins_ofk_2ch_matrices(
    a_body_b: np.ndarray,
    cbn: np.ndarray,
    np_bins: np.ndarray,
    dt_nav: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Вычислить ``F (13×13)``, ``G (13×6)``, ``H (4×13)``, ``Q (6×6)`` по ``BINS_OFK_2ch.m``.

    Параметры
    ----------
    a_body_b
        Ускорение в связанной СК (выход акселерометровой линии), м/с².
    cbn
        Матрица перехода (как ``C1`` в MATLAB перед ``C_ANG``).
    np_bins
        Навиг. вектор БИНС в соглашении симулятора: ``[Vn, V_h_stored, Ve, h, φ, λ]``.
        По MATLAB ``V_h = -NP1(2)`` берётся ``V_h = -np_bins[1]``.
    dt_nav
        Шаг между обновлениями ГНСС (``dt_gnss``), с — нужен только для расчёта ``Q``.
    """
    psi, theta, gamma = c_ang(np.asarray(cbn, dtype=float))
    c2 = _build_C2(float(psi), float(theta), float(gamma))

    alt = float(np_bins[3])
    fi = float(np_bins[4])
    lm = float(np_bins[5])
    vn = float(np_bins[0])
    vh_ml = -float(np_bins[1])
    ve = float(np_bins[2])

    n_vec = c2 @ np.asarray(a_body_b, dtype=float).reshape(3)
    _gg, r_meridian, r_prime_vert, _gtg = earthmodel(alt, fi, lm)
    rn_m = r_meridian
    re_m = r_prime_vert

    o33 = np.zeros((3, 3))
    o23 = np.zeros((2, 3))
    o32 = np.zeros((3, 2))
    ue = 7292115.0e-11

    wf = np.array([ue * np.cos(fi), 0.0, -ue * np.sin(fi)], dtype=float) + np.array(
        [ve / re_m, -vn / rn_m, -ve * np.tan(fi) / re_m],
        dtype=float,
    )

    wx, wy, wz = float(wf[0]), float(wf[1]), float(wf[2])
    f11 = -np.array(
        [[0.0, -wz, wy], [wz, 0.0, -wx], [-wy, wx, 0.0]],
        dtype=float,
    )
    f12 = np.array(
        [[0.0, -1.0 / re_m], [1.0 / rn_m, 0.0], [0.0, np.tan(fi) / re_m]],
        dtype=float,
    )
    f13 = np.array(
        [
            [ue * np.sin(fi), 0.0],
            [0.0, 0.0],
            [
                ue * np.cos(fi)
                + ve / (re_m * np.cos(fi) ** 2),
                0.0,
            ],
        ],
        dtype=float,
    )

    nx, ny, nz = float(n_vec[0]), float(n_vec[1]), float(n_vec[2])
    f21 = -np.array([[0.0, -nz, ny], [nz, 0.0, -nx]], dtype=float)

    f22 = np.array(
        [
            [
                vh_ml / rn_m,
                (-2.0 * ve * np.tan(fi) / re_m) - 2.0 * ue * np.sin(fi),
            ],
            [
                (ve * np.tan(fi) / re_m) + 2.0 * ue * np.sin(fi),
                (vn * np.tan(fi) + vh_ml) / re_m,
            ],
        ],
        dtype=float,
    )
    cf = np.cos(fi) ** 2
    f23 = np.array(
        [
            [
                (ve**2 / (re_m * cf)) - 2.0 * ve * ue * np.cos(fi),
                0.0,
            ],
            [
                (vn * ve / (re_m * cf))
                + 2.0 * vn * ue * np.cos(fi)
                - 2.0 * vh_ml * ue * np.sin(fi),
                0.0,
            ],
        ],
        dtype=float,
    )

    f32 = np.array([[1.0 / rn_m, 0.0], [0.0, 1.0 / (re_m * np.cos(fi))]], dtype=float)
    f33 = np.array([[0.0, 0.0], [ve * np.sin(fi) / (re_m * cf), 0.0]], dtype=float)

    c23 = c2[:2, :].copy()

    row1 = np.hstack([f11, f12, f13, o33, c2])
    row2 = np.hstack([f21, f22, f23, c23, o23])
    row3 = np.hstack([o23, f32, f33, o23, o23])
    row4 = np.hstack([o33, o32, o32, o33, o33])
    row5 = np.hstack([o33, o32, o32, o33, o33])
    f_ml = np.vstack([row1, row2, row3, row4, row5])

    g_ml = np.vstack(
        [
            np.hstack([o33, c2]),
            np.hstack([c23, o23]),
            np.hstack([o23, o23]),
            np.hstack([o33, o33]),
            np.hstack([o33, o33]),
        ]
    )
    h_ml = np.zeros((4, 13))
    h_ml[0, 5] = 1.0  # MATLAB (1,6)
    h_ml[1, 6] = 1.0  # MATLAB (2,7)
    h_ml[2, 3] = 1.0  # MATLAB (3,4)
    h_ml[3, 4] = 1.0  # MATLAB (4,5)

    wq = np.array(
        [
            20e-10,
            20e-10,
            20e-10,
            25e-7,
            25e-7,
            25e-7,
        ],
        dtype=float,
    )
    q_ml = np.diag((wq**2) / float(dt_nav))

    return f_ml, g_ml.astype(float), h_ml.astype(float), q_ml.astype(float)


def build_bins_ofk_6ch_matrices(
    a_body_b: np.ndarray,
    cbn: np.ndarray,
    np_bins: np.ndarray,
    dt_nav: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """
    Матрицы ОФК для **6** измерений ГНСС: φ, λ, Vn, Ve, Vh, h.

    Состояние **15**: первые 13 — ``BINS_OFK_2ch.m``, индексы 13–14 — ошибки
    вертикальной скорости ``np_bins[1]`` и высоты ``np_bins[3]``.
    """
    f13, g13, h4, q6 = build_bins_ofk_2ch_matrices(
        a_body_b, cbn, np_bins, dt_nav
    )

    psi, theta, gamma = c_ang(np.asarray(cbn, dtype=float))
    c2 = _build_C2(float(psi), float(theta), float(gamma))
    n_vec = c2 @ np.asarray(a_body_b, dtype=float).reshape(3)
    nx, ny, nz = float(n_vec[0]), float(n_vec[1]), float(n_vec[2])

    alt = float(np_bins[3])
    fi = float(np_bins[4])
    lm = float(np_bins[5])
    vn = float(np_bins[0])
    ve = float(np_bins[2])
    gg, rn_m, re_m, _gtg = earthmodel(alt, fi, lm)
    ue = 7292115.0e-11
    g_up = float(gg[1])

    f15 = np.zeros((15, 15), dtype=float)
    f15[:13, :13] = f13
    # Вертикаль из механизации _navigation (Vh вверх):
    # δV̇_h: ориентация, ДЛУ, кориолис/перенос от δVn,δVe,δφ, гравитация от δh.
    f15[13, 0:3] = np.array([ny, -nx, 0.0], dtype=float)
    f15[13, 3] = 2.0 * vn / re_m
    f15[13, 4] = 2.0 * ve / rn_m + 2.0 * ue * np.cos(fi)
    f15[13, 5] = -2.0 * ue * np.sin(fi) * ve
    f15[13, 7:10] = c2[2, :]
    f15[13, 14] = 2.0 * abs(g_up) / rn_m
    f15[14, 13] = 1.0
    # Обратная связь: δVh в горизонтальные ускорения (перенос).
    f15[3, 13] = -vn / re_m
    f15[4, 13] = -ve / rn_m

    g15 = np.zeros((15, 6), dtype=float)
    g15[:13, :] = g13
    g15[13, 3:6] = c2[2, :]

    h15 = np.zeros((6, 15), dtype=float)
    h15[:4, :13] = h4
    h15[4, 13] = 1.0
    h15[5, 14] = 1.0

    return f15.astype(float), g15.astype(float), h15.astype(float), q6.astype(float)
