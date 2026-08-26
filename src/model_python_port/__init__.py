"""
Пакет симуляции БИНС/ГНСС/ОФК.

Один БИНС — ``bins_common.bins_step``; сценарий — ``bins_gnss_simulation.run_simulation``.
MATLAB-порт (``bins1``, ``modeling_1``) сохранён для совместимости.
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
