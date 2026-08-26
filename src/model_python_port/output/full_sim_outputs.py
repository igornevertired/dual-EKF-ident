"""
Печать табличных логов и графиков симулятора БИНС/ГНСС (вызов из сценария ``run_full_sim.py``).

Требует ``matplotlib``.
"""

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import numpy as np
import matplotlib.pyplot as plt


def _geodetic_to_local_ne(fi, lam, h, fi0, lam0):
    """Широта/долгота (рад) → локальные North/East (м) относительно начала траектории."""
    a_earth = 6378245.0
    north = (np.asarray(fi, dtype=float) - fi0) * a_earth
    east = (np.asarray(lam, dtype=float) - lam0) * a_earth * np.cos(fi0)
    return north, east


def plot_passenger_aircraft_flight_trajectory(data, out_path=None):
    """
    Отдельный график траектории полёта пассажирского самолёта (истинная траектория FX1).

    Вид сверху (North–East) и профиль высоты по пройденному пути.
    """
    t = np.asarray(data["time"], dtype=float)
    fi = np.asarray(data["true_fi"], dtype=float)
    lam = np.asarray(data["true_lam"], dtype=float)
    h = np.asarray(data["true_h"], dtype=float)

    north, east = _geodetic_to_local_ne(fi, lam, h, fi[0], lam[0])
    track_km = np.sqrt(north**2 + east**2) / 1000.0

    path = Path(out_path or "passenger_aircraft_flight_trajectory.png")

    fig = plt.figure(figsize=(12, 5.5), constrained_layout=True)
    gs = fig.add_gridspec(1, 2, width_ratios=[1.15, 1.0], wspace=0.28)

    ax_plan = fig.add_subplot(gs[0, 0])
    sc = ax_plan.scatter(
        east / 1000.0,
        north / 1000.0,
        c=t,
        cmap="viridis",
        s=18,
        zorder=3,
    )
    ax_plan.plot(east / 1000.0, north / 1000.0, color="0.35", lw=0.8, alpha=0.6, zorder=2)
    ax_plan.scatter(east[0] / 1000.0, north[0] / 1000.0, c="green", s=80, marker="o", label="Старт", zorder=4)
    ax_plan.scatter(east[-1] / 1000.0, north[-1] / 1000.0, c="red", s=80, marker="s", label="Конец", zorder=4)
    ax_plan.set_xlabel("East (км)")
    ax_plan.set_ylabel("North (км)")
    ax_plan.set_title("Вид сверху")
    ax_plan.set_aspect("equal", adjustable="box")
    ax_plan.grid(True, alpha=0.3)
    ax_plan.legend(loc="best", fontsize=8)
    cbar = fig.colorbar(sc, ax=ax_plan, fraction=0.046, pad=0.04)
    cbar.set_label("Время (с)")

    ax_prof = fig.add_subplot(gs[0, 1])
    ax_prof.plot(track_km, h, color="steelblue", lw=2.0)
    ax_prof.scatter(track_km[0], h[0], c="green", s=60, zorder=3)
    ax_prof.scatter(track_km[-1], h[-1], c="red", s=60, zorder=3)
    ax_prof.set_xlabel("Пройденный путь (км)")
    ax_prof.set_ylabel("Высота (м)")
    ax_prof.set_title("Профиль высоты")
    ax_prof.grid(True, alpha=0.3)

    fig.suptitle("Траектория полёта пассажирского самолёта", fontsize=14, fontweight="bold")
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def plot_latitude_vs_longitude(data, out_path=None):
    """
    Траектория полёта: широта от долготы по **тем же** ``true_fi`` / ``true_lam``,
    что и в ``plot_bins_gnss_trajectory_dashboard`` (лог ``run_simulation``).
    """
    fi = np.asarray(data["true_fi"], dtype=float)
    lam = np.asarray(data["true_lam"], dtype=float)

    path = Path(out_path or "latitude_vs_longitude.png")

    fig, ax = plt.subplots(figsize=(7, 5.5), constrained_layout=True)
    ax.plot(fi * 1.0e3, lam * 1.0e5, color="blue", lw=2.0)
    ax.set_xlabel("Долгота (рад.)")
    ax.set_ylabel("Широта (рад.)")
    ax.set_title("Траектория полета")
    ax.grid(True, alpha=0.3)
    ax.text(1.0, -0.08, "×10⁻³", transform=ax.transAxes, ha="right", va="top", fontsize=10)
    ax.text(0.0, 1.02, "×10⁻⁵", transform=ax.transAxes, ha="left", va="bottom", fontsize=10)

    plt.savefig(path, dpi=150)
    plt.close(fig)
    t_end = float(np.max(data["time"]))
    print(
        f"\nPlot saved to {path}  "
        f"(истина FX1, T={t_end:.0f} с, fi_end={fi[-1]:.4e}, lam_end={lam[-1]:.4e})"
    )


