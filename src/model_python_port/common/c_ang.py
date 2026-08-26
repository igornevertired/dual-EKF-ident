"""
Извлечение углов ориентации из матрицы направляющих косинусов (порт C_ANG.m).
"""

import numpy as np

_SQ2 = np.sqrt(2.0) / 2.0


def c_ang(C):
    """
    Вычисляет углы курса, тангажа и крена по матрице перехода между осями (DCM).

    Реализация повторяет ветвления MATLAB C_ANG.m при |C(2,1)| и |C(3,2)|,
    близких к sin(45°), чтобы избежать неустойчивости арктангенса.

    Параметры
    ---------
    C : ndarray, shape (3, 3)
        Матрица направляющих косинусов.

    Возвращает
    ----------
    ndarray, shape (3,)
        Углы ``[Psi, Theta, Gamma]`` в радианах в том же порядке, что в MATLAB.

    Исключения
    ----------
    ValueError
        Если ``C`` не матрица 3×3.
    """
    C = np.asarray(C, dtype=float)
    if C.shape != (3, 3):
        raise ValueError("Ожидается матрица направляющих косинусов 3×3")

    if abs(C[1, 0]) > _SQ2:
        psi = np.arctan(-C[0, 0] / C[1, 0])
    else:
        psi = np.pi / 2.0 - np.arctan(-C[1, 0] / C[0, 0])

    theta = np.arcsin(C[2, 0])

    if abs(C[2, 1]) > _SQ2:
        gamma = np.arctan(-C[2, 2] / C[2, 1])
    else:
        gamma = np.pi / 2.0 - np.arctan(-C[2, 1] / C[2, 2])

    return np.array([psi, theta, gamma], dtype=float)
