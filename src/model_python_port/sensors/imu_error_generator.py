"""
Ошибки ДУС/ДЛУ перед механизацией БИНС.

Порт DUS/DLU из BINS1.m + инициализация масштаба/перекоса из INITIVK.m:

    ω_m = (I + K_ω) Φ_ω ω + b_ω + n_ω
    a_m = (I + K_a) Φ_a a + b_a + n_a

K — диагональ погрешностей масштабных коэффициентов,
Φ — матрица неортогональности осей (как fiw_1 / fia_1).
Bias ДУС/ДЛУ — табл. 3: 0.003 °/ч и 25 µg. Белый шум — как в контуре.
"""

from __future__ import annotations

import numpy as np

_DEG_HR = np.pi / 180.0 / 3600.0

# INITIVK.m, БИНС 1
_SIGKMW = 1.0e-13
_SIGKMA = 1.0e-7
_SIGFIW = 0.001 * np.pi / 180.0 / 3600.0
_SIGFIA = 0.001 * np.pi / 180.0 / 3600.0


def _signed_sigma(rng: np.random.Generator, sigma: float) -> float:
    return float(sigma) * (1.0 if rng.random() < 0.5 else -1.0)


def _diag_scale(rng: np.random.Generator, sigma: float) -> np.ndarray:
    return np.diag([_signed_sigma(rng, sigma) for _ in range(3)])


def _misalignment(rng: np.random.Generator, sigma: float) -> np.ndarray:
    """Матрица fiw/fia из INITIVK.m."""
    fixy = _signed_sigma(rng, sigma)
    fixz = _signed_sigma(rng, sigma)
    fiyx = _signed_sigma(rng, sigma)
    fiyz = _signed_sigma(rng, sigma)
    fizx = _signed_sigma(rng, sigma)
    fizy = _signed_sigma(rng, sigma)
    return np.array(
        [
            [np.sqrt(max(0.0, 1.0 - fixy**2 - fixz**2)), fixy, fixz],
            [fiyx, np.sqrt(max(0.0, 1.0 - fiyx**2 - fiyz**2)), fiyz],
            [fizx, fizy, np.sqrt(max(0.0, 1.0 - fizx**2 - fizy**2))],
        ],
        dtype=float,
    )


class InsErrorGen:
    """
    Генератор ошибок инерциальных датчиков.

    | Когда            | Что |
    |------------------|-----|
    | __init__ (1 раз) | bias ДУС/ДЛУ, K_ω, Φ_ω, K_a, Φ_a |
    | generate (dt)    | белый шум ДУС/ДЛУ |
    """

    def __init__(self, seed: int = 42):
        rng = np.random.default_rng(seed)
        self.dw_bias = rng.normal(0.0, 0.003 * _DEG_HR, 3)  # табл. 3
        self.da_bias = rng.normal(0.0, 25.0e-6 * 9.80665, 3)  # 25 µg
        self.kmw = _diag_scale(rng, _SIGKMW)
        self.kma = _diag_scale(rng, _SIGKMA)
        self.fiw = _misalignment(rng, _SIGFIW)
        self.fia = _misalignment(rng, _SIGFIA)
        self.rng = np.random.default_rng(seed + 1)
        self.dw_noise_std = 1.0e-5
        self.da_noise_std = 5.0e-5

    def generate(self, w: np.ndarray, a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        w = np.asarray(w, dtype=float)
        a = np.asarray(a, dtype=float)
        w_p = self.fiw @ w
        a_p = self.fia @ a
        w_m = (np.eye(3) + self.kmw) @ w_p + self.dw_bias + self.rng.normal(
            0.0, self.dw_noise_std, 3
        )
        a_m = (np.eye(3) + self.kma) @ a_p + self.da_bias + self.rng.normal(
            0.0, self.da_noise_std, 3
        )
        return w_m, a_m