def plot_bins_gnss_trajectory_dashboard(data, out_path=None):
    """
    Абсолютные навигационные параметры (не ошибки): φ, λ, h, Vn, Ve, Vh.

    Кривые:
      истина FX1 — эталон траектории;
      БИНС до ОФК — механизация на такте ГНСС до коррекции;
      БИНС после ОФК-1 — тот же вектор после обратной связи фильтра;
      ГНСС — измерения PVT (точки).

    Ошибки ``оценка − истина`` и ±3σ — на ``ofk_error_vs_three_sigma_P.png``.
    """
    t = data["time"]

    fig, axes = plt.subplots(2, 3, figsize=(18, 9))

    # Единые подписи легенды для всех панелей
    lbl_true = "истина FX1"
    lbl_bins = "БИНС до ОФК"
    lbl_ofk = "БИНС после ОФК-1"
    lbl_gnss = "ГНСС (измерение)"

    def add_gnss(ax, t_m, y_meas, mask):
        ax.plot(t_m[mask], y_meas[mask], "g.", markersize=4, label=lbl_gnss)

    panels = [
        (axes[0, 0], np.degrees(data["true_fi"]), np.degrees(data["bins_fi"]),
         np.degrees(data["ofk_fi"]), np.degrees(data["gnss_fi"]),
         r"широта $\varphi$", "°", False),
        (axes[0, 1], np.degrees(data["true_lam"]), np.degrees(data["bins_lam"]),
         np.degrees(data["ofk_lam"]), np.degrees(data["gnss_lam"]),
         r"долгота $\lambda$", "°", False),
        (axes[0, 2], data["true_h"], data["bins_h"], data["ofk_h"], data["gnss_h"],
         r"высота $h$", "м", False),
        (axes[1, 0], data["true_vn"], data["bins_vn"], data["ofk_vn"], data["gnss_vn"],
         r"скорость север $V_N$", "м/с", True),
        (axes[1, 1], data["true_ve"], data["bins_ve"], data["ofk_ve"], data["gnss_ve"],
         r"скорость восток $V_E$", "м/с", True),
        (axes[1, 2], data["true_vh"], data["bins_vh"], data["ofk_vh"], data["gnss_vh"],
         r"скорость вертикаль $V_H$", "м/с", True),
    ]

    for ax, y_t, y_b, y_o, y_g, title, unit, xlabel in panels:
        ax.plot(t, y_t, "k-", lw=1.5, label=lbl_true)
        ax.plot(t, y_b, "r--", lw=1, label=lbl_bins)
        ax.plot(t, y_o, "b-", lw=1.2, label=lbl_ofk)
        mask = ~np.isnan(y_g)
        add_gnss(ax, t, y_g, mask)
        ax.set_title(title, fontsize=11)
        ax.set_ylabel(unit)
        if xlabel:
            ax.set_xlabel("Время (с)")
        ax.legend(fontsize=6, loc="best")
        ax.grid(True, alpha=0.3)

    fig.suptitle(
        "Абсолютные параметры навигации (не ошибки): истина FX1 / БИНС / ОФК-1 / ГНСС",
        fontsize=13,
        fontweight="bold",
    )
    path = Path(out_path or "bins_gnss_full.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def plot_ofk_error_with_posterior_three_sigma(data, out_dir=None):
    """
    Ошибки навигации после ОФК-1: δ = (БИНС после коррекции) − (истина FX1)
    на тактах ГНСС; полосы ±3√Pᵢᵢ апостериори.
    """
    t = np.asarray(data["time"], dtype=float)

    defs = (
        (r"$\delta\varphi$", "°", data["err_ofk_fi"], data["ofk_std_fi"], np.degrees),
        (r"$\delta\lambda$", "°", data["err_ofk_lam"], data["ofk_std_lam"], np.degrees),
        (r"$\delta h$", "м", data["err_ofk_h"], data["ofk_std_h"], lambda x: x),
        (r"$\delta V_N$", "м/с", data["err_ofk_vn"], data["ofk_std_vn"], lambda x: x),
        (r"$\delta V_E$", "м/с", data["err_ofk_ve"], data["ofk_std_ve"], lambda x: x),
        (r"$\delta V_H$", "м/с", data["err_ofk_vh"], data["ofk_std_vh"], lambda x: x),
    )

    base = Path(out_dir or "plots_sigma")
    base.mkdir(parents=True, exist_ok=True)

    fig, axes = plt.subplots(6, 1, figsize=(12, 14), sharex=True)
    for ax, (name, u, err, std, sc) in zip(axes, defs):
        err = np.asarray(err, dtype=float)
        std = np.asarray(std, dtype=float)
        e = sc(err)
        band = sc(3.0 * std)
        ax.fill_between(
            t, -band, band, alpha=0.2, color="mediumpurple",
            label=r"$\pm 3\sqrt{P_{ii}}$ апостериори",
        )
        ax.plot(
            t, e, color="darkblue", lw=1.05,
            label=rf"ошибка: (БИНС после ОФК-1) − истина FX1 ({u})",
        )
        ax.axhline(0.0, color="gray", lw=0.7, ls=":")
        ax.set_ylabel(f"{name}\n({u})")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=6)

    axes[0].set_title(
        r"Ошибки навигации $\delta = x_{\mathrm{ОФК-1}} - x_{\mathrm{истина}}$ "
        r"и полосы $\pm 3\sigma$ по $P$ (6 каналов)"
    )
    axes[-1].set_xlabel("Время (с)")
    plt.tight_layout()
    outp = base / "ofk_error_vs_three_sigma_P.png"
    plt.savefig(outp, dpi=150)
    plt.close(fig)
    print(f"Plot saved to {outp}")


