"""
Модель ГНСС: полный PVT — 6 каналов ``[Fi, Lm, H, Vn, Ve, Vh]``.

СКО измерений — табл. 2 (``σ_ρ = 6.6`` м, ``σ_{ρ̇} = 0.05`` м/с).
"""

from __future__ import annotations

import numpy as np

from .sensor_error_params import gnss_measurement_sigma


def gnss_1(
    fi: float,
    lm: float,
    h: float,
    vn: float,
    ve: float,
    vh: float,
    sigma: np.ndarray | None = None,
    rng=None,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Зашумлённые измерения ГНСС: ``[Fi, Lm, H, Vn, Ve, Vh]``.

    Возвращает ``(np_gnss, v_gnss)`` — вектор измерений и использованные СКО.
    """
    rng = rng or np.random.default_rng()
    sig = np.asarray(sigma if sigma is not None else gnss_measurement_sigma(), dtype=float).reshape(6)

    np_gnss = np.array(
        [
            fi + sig[0] * rng.standard_normal(),
            lm + sig[1] * rng.standard_normal(),
            h + sig[2] * rng.standard_normal(),
            vn + sig[3] * rng.standard_normal(),
            ve + sig[4] * rng.standard_normal(),
            vh + sig[5] * rng.standard_normal(),
        ],
        dtype=float,
    )
    return np_gnss, sig.copy()
