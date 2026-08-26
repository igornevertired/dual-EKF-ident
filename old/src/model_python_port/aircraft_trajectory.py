"""
Интеграция только модели полёта FX1 (без БИНС/ГНСС/ОФК) для построения траектории.

Полный прогон TMODEL = 1000 с соответствует исходному INITSIM.m / OUT_X.txt
и даёт график «широта от долготы» как в дипломе (Рис. 10).
"""

from __future__ import annotations

import numpy as np

from .autopilot_model import autopilot
from .core import rk4_step
from .fx1 import fx1 as fx1_func
from .initsim import initsim


def run_fx1_trajectory(tmodel: float = 1000.0, dt: float = 1e-3, log_dt: float = 1.0):
    """
    Прогон FX1 + RK4 + автопилот; логирование истинных φ, λ на шаге ``log_dt``.

    Возвращает словарь с ключами ``time``, ``true_fi``, ``true_lam``, ``true_h``.
    """
    sim = initsim()
    la = sim["la"]
    htr, vtr, tettr = sim["htr"], sim["vtr"], sim["tettr"]

    x = sim["x0"].copy()
    u = sim["u0"].copy()

    n_steps = int(tmodel / dt)
    log_stride = max(1, int(round(log_dt / dt)))
    n_log = n_steps // log_stride + 1

    log = {
        "time": np.zeros(n_log, dtype=float),
        "true_fi": np.zeros(n_log, dtype=float),
        "true_lam": np.zeros(n_log, dtype=float),
        "true_h": np.zeros(n_log, dtype=float),
    }

    ap_count = 0
    ap_steps = int(0.01 / dt)
    log_idx = 0
    fx1 = lambda x, u, t: fx1_func(x, u, t, la)

    for i in range(n_steps):
        t = (i + 1) * dt
        result = rk4_step(fx1, t - dt, dt, x, u)
        x = result[0]

        ap_count += 1
        if ap_count >= ap_steps:
            ap_count = 0
            u = autopilot(x, result[1], t, sim["u0"], htr, vtr, tettr)

        if (i + 1) % log_stride == 0:
            log["time"][log_idx] = t
            log["true_fi"][log_idx] = x[12]
            log["true_lam"][log_idx] = x[13]
            log["true_h"][log_idx] = x[10]
            log_idx += 1

        if i % 200000 == 0 and i > 0:
            print(f"t={t:.1f}s  H={x[10]:.1f}m  fi={x[12]:.4e}  lam={x[13]:.4e}")

    for key in log:
        log[key] = log[key][:log_idx]
    return log