def plot_control_vector_deflections(
    data,
    out_path=None,
):
    """
    Графики вектора управления ``u = [δT, δV, δN, δE]``.
    Точки только на тактах ГНСС (как в логе ``data['u']``).

    По умолчанию сохраняет ``control_surface_deflections.png`` в текущем каталоге.
    """
    t = np.asarray(data["time"], dtype=float)
    u = np.asarray(data["u"], dtype=float)
    if u.ndim != 2 or u.shape[0] != 4:
        raise ValueError("data['u'] должен иметь форму (4, n_epochs)")

    path = Path(out_path or "control_surface_deflections.png")

    titles = [
        r"Относительная тяга $\delta_T$",
        r"Руль высоты $\delta_V$",
        r"Руль направления $\delta_N$",
        r"Элероны $\delta_E$",
    ]

    fig, axes = plt.subplots(4, 1, figsize=(10, 9), sharex=True)
    for i, ax in enumerate(axes):
        ax.plot(t, u[i], color="steelblue", lw=1.2, marker="o", markersize=2, alpha=0.85)
        yl = r"$\delta_T$ (−)" if i == 0 else "°, отклонение"
        ax.set_ylabel(yl)
        ax.set_title(titles[i])
        ax.grid(True, alpha=0.3)

    axes[-1].set_xlabel("Время (с)")
    fig.suptitle("Вектор управления ЛА на тактах ГНСС", fontsize=13, fontweight="bold")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def print_bins_gnss_simulation_tables(data):
    """Краткая выборочная таблица истинные / БИНС / ОФК / ГНСС каналы."""
    print("\n" + "=" * 110)
    print("ЛОГ: Истинные параметры ЛА")
    print("=" * 110)
    print(f"{'Time':>6s}  {'H(m)':>8s}  {'Fi(°)':>10s}  {'Lm(°)':>10s}  {'Vn':>8s}  {'Ve':>8s}")
    print("-" * 110)
    for i in range(0, len(data["time"]), max(1, len(data["time"]) // 10)):
        print(f"{data['time'][i]:6.1f}  {data['true_h'][i]:8.2f}  "
              f"{np.degrees(data['true_fi'][i]):10.6f}  {np.degrees(data['true_lam'][i]):10.6f}  "
              f"{data['true_vn'][i]:8.2f}  {data['true_ve'][i]:8.2f}")

    print(f"\n{'='*110}")
    print("ЛОГ: БИНС до коррекции ОФК (на тактах ГНСС)")
    print(f"{'='*110}")
    print(f"{'Time':>6s}  {'H':>8s}  {'dH':>6s}  {'Fi(°)':>10s}  {'dFi_bins':>10s}  {'Vn':>8s}  {'dVn_bins':>10s}")
    print("-" * 110)
    for i in range(0, len(data["time"]), max(1, len(data["time"]) // 10)):
        print(f"{data['time'][i]:6.1f}  {data['bins_h'][i]:8.2f}  {data['bins_h'][i]-data['true_h'][i]:6.3f}  "
              f"{np.degrees(data['bins_fi'][i]):10.6f}  {np.degrees(data['err_bins_fi'][i]):10.6f}  "
              f"{data['bins_vn'][i]:8.2f}  {data['err_bins_vn'][i]:10.3f}")

    print(f"\n{'='*110}")
    print("ЛОГ: навигация после коррекции ОФК")
    print(f"{'='*110}")
    print(f"{'Time':>6s}  {'Fi(°)':>10s}  {'dFi_ofk':>10s}  {'Vn':>8s}  {'dVn_ofk':>10s}")
    print("-" * 110)
    for i in range(0, len(data["time"]), max(1, len(data["time"]) // 10)):
        print(f"{data['time'][i]:6.1f}  {np.degrees(data['ofk_fi'][i]):10.6f}  {np.degrees(data['err_ofk_fi'][i]):10.6f}  "
              f"{data['ofk_vn'][i]:8.2f}  {data['err_ofk_vn'][i]:10.3f}")

    print(f"\n{'='*110}")
    print("ЛОГ: ГНСС (6 каналов: Fi, Lm, H, Vn, Ve, Vh)")
    print(f"{'='*110}")
    print(f"{'Time':>6s}  {'Fi(°)':>10s}  {'Lm(°)':>10s}  {'H(m)':>8s}  {'Vn':>8s}  {'Ve':>8s}  {'Vh':>8s}")
    print("-" * 110)
    for i in range(0, len(data["time"]), max(1, len(data["time"]) // 10)):
        if not np.isnan(data["gnss_fi"][i]):
            print(
                f"{data['time'][i]:6.1f}  {np.degrees(data['gnss_fi'][i]):10.6f}  "
                f"{np.degrees(data['gnss_lam'][i]):10.6f}  {data['gnss_h'][i]:8.2f}  "
                f"{data['gnss_vn'][i]:8.2f}  {data['gnss_ve'][i]:8.2f}  {data['gnss_vh'][i]:8.2f}"
            )

    if "sp_params" in data:
        print_ofk2_coeff_table(data)


def print_ofk2_coeff_table(data, index: int = -1) -> None:
    """Итоговая таблица L*,M*: теория | ОФК-2 | Δ."""
    from ..filtering.ofk2_theory import PARAM_NAMES

    th = data.get("sp_theory", {})
    i = index if index >= 0 else len(data["time"]) - 1
    t = float(data["time"][i])
    th_vec = np.asarray(data.get("sp_theory_vec", []), dtype=float)
    ekf = np.asarray(data["sp_params"][:, i], dtype=float)
    dlt = np.asarray(data["d_params"][:, i], dtype=float)
    print(f"\n{'='*72}")
    print(f"ОФК-2: короткопериод [{', '.join(PARAM_NAMES)}]  t = {t:.1f} с")
    if th:
        print(
            f"trim  α0={th.get('alpha0', float('nan')):.4f}  "
            f"q0={th.get('q0', float('nan')):.4f}  "
            f"δe0={th.get('delta_e0', float('nan')):.4f}"
        )
    print(f"{'='*72}")
    print(f"{'параметр':<10s}  {'теория':>14s}  {'ОФК-2':>14s}  {'Δ':>14s}")
    print("-" * 72)
    mae = 0.0
    for k, name in enumerate(PARAM_NAMES):
        th_v = float(th_vec[k]) if th_vec.size > k else float("nan")
        print(f"{name:<10s}  {th_v:14.6f}  {float(ekf[k]):14.6f}  {float(dlt[k]):14.3e}")
        mae += abs(float(dlt[k]))
    mae /= max(len(PARAM_NAMES), 1)
    print("-" * 72)
    print(f"MAE(|Δ|) = {mae:.6f}")
    print("=" * 72)


def plot_ofk2_identified_params(data, out_path=None):
    """Только идентифицируемые параметры: оценка ОФК-2 vs теория."""
    from ..filtering.ofk2_theory import PARAM_NAMES

    t = np.asarray(data["time"], dtype=float)
    path = Path(out_path or "ofk2_params.png")
    th_vec = np.asarray(data.get("sp_theory_vec", []), dtype=float)
    ekf = np.asarray(data["sp_params"], dtype=float)
    dlt = np.asarray(data["d_params"], dtype=float)
    n = len(PARAM_NAMES)

    fig, axes = plt.subplots(n, 2, figsize=(11, 3.2 * n), sharex=True)
    if n == 1:
        axes = np.asarray([axes])

    for k, name in enumerate(PARAM_NAMES):
        ax_p, ax_d = axes[k, 0], axes[k, 1]
        ax_p.plot(t, ekf[k], color="C0", lw=1.6, label="ОФК-2 (оценка)")
        if th_vec.size > k:
            ax_p.axhline(th_vec[k], color="k", ls="--", lw=1.4, label="теория (эталон)")
            ax_p.plot(t[0], ekf[k, 0], "o", color="C3", ms=7, label="старт (+50%)")
        ax_p.set_ylabel(name)
        ax_p.set_title(f"{name}: сходимость идентификации")
        ax_p.legend(fontsize=8, loc="best")
        ax_p.grid(True, alpha=0.3)

        ax_d.plot(t, dlt[k], color="C1", lw=1.4, label=r"$\Delta$ = оценка − теория")
        ax_d.axhline(0.0, color="k", lw=0.9, alpha=0.6)
        ax_d.set_ylabel(rf"$\Delta${name}")
        ax_d.set_title(f"{name}: ошибка после ОФК-2")
        ax_d.legend(fontsize=8, loc="best")
        ax_d.grid(True, alpha=0.3)

    axes[-1, 0].set_xlabel("Время (с)")
    axes[-1, 1].set_xlabel("Время (с)")
    fig.suptitle(
        "ОФК-2 short-period: Lα, Lq, Lδe, Mα, Mq, Mδe (оценка vs теория)",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def plot_ofk2_params_time(data, out_path=None):
    """Один PNG: отдельная панель на каждый L*/M* (оценка vs теория во времени)."""
    from ..filtering.ofk2_theory import PARAM_NAMES

    t = np.asarray(data["time"], dtype=float)
    path = Path(out_path or "ofk2_params_time.png")
    th = np.asarray(data.get("sp_theory_vec", []), dtype=float)
    ekf = np.asarray(data["sp_params"], dtype=float)
    n = len(PARAM_NAMES)
    ncols = 2
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.8 * nrows), sharex=True)
    axes_flat = np.atleast_1d(axes).ravel()

    for k, name in enumerate(PARAM_NAMES):
        ax = axes_flat[k]
        ax.plot(t, ekf[k], color="C0", lw=1.5, label="ОФК-2")
        if th.size > k:
            ax.axhline(th[k], color="k", ls="--", lw=1.2, label="теория")
            ax.plot(t[0], ekf[k, 0], "o", color="C3", ms=6, label="старт (+50%)")
        ax.set_ylabel(name)
        ax.set_title(name)
        ax.legend(fontsize=7, loc="best")
        ax.grid(True, alpha=0.3)

    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)

    for ax in axes_flat[max(0, n - ncols) : n]:
        ax.set_xlabel("Время (с)")

    fig.suptitle(
        "ОФК-2 short-period: L*, M* во времени (сплошная — оценка, пунктир — теория)",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def plot_ofk2_error_start_vs_end(data, out_path=None):
    """Столбцы: |Δ| на старте и в конце для каждого L*, M*."""
    from ..filtering.ofk2_theory import PARAM_NAMES

    path = Path(out_path or "ofk2_error_start_end.png")
    th = np.asarray(data.get("sp_theory_vec", []), dtype=float)
    ekf = np.asarray(data["sp_params"], dtype=float)
    dlt = np.asarray(data["d_params"], dtype=float)
    n = len(PARAM_NAMES)
    err0 = np.abs(dlt[:, 0])
    err1 = np.abs(dlt[:, -1])
    # относительная ошибка |Δ|/|теория|
    rel0 = err0 / np.maximum(np.abs(th[:n]), 1e-9)
    rel1 = err1 / np.maximum(np.abs(th[:n]), 1e-9)

    x = np.arange(n)
    w = 0.36
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))

    axes[0].bar(x - w / 2, err0, w, label="старт (|Δ|)", color="C3")
    axes[0].bar(x + w / 2, err1, w, label="итог (|Δ|)", color="C0")
    axes[0].set_xticks(x)
    axes[0].set_xticklabels(list(PARAM_NAMES))
    axes[0].set_ylabel(r"$|\hat\theta - \theta_{\mathrm{теор}}|$")
    axes[0].set_title("Абсолютная ошибка: старт → итог")
    axes[0].legend(fontsize=9)
    axes[0].grid(True, axis="y", alpha=0.3)

    axes[1].bar(x - w / 2, 100.0 * rel0, w, label="старт", color="C3")
    axes[1].bar(x + w / 2, 100.0 * rel1, w, label="итог", color="C0")
    axes[1].set_xticks(x)
    axes[1].set_xticklabels(list(PARAM_NAMES))
    axes[1].set_ylabel("% от |теории|")
    axes[1].set_title("Относительная ошибка: старт → итог")
    axes[1].legend(fontsize=9)
    axes[1].grid(True, axis="y", alpha=0.3)

    # подписи итоговых %
    for i in range(n):
        axes[1].text(
            i + w / 2,
            100.0 * rel1[i],
            f"{100.0 * rel1[i]:.1f}%",
            ha="center",
            va="bottom",
            fontsize=7,
        )

    t0 = float(data["time"][0])
    t1 = float(data["time"][-1])
    fig.suptitle(
        f"ОФК-2: ошибка идентификации L*,M*  (t={t0:.1f} с → t={t1:.1f} с, старт +50%)",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)

    print(f"\nPlot saved to {path}")
    print(f"{'параметр':<8s}  {'|Δ| старт':>12s}  {'|Δ| итог':>12s}  {'% старт':>10s}  {'% итог':>10s}")
    print("-" * 60)
    for i, name in enumerate(PARAM_NAMES):
        print(
            f"{name:<8s}  {err0[i]:12.6f}  {err1[i]:12.6f}  "
            f"{100*rel0[i]:9.1f}%  {100*rel1[i]:9.1f}%"
        )


def plot_ofk2_ekf(data, out_path=None):
    """ОФК-2 short-period: входы α–q–az и ошибки L*,M*."""
    from ..filtering.ofk2_theory import PARAM_NAMES

    t = np.asarray(data["time"], dtype=float)
    path = Path(out_path or "ofk2_ekf.png")
    d_params = np.asarray(data["d_params"], dtype=float)

    fig, axes = plt.subplots(3, 2, figsize=(11, 9), sharex=True)

    axes[0, 0].plot(t, data["true_alpha"], "k--", lw=1.0, label="α истина")
    axes[0, 0].plot(t, data["sp_alpha"], color="darkblue", lw=1.2, label="α БНК")
    axes[0, 0].set_ylabel("рад")
    axes[0, 0].set_title("Вход: α")
    axes[0, 0].legend(fontsize=8)
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(t, data["true_q"], "k--", lw=1.0, label="q истина")
    axes[0, 1].plot(t, data["sp_q"], color="darkblue", lw=1.2, label="q ДУС")
    axes[0, 1].set_ylabel("рад/с")
    axes[0, 1].set_title("Вход: q")
    axes[0, 1].legend(fontsize=8)
    axes[0, 1].grid(True, alpha=0.3)

    axes[1, 0].plot(t, data["true_az"], "k--", lw=1.0, label="az истина")
    axes[1, 0].plot(t, data["sp_az"], color="darkblue", lw=1.2, label="az ДЛУ")
    axes[1, 0].set_ylabel("g")
    axes[1, 0].set_title("Вход: az")
    axes[1, 0].legend(fontsize=8)
    axes[1, 0].grid(True, alpha=0.3)

    for k, name in enumerate(PARAM_NAMES):
        axes[1, 1].plot(t, d_params[k], lw=1.1, label=rf"$\Delta {name}$")
    axes[1, 1].axhline(0.0, color="k", lw=0.8, alpha=0.5)
    axes[1, 1].set_title(r"После ОФК-2: $\Delta$ = оценка − теория")
    axes[1, 1].legend(fontsize=7, ncol=2)
    axes[1, 1].grid(True, alpha=0.3)

    axes[2, 0].plot(t, data["sp_delta"][0], label=r"$\delta_{\dot\alpha}$")
    axes[2, 0].plot(t, data["sp_delta"][1], label=r"$\delta_{\dot q}$")
    axes[2, 0].plot(t, data["sp_delta"][2], label=r"$\delta_{az}$")
    axes[2, 0].set_title("Невязки equation-error")
    axes[2, 0].legend(fontsize=8)
    axes[2, 0].grid(True, alpha=0.3)
    axes[2, 0].set_xlabel("Время (с)")

    for k, name in enumerate(PARAM_NAMES):
        axes[2, 1].plot(t, data["sp_params"][k], lw=1.2, label=name)
    axes[2, 1].set_title("Оценки L*, M* во времени")
    axes[2, 1].legend(fontsize=7, ncol=2)
    axes[2, 1].grid(True, alpha=0.3)
    axes[2, 1].set_xlabel("Время (с)")

    fig.suptitle("ОФК-2 short-period: α–q–az → L*, M*", fontsize=12)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")
