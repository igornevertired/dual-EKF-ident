"""
Моделирование контура: ЛА + БИНС + СНС + ОФК-1 + ОФК-2.

Запуск из корня репозитория::

    python run_full_sim.py

Сценарий задаётся константами ниже. Манёвр описывается объектом ``Maneuver``
(см. src/model_python_port/dynamics/maneuvers.py), например::

    Maneuver("doublet", amp_deg=5, pulse_s=2.5)                 # дублет руля ±5°
    Maneuver("doublet", amp_deg=5, pulse_s=2.5, hold_throttle=True)   # + РУД зафиксирован
    Maneuver("multisine", amp_deg=5, duration_s=10)             # полигармонический сигнал
    Maneuver("3211", amp_deg=5, unit_s=1.0)                     # 3-2-1-1

Графики сохраняются в src/plots/.
"""

from pathlib import Path

from src.model_python_port.dynamics.maneuvers import Maneuver
from src.model_python_port.output.full_sim_outputs import (
    plot_bins_gnss_trajectory_dashboard,
    plot_ofk2_error_with_posterior_three_sigma,
    plot_ofk2_params_time,
    plot_ofk_error_with_posterior_three_sigma,
    print_bins_gnss_simulation_tables,
)
from src.model_python_port.output.plot_flight_3d import animate_flight_3d, plot_flight_3d
from src.model_python_port.simulation.bins_gnss_simulation import run_simulation

# ---------------- сценарий ----------------
T_MODEL = 60.0      # длительность, с
DT = 1e-3            # шаг модели ЛА и БИНС, с
DT_GNSS = 0.1        # период СНС и ОФК-1, с
DT_OFK2 = 0.2        # период ОФК-2, с
MANEUVER = Maneuver("doublet", amp_deg=5.0, pulse_s=2.5)
MAKE_ANIMATION = False   # GIF полёта (~1 мин на построение)
PLOTS_DIR = Path("src/plots")


if __name__ == "__main__":
    print(f"Запуск: {T_MODEL:.0f} с, манёвр {MANEUVER.kind}, амплитуда {MANEUVER.amp_deg}°")
    PLOTS_DIR.mkdir(parents=True, exist_ok=True)
    data = run_simulation(tmodel=T_MODEL, dt=DT, dt_gnss=DT_GNSS, dt_ofk2=DT_OFK2, maneuver=MANEUVER)
    print(f"\nСимуляция завершена: {len(data['time'])} точек лога")

    print_bins_gnss_simulation_tables(data)
    plot_bins_gnss_trajectory_dashboard(data, out_path=PLOTS_DIR / "bins_gnss_full.png")
    plot_ofk_error_with_posterior_three_sigma(data, out_dir=PLOTS_DIR)
    plot_ofk2_params_time(data, out_path=PLOTS_DIR / "ofk2_params_time.png")
    plot_ofk2_error_with_posterior_three_sigma(data, out_dir=PLOTS_DIR)
    plot_flight_3d(data, PLOTS_DIR / "flight_3d.png")
    if MAKE_ANIMATION:
        animate_flight_3d(data, PLOTS_DIR / "flight_3d.gif")
