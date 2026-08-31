"""
Сравнение идентификации L*, M* при doublet руля ±2°, ±5°, ±10°.
"""

from pathlib import Path

import numpy as np

from src.model_python_port.filtering.ofk2_theory import PARAM_NAMES
from src.model_python_port.output.full_sim_outputs import (
    plot_ofk2_params_time,
    print_ofk2_coeff_table,
)
from src.model_python_port.simulation.bins_gnss_simulation import run_simulation

AMPS = (2.0, 5.0, 10.0)


def _mae_and_rel(data) -> tuple[float, np.ndarray]:
    dlt = np.asarray(data["d_params"][:, -1], dtype=float)
    th = np.asarray(data["sp_theory_vec"], dtype=float)
    mae = float(np.mean(np.abs(dlt)))
    rel = np.abs(dlt) / np.maximum(np.abs(th), 1e-9) * 100.0
    return mae, rel


if __name__ == "__main__":
    plots_dir = Path("src/plots")
    plots_dir.mkdir(parents=True, exist_ok=True)
    rows = []

    for amp in AMPS:
        print(f"\n{'#' * 72}\nDoublet amplitude ±{amp:.0f}°\n{'#' * 72}")
        data = run_simulation(
            tmodel=60.0,
            dt=1e-3,
            dt_gnss=0.1,
            dt_ofk2=0.02,
            elevator_doublet_amp_deg=float(amp),
        )
        print_ofk2_coeff_table(data)
        tag = f"amp{int(amp)}"
        plot_ofk2_params_time(data, out_path=plots_dir / f"ofk2_params_time_{tag}.png")
        if int(amp) == 5:
            plot_ofk2_params_time(data, out_path=plots_dir / "ofk2_params_time.png")
        mae, rel = _mae_and_rel(data)
        rows.append((amp, mae, rel))

    print(f"\n{'=' * 72}")
    print("Сводка: MAE(|Δ|) и относительная ошибка |Δ|/|теория| (%), t = 60 с")
    print(f"{'=' * 72}")
    hdr = f"{'±δe,°':>8s}  {'MAE':>10s}  " + "  ".join(f"{n:>8s}" for n in PARAM_NAMES)
    print(hdr)
    print("-" * 72)
    for amp, mae, rel in rows:
        rel_s = "  ".join(f"{r:7.1f}%" for r in rel)
        print(f"{amp:8.0f}  {mae:10.5f}  {rel_s}")
    print("=" * 72)
