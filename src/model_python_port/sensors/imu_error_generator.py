"""
Ошибки ДУС/ДЛУ перед механизацией БИНС (порт ``GENERATOR_SV.m``).

Моделирует два прибора блока INS:
  • ДУС (гироскоп)  — искажает угловую скорость ω
  • ДЛУ (акселерометр) — искажает ускорение a

Ошибки добавляются ПОСЛЕ FX1 и ДО bins_step.
"""

from __future__ import annotations

import numpy as np

_DEG_HR = np.pi / 180.0 / 3600.0


class InsErrorGen:
    """
    Генератор ошибок инерциальных датчиков.

    Моменты генерации ошибок:
    ─────────────────────────────────────────────────────────
    | Когда              | Что генерируется              |
    |--------------------|-------------------------------|
    | __init__ (1 раз)   | bias ДУС: N(0, 0.5 °/ч) × 3  |
    |                    | bias ДЛУ: N(0, 5e-4 м/с²)×3  |
    | generate (каждый   | белый шум ДУС: σ = 1e-5       |
    |   шаг dt)          | белый шум ДЛУ: σ = 5e-5 м/с²  |
    ─────────────────────────────────────────────────────────
    """

    def __init__(self, seed: int = 42):
        rng = np.random.default_rng(seed)
        # Смещение нуля (bias) — постоянное на весь прогон, задаётся один раз
        self.dw_bias = rng.normal(0.0, 0.5 * _DEG_HR, 3)  # ДУС, рад/с
        self.da_bias = rng.normal(0.0, 5.0e-4, 3)          # ДЛУ, м/с²
        self.rng = np.random.default_rng(seed + 1)
        self.dw_noise_std = 1.0e-5   # СКО белого шума ДУС на шаг
        self.da_noise_std = 5.0e-5   # СКО белого шума ДЛУ на шаг

    def generate(self, w: np.ndarray, a: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Исказить «идеальные» показания FX1 → «сырые» показания датчиков.

        Параметры
        ---------
        w : истинная ω от FX1 (wbi_b), рад/с, связанная СК
        a : истинное a без g от FX1 (af_bi_b), м/с², связанная СК

        Возвращает
        ----------
        w_m : показание ДУС  = ω + bias_ω + шум_ω
        a_m : показание ДЛУ  = a  + bias_a + шум_a
        """
        w_m = (
            np.asarray(w, dtype=float)
            + self.dw_bias
            + self.rng.normal(0.0, self.dw_noise_std, 3)
        )
        a_m = (
            np.asarray(a, dtype=float)
            + self.da_bias
            + self.rng.normal(0.0, self.da_noise_std, 3)
        )
        return w_m, a_m
