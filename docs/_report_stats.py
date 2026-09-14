"""Сводные числовые показатели прогона для отчёта (docs/_report_stats.json)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.model_python_port.simulation.bins_gnss_simulation import run_simulation
from src.model_python_port.filtering.ofk2_theory import REPORT_PARAM_INDICES, REPORT_PARAM_NAMES

R_E = 6371000.0
OUT = Path(__file__).resolve().parent / "_report_stats.json"


def main() -> None:
    d = run_simulation(tmodel=60.0, dt=1e-3, dt_gnss=0.1, dt_ofk2=0.02)
    t = np.asarray(d["time"])
    m = t >= 5.0

    chan = {
        "fi": ("широта", R_E, "м"),
        "lam": ("долгота", R_E, "м"),
        "h": ("высота", 1.0, "м"),
        "vn": ("северная скорость", 1.0, "м/с"),
        "ve": ("восточная скорость", 1.0, "м/с"),
        "vh": ("вертикальная скорость", 1.0, "м/с"),
    }
    nav = {}
    for key, (name, k, unit) in chan.items():
        eb = np.asarray(d[f"err_bins_{key}"]) * k
        eo = np.asarray(d[f"err_ofk_{key}"]) * k
        s3 = 3.0 * np.asarray(d[f"ofk_std_{key}"]) * k
        nav[key] = {
            "name": name,
            "unit": unit,
            "rms_bins": float(np.sqrt(np.mean(eb[m] ** 2))),
            "rms_ofk": float(np.sqrt(np.mean(eo[m] ** 2))),
            "max_bins": float(np.max(np.abs(eb[m]))),
            "max_ofk": float(np.max(np.abs(eo[m]))),
            "sigma3_end": float(s3[-1]),
            "inside": float(np.mean(np.abs(eo[m]) <= s3[m]) * 100.0),
        }

    th = np.asarray(d["sp_theory_vec"], dtype=float)
    est = np.asarray(d["sp_params"])[:, -1]
    std = np.asarray(d["sp_std"])[:, -1]
    par0 = np.asarray(d["sp_params"])[:, 0]
    coeff = []
    for idx, name in zip(REPORT_PARAM_INDICES, REPORT_PARAM_NAMES):
        coeff.append(
            {
                "name": name,
                "theory": float(th[idx]),
                "start": float(par0[idx]),
                "est": float(est[idx]),
                "delta": float(est[idx] - th[idx]),
                "sigma3": float(3.0 * std[idx]),
                "rel": float(abs(est[idx] - th[idx]) / max(abs(th[idx]), 1e-12) * 100.0),
            }
        )

    OUT.write_text(
        json.dumps({"nav": nav, "coeff": coeff, "t_end": float(t[-1])}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(OUT)


if __name__ == "__main__":
    main()
