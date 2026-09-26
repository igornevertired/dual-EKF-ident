"""
Пакет симуляции. Цепочка: FX1 → ДУС/ДЛУ → БИНС → ГНСС/ОФК-1 → ОФК-2.

Кто что считает
---------------
dynamics/fx1.py                      истина ЛА
dynamics/autopilot_model.py          автопилот / руль
sensors/imu_error_generator.py       сырые ДУС, ДЛУ
sensors/core.py                      ГНСС, RK4
navigation/bins_common.py            БИНС: bins_step(a_m, w_m)
filtering/loosely_coupled_ofk.py     ОФК-1 (шаг КФ)
filtering/bins_ofk_2ch.py            ОФК-1: F, G, H, Q
filtering/ofk2_ekf.py                ОФК-2 (шаг EKF)
filtering/ofk2_theory.py             ОФК-2: эталонные L*, M*, X*
simulation/bins_gnss_simulation.py   цикл 1 мс, этапы 0–5
simulation/initsim.py                старт ЛА / БИНС
output/full_sim_outputs.py           таблицы и графики

Точка входа репозитория: ``run_full_sim.py``.
"""

from .navigation.bins_common import bins, bins_step
from .simulation.bins_gnss_simulation import run_simulation
from .filtering.bins_ofk_2ch import build_bins_ofk_2ch_matrices, build_bins_ofk_6ch_matrices
from .sensors.core import c_ang, earth_model, gnss, rk4_step
from .sensors.imu_error_generator import InsErrorGen
from .simulation.initsim import initsim
from .filtering.loosely_coupled_ofk import ofk_step

__all__ = [
    "bins",
    "bins_step",
    "build_bins_ofk_2ch_matrices",
    "build_bins_ofk_6ch_matrices",
    "gnss",
    "InsErrorGen",
    "initsim",
    "ofk_step",
    "run_simulation",
    "rk4_step",
    "earth_model",
    "c_ang",
]
