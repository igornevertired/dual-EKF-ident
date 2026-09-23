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
    plot_ofk2_ic_sweep,
    plot_ofk2_ic_error_three_sigma,
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
    data = run_simulation(tmodel=120.0, dt=1e-3, dt_gnss=0.1, dt_ofk2=0.02)
    print(f"\nСимуляция завершена: {len(data['time'])} точек лога")
    print_bins_gnss_simulation_tables(data)
    plot_bins_gnss_trajectory_dashboard(data, out_path=plots_dir / "bins_gnss_full.png")
    plot_ofk_error_with_posterior_three_sigma(data, out_dir=plots_dir)
    plot_ofk2_params_time(data, out_path=plots_dir / "ofk2_params_time.png")
    plot_ofk2_error_with_posterior_three_sigma(data, out_dir=plots_dir)

    print("\nОФК-2: разброс начальных условий...")
    ic_scales = tuple(round(0.2 * i, 1) for i in range(1, 11))
    ic_runs = []
    for scale in ic_scales:
        print(f"  старт ×{scale}")
        ic_runs.append(
            run_simulation(
                tmodel=60.0,
                dt=1e-3,
                dt_gnss=0.1,
                dt_ofk2=0.02,
                ofk2_start_scale=scale,
            )
        )
    plot_ofk2_ic_sweep(ic_runs, out_path=plots_dir / "ofk2_ic_sweep.png")
    plot_ofk2_ic_error_three_sigma(
        ic_runs, out_path=plots_dir / "ofk2_ic_error_three_sigma.png"
    )

    print("\nОФК-2: скачок аэродинамики при t=30 с (Cy^α, mz^α, mz^δV ×1.4)...")
    data_step = run_simulation(
        tmodel=60.0,
        dt=1e-3,
        dt_gnss=0.1,
        dt_ofk2=0.02,
        aero_step_t=30.0,
        aero_step_scale={7: 1.4, 20: 1.4, 22: 1.4},
        elevator_extra_t0=(32.0,),
        ofk2_q_std=0.003,
    )
    plot_ofk2_params_time(data_step, out_path=plots_dir / "ofk2_aero_step.png")
