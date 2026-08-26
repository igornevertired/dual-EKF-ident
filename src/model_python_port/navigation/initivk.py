"""
Начальные матрица ориентации и кватернион для блока БИНС (порт INITIVK.m).

Вызывается один раз при старте — ошибок датчиков на этом этапе нет.
Задаёт начальную ориентацию INS из углов модели полёта FX1.
"""

import numpy as np


def initivk(x0):
    """
    Начальная выставка БИНС (до цикла симуляции, без INS-ошибок).

    Из углов FX1 (крен x[6], курс x[7], тангаж x[8]) строятся:
      CBN0 — матрица ориентации для bins_step
      Qu   — начальный кватернион
    """
    tet0 = float(x0[8])
    gam0 = float(x0[6])
    psi0 = float(x0[7])

    cbn0 = np.array(
        [
            [np.cos(psi0) * np.cos(tet0), -np.cos(psi0) * np.sin(tet0) * np.cos(gam0) + np.sin(psi0) * np.sin(gam0), np.cos(psi0) * np.sin(tet0) * np.sin(gam0) + np.sin(psi0) * np.cos(gam0)],
            [np.sin(tet0), np.cos(tet0) * np.cos(gam0), -np.cos(tet0) * np.sin(gam0)],
            [-np.cos(tet0) * np.sin(psi0), np.cos(psi0) * np.sin(gam0) + np.sin(psi0) * np.sin(tet0) * np.cos(gam0), np.cos(psi0) * np.cos(gam0) - np.sin(psi0) * np.sin(tet0) * np.sin(gam0)],
        ],
        dtype=float,
    )

    q0 = np.cos(tet0 / 2) * np.cos(psi0 / 2) * np.cos(gam0 / 2) - np.sin(tet0 / 2) * np.sin(psi0 / 2) * np.sin(gam0 / 2)
    q1 = np.cos(tet0 / 2) * np.cos(psi0 / 2) * np.sin(gam0 / 2) + np.sin(tet0 / 2) * np.sin(psi0 / 2) * np.cos(gam0 / 2)
    q2 = np.cos(tet0 / 2) * np.sin(psi0 / 2) * np.cos(gam0 / 2) + np.sin(tet0 / 2) * np.cos(psi0 / 2) * np.sin(gam0 / 2)
    q3 = np.sin(tet0 / 2) * np.cos(psi0 / 2) * np.cos(gam0 / 2) - np.cos(tet0 / 2) * np.sin(psi0 / 2) * np.sin(gam0 / 2)
    qu = np.array([q0, q1, q2, q3], dtype=float)

    xb0 = np.zeros(15, dtype=float)
    xb0[:9] = cbn0.reshape(-1)
    xb0[9:12] = x0[:3]
    xb0[12:15] = x0[9:12]

    return {
        "XB0": xb0,
        "CBN0": cbn0,
        "Qu": qu,
        "Qu1": qu.copy(),
        "Qu2": qu.copy(),
        "Qu3": qu.copy(),
    }
