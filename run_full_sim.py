"""
Точка входа: ЛА + БИНС + ГНСС + ОФК-1 + ОФК-2 (``bins_gnss_simulation.run_simulation``).

Запуск из корня репозитория::

    python run_full_sim.py
"""

from pathlib import Path

from src.model_python_port.simulation.bins_gnss_simulation import run_simulation
from src.model_python_port.output.full_sim_outputs import (
    plot_bins_gnss_trajectory_dashboard,
    plot_ofk_error_with_posterior_three_sigma,
    plot_ofk2_error_with_posterior_three_sigma,
    plot_ofk2_params_time,
    print_bins_gnss_simulation_tables,
)

__all__ = [
    "run_simulation",
    "plot_bins_gnss_trajectory_dashboard",
    "plot_ofk_error_with_posterior_three_sigma",
    "plot_ofk2_params_time",
    "print_bins_gnss_simulation_tables",
]


if __name__ == "__main__":
    print("Запуск симуляции БИНС + ГНСС + ОФК-1 + ОФК-2...")
    plots_dir = Path("src/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    data = run_simulation(
        tmodel=240.0,
        dt=1e-3,
        dt_gnss=0.1,
        dt_ofk2=0.2,
    )
    print(f"\nСимуляция завершена: {len(data['time'])} точек лога")
    print_bins_gnss_simulation_tables(data)
    plot_bins_gnss_trajectory_dashboard(data, out_path=plots_dir / "bins_gnss_full.png")
    plot_ofk_error_with_posterior_three_sigma(data, out_dir=plots_dir)
    plot_ofk2_params_time(data, out_path=plots_dir / "ofk2_params_time.png")
    plot_ofk2_error_with_posterior_three_sigma(data, out_dir=plots_dir)
