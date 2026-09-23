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
    """Траектория FX1 в локальных метрах (север / восток от старта)."""
    fi = np.asarray(data["true_fi"], dtype=float)
    lam = np.asarray(data["true_lam"], dtype=float)
    north, east = _geodetic_to_local_ne(fi, lam, 0.0, fi[0], lam[0])

    path = Path(out_path or "latitude_vs_longitude.png")

    fig, ax = plt.subplots(figsize=(7, 5.5), constrained_layout=True)
    ax.plot(east, north, color="blue", lw=2.0)
    ax.scatter(east[0], north[0], c="green", s=50, zorder=3, label="старт")
    ax.scatter(east[-1], north[-1], c="red", s=50, marker="s", zorder=3, label="конец")
    ax.set_xlabel("Восток, м")
    ax.set_ylabel("Север, м")
    ax.set_title("Траектория полёта (локальные метры)")
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, loc="best")

    plt.savefig(path, dpi=150)
    plt.close(fig)
    t_end = float(np.max(data["time"]))
    print(
        f"\nPlot saved to {path}  "
        f"(истина FX1, T={t_end:.0f} с, N={north[-1]:.1f} м, E={east[-1]:.1f} м)"
    )


def plot_bins_gnss_trajectory_dashboard(data, out_path=None):
    """
    Абсолютные навигационные параметры (не ошибки): φ, λ, h, Vn, Ve, Vh.

    Кривые:
      истина FX1 — эталон траектории;
      БИНС — автономное счисление по сырым ДУС/ДЛУ;
      ОФК-1 (потребитель) — NP минус ошибки фильтра, в БИНС не пишется;
      ГНСС — измерения PVT (точки).

    Ошибки ``оценка − истина`` и ±3σ — на ``ofk_error_vs_three_sigma_P.png``.
    """
    t = data["time"]
    fi0 = float(np.asarray(data["true_fi"], dtype=float)[0])
    lam0 = float(np.asarray(data["true_lam"], dtype=float)[0])
    a_earth = 6378245.0
    rn = a_earth
    re = a_earth * np.cos(fi0)

    def _n(fi):
        return (np.asarray(fi, dtype=float) - fi0) * rn

    def _e(lam):
        return (np.asarray(lam, dtype=float) - lam0) * re

    fig, axes = plt.subplots(2, 3, figsize=(18, 9))

    # Единые подписи легенды для всех панелей
    lbl_true = "истина FX1"
    lbl_bins = "БИНС (автономный)"
    lbl_ofk = "ОФК-1 (потребитель)"
    lbl_gnss = "ГНСС (измерение)"

    def add_gnss(ax, t_m, y_meas, mask):
        ax.plot(t_m[mask], y_meas[mask], "g.", markersize=4, label=lbl_gnss)

    panels = [
        (axes[0, 0], _n(data["true_fi"]), _n(data["bins_fi"]),
         _n(data["ofk_fi"]), _n(data["gnss_fi"]),
         r"север (от $\varphi_0$)", "м", False),
        (axes[0, 1], _e(data["true_lam"]), _e(data["bins_lam"]),
         _e(data["ofk_lam"]), _e(data["gnss_lam"]),
         r"восток (от $\lambda_0$)", "м", False),
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
        (
            "Автономный БИНС (без обратной связи ОФК-1): истина FX1 / БИНС / ГНСС"
            if not data.get("ofk1_feedback", True)
            else "Абсолютные параметры навигации (не ошибки): истина FX1 / БИНС / ОФК-1 / ГНСС"
        ),
        fontsize=13,
        fontweight="bold",
    )
    path = Path(out_path or "bins_gnss_full.png")
    path.parent.mkdir(parents=True, exist_ok=True)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def plot_ofk_error_with_posterior_three_sigma(data, out_dir=None, *, out_path=None, title=None, error_from="ofk"):
    """
    Ошибки навигации: δ = (БИНС) − (истина FX1)
    на тактах ГНСС; полосы ±3√Pᵢᵢ апостериори ОФК-1.

    error_from: ``ofk`` — выход ОФК-1 потребителю; ``bins`` — автономный БИНС.
    """
    t = np.asarray(data["time"], dtype=float)
    fi0 = float(np.asarray(data["true_fi"], dtype=float)[0])
    a_earth = 6378245.0
    rn = a_earth
    re = a_earth * np.cos(fi0)
    if error_from == "bins":
        err_keys = (
            "err_bins_fi", "err_bins_lam", "err_bins_h",
            "err_bins_vn", "err_bins_ve", "err_bins_vh",
        )
        line_label = r"ошибка: (автономный БИНС) $-$ истина FX1"
    else:
        err_keys = (
            "err_ofk_fi", "err_ofk_lam", "err_ofk_h",
            "err_ofk_vn", "err_ofk_ve", "err_ofk_vh",
        )
        line_label = r"ошибка: (ОФК-1, потребитель) $-$ истина FX1"

    defs = (
        (r"$\delta N$", "м", data[err_keys[0]], data["ofk_std_fi"], lambda x: np.asarray(x) * rn),
        (r"$\delta E$", "м", data[err_keys[1]], data["ofk_std_lam"], lambda x: np.asarray(x) * re),
        (r"$\delta h$", "м", data[err_keys[2]], data["ofk_std_h"], lambda x: x),
        (r"$\delta V_N$", "м/с", data[err_keys[3]], data["ofk_std_vn"], lambda x: x),
        (r"$\delta V_E$", "м/с", data[err_keys[4]], data["ofk_std_ve"], lambda x: x),
        (r"$\delta V_H$", "м/с", data[err_keys[5]], data["ofk_std_vh"], lambda x: x),
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
            label=f"{line_label} ({u})",
        )
        ax.axhline(0.0, color="gray", lw=0.7, ls=":")
        ax.set_ylabel(f"{name}\n({u})")
        ax.grid(True, alpha=0.3)
        ax.legend(loc="upper right", fontsize=6)

    axes[0].set_title(
        title
        or (
            r"Ошибки навигации $\delta = x_{\mathrm{ОФК-1}} - x_{\mathrm{истина}}$ "
            r"и полосы $\pm 3\sigma$ по $P$ (6 каналов)"
        )
    )
    axes[-1].set_xlabel("Время (с)")
    plt.tight_layout()
    outp = Path(out_path) if out_path else (base / "ofk_error_vs_three_sigma_P.png")
    outp.parent.mkdir(parents=True, exist_ok=True)
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
    print("ЛОГ: автономный БИНС (на тактах ГНСС)")
    print(f"{'='*110}")
    print(f"{'Time':>6s}  {'H':>8s}  {'dH':>6s}  {'Fi(°)':>10s}  {'dFi_bins':>10s}  {'Vn':>8s}  {'dVn_bins':>10s}")
    print("-" * 110)
    for i in range(0, len(data["time"]), max(1, len(data["time"]) // 10)):
        print(f"{data['time'][i]:6.1f}  {data['bins_h'][i]:8.2f}  {data['bins_h'][i]-data['true_h'][i]:6.3f}  "
              f"{np.degrees(data['bins_fi'][i]):10.6f}  {np.degrees(data['err_bins_fi'][i]):10.6f}  "
              f"{data['bins_vn'][i]:8.2f}  {data['err_bins_vn'][i]:10.3f}")

    print(f"\n{'='*110}")
    print("ЛОГ: выход ОФК-1 для потребителей")
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

    t = np.asarray(data["ofk2_time"], dtype=float)
    path = Path(out_path or "ofk2_params_time.png")
    th_trim = np.asarray(data.get("sp_theory_vec_trim", []), dtype=float)
    th_t = np.asarray(data["ofk2_theory"], dtype=float)
    ekf = np.asarray(data["ofk2_params"], dtype=float)
    start_err = 100.0 * float(data.get("coeff_start_err", 0.0))
    n = len(PARAM_NAMES)
    ncols = 2
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.8 * nrows), sharex=True)
    axes_flat = np.atleast_1d(axes).ravel()

    for k, name in enumerate(PARAM_NAMES):
        ax = axes_flat[k]
        ax.plot(t, ekf[k], color="C0", lw=1.5, label="ОФК-2")
        ax.plot(t, th_t[k], color="k", lw=1.2, label="теория FX1(t)")
        t_step = data.get("aero_step_t")
        if t_step is not None:
            ax.axvline(float(t_step), color="crimson", ls=":", lw=1.0, label="скачок PAR")
        if th_trim.size > k:
            ax.axhline(
                th_trim[k], color="darkorange", ls="--", lw=1.1,
                label="теория на балансировке",
            )
            ax.plot(
                t[0], ekf[k, 0], "o", color="C3", ms=6,
                label=f"старт (+{start_err:.0f}%)",
            )
        # для малых коэффициентов (Lθ, Mθ, Lv, Mv) — масштаб по данным
        if max(abs(th_trim[k]), float(np.max(np.abs(ekf[k]))), float(np.max(np.abs(th_t[k])))) < 0.02:
            yc = np.concatenate([ekf[k], th_t[k], [th_trim[k]]])
            pad = max(0.0003, 0.15 * float(np.ptp(yc)) if np.ptp(yc) > 0 else 0.001)
            mid = float(np.median(yc))
            ax.set_ylim(mid - pad, mid + pad)
        ax.set_ylabel(name)
        ax.set_title(name)
        ax.legend(fontsize=7, loc="best")
        ax.grid(True, alpha=0.3)

    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)

    for ax in axes_flat[max(0, n - ncols) : n]:
        ax.set_xlabel("Время (с)")

    fig.suptitle(
        "ОФК-2 short-period: L*, M* во времени "
        "(синяя — оценка, чёрная — эталон FX1(t), оранжевая — балансировка)",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def plot_ofk2_params_with_three_sigma(data, out_path=None):
    """
    Hoff: θ̂(t) с полосами [θ̂ − 3σ, θ̂ + 3σ]; пунктир — эталон на балансировке.
    """
    from ..filtering.ofk2_theory import REPORT_PARAM_INDICES, REPORT_PARAM_NAMES

    t = np.asarray(data["ofk2_time"], dtype=float)
    path = Path(out_path or "ofk2_params_three_sigma.png")
    th_trim = np.asarray(data.get("sp_theory_vec_trim", []), dtype=float)
    ekf = np.asarray(data["ofk2_params"], dtype=float)
    std = np.asarray(data["ofk2_std"], dtype=float)
    names = REPORT_PARAM_NAMES
    n = len(names)
    ncols = 2
    nrows = int(np.ceil(n / ncols))

    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.8 * nrows), sharex=True)
    axes_flat = np.atleast_1d(axes).ravel()

    for ax, pi, name in zip(axes_flat, REPORT_PARAM_INDICES, names):
        band = 3.0 * std[pi]
        ax.fill_between(
            t, ekf[pi] - band, ekf[pi] + band,
            alpha=0.25, color="mediumpurple", label=r"$\pm 3\sigma$",
        )
        ax.plot(t, ekf[pi], color="C0", lw=1.5, label=r"$\hat{\theta}$")
        if th_trim.size > pi:
            ax.axhline(
                th_trim[pi], color="darkorange", ls="--", lw=1.1,
                label="теория (балансировка)",
            )
        ax.set_ylabel(name)
        ax.set_title(name)
        ax.legend(fontsize=7, loc="best")
        ax.grid(True, alpha=0.3)

    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)

    for ax in axes_flat[max(0, n - ncols) : n]:
        ax.set_xlabel("Время (с)")

    fig.suptitle(
        "ОФК-2 (Hoff): оценка параметров и полосы ±3σ",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def _plot_ofk2_error_three_sigma_panels(
    t,
    err,
    std,
    param_names,
    param_indices,
    *,
    title: str,
    out_path: Path,
    band_color: str = "mediumpurple",
    line_color: str = "darkblue",
    band_label: str = r"$\pm 3\sigma$",
    line_label: str = r"$\Delta$",
):
    fig, axes = plt.subplots(len(param_names), 1, figsize=(12, 2.2 * len(param_names)), sharex=True)
    axes = np.atleast_1d(axes)

    for ax, pi, name in zip(axes, param_indices, param_names):
        band = 3.0 * std[pi]
        ax.fill_between(
            t, -band, band, alpha=0.2, color=band_color, label=band_label,
        )
        ax.plot(t, err[pi], color=line_color, lw=1.05, label=line_label)
        ax.axhline(0.0, color="gray", lw=0.7, ls=":")
        ax.set_ylabel(name)
        ax.grid(True, alpha=0.3)
        if pi == param_indices[0]:
            ax.legend(loc="upper right", fontsize=8)

    axes[0].set_title(title)
    axes[-1].set_xlabel("Время (с)")
    plt.tight_layout()
    plt.savefig(out_path, dpi=150)
    plt.close(fig)
    print(f"Plot saved to {out_path}")


def plot_ofk2_error_with_posterior_three_sigma(data, out_dir=None):
    """ОФК-2 (новая модель): Δ = θ̂ − θ_trim и полосы ±3σ (без Lθ, Mθ)."""
    from ..filtering.ofk2_theory import REPORT_PARAM_INDICES, REPORT_PARAM_NAMES

    t = np.asarray(data["ofk2_time"], dtype=float)
    err = np.asarray(
        data.get("ofk2_d_params_trim", data["ofk2_d_params"]), dtype=float
    )
    std = np.asarray(data["ofk2_std"], dtype=float)

    base = Path(out_dir or "src/plots")
    base.mkdir(parents=True, exist_ok=True)

    _plot_ofk2_error_three_sigma_panels(
        t,
        err,
        std,
        REPORT_PARAM_NAMES,
        REPORT_PARAM_INDICES,
        title="ОФК-2 (новая модель): ошибка параметров и полосы ±3σ",
        out_path=base / "ofk2_error_vs_three_sigma_P.png",
        band_label=r"$\pm 3\sigma$ фильтра",
        line_label="ошибка: оценка − балансировка",
    )


def plot_ofk2_error_legacy_three_sigma(data, out_dir=None):
    """ОФК-2 (Hoff, 3 рег., 6 coeff): Δ = θ̂ − θ_trim и полосы ±3σ."""
    from ..filtering.ofk2_ekf_legacy import LEGACY_PARAM_NAMES

    if "ofk2_legacy_d_params_trim" not in data:
        print("plot_ofk2_error_legacy_three_sigma: нет legacy-лога, пропуск")
        return

    t = np.asarray(data["ofk2_time"], dtype=float)
    err = np.asarray(data["ofk2_legacy_d_params_trim"], dtype=float)
    std = np.asarray(data["ofk2_legacy_std"], dtype=float)

    base = Path(out_dir or "src/plots")
    base.mkdir(parents=True, exist_ok=True)

    _plot_ofk2_error_three_sigma_panels(
        t,
        err,
        std,
        LEGACY_PARAM_NAMES,
        tuple(range(len(LEGACY_PARAM_NAMES))),
        title="ОФК-2 (Hoff, 3 рег.): ошибка параметров и полосы ±3σ",
        out_path=base / "ofk2_error_vs_three_sigma_legacy.png",
        band_color="darkorange",
        line_color="firebrick",
        band_label=r"$\pm 3\sigma$ фильтра",
        line_label="ошибка: оценка − балансировка",
    )


def plot_ofk2_theory_drift(data, out_path=None):
    """
    Дрейф самого эталона: θ_FX1(t) на такте ОФК-2 против θ_FX1(t₀) с балансировки.

    Отвечает на вопрос, меняется ли «истина» из-за внутренней динамики ЛА.
    """
    from ..filtering.ofk2_theory import PARAM_NAMES

    t = np.asarray(data["ofk2_time"], dtype=float)
    th = np.asarray(data["ofk2_theory"], dtype=float)
    est = np.asarray(data["ofk2_params"], dtype=float)
    th_trim = np.asarray(data["sp_theory_vec_trim"], dtype=float)

    path = Path(out_path or "ofk2_theory_drift.png")
    n = len(PARAM_NAMES)
    nrows = int(np.ceil(n / 2))

    fig, axes = plt.subplots(nrows, 2, figsize=(12, 2.9 * nrows), sharex=True)
    axes_flat = np.atleast_1d(axes).ravel()

    for k, name in enumerate(PARAM_NAMES):
        ax = axes_flat[k]
        ax.plot(t, th[k], color="k", lw=1.4, label=r"$\theta_{\mathrm{FX1}}(t)$")
        ax.axhline(
            th_trim[k], color="darkorange", ls="--", lw=1.2,
            label=r"$\theta_{\mathrm{FX1}}(t_0)$ балансировка",
        )
        ax.plot(t, est[k], color="C0", lw=1.0, alpha=0.75, label="ОФК-2")
        span = 100.0 * np.ptp(th[k]) / max(abs(th_trim[k]), 1e-12)
        ax.set_title(f"{name}   размах эталона {span:.1f}%")
        ax.set_ylabel(name)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=6, loc="best")

    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)
    for ax in axes_flat[max(0, n - 2) : n]:
        ax.set_xlabel("Время (с)")

    fig.suptitle(
        "ОФК-2: дрейф эталона FX1 во времени против фиксированной балансировки",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def print_ofk2_theory_drift_table(data) -> None:
    """Числа к ``plot_ofk2_theory_drift``: насколько эталон уходит от балансировки."""
    from ..filtering.ofk2_theory import PARAM_NAMES

    th = np.asarray(data["ofk2_theory"], dtype=float)
    est = np.asarray(data["ofk2_params"], dtype=float)
    std = np.asarray(data["ofk2_std"], dtype=float)
    th_trim = np.asarray(data["sp_theory_vec_trim"], dtype=float)

    print("\n" + "=" * 96)
    print("ОФК-2: дрейф эталона FX1 и итоговая ошибка (такт ОФК-2)")
    print("=" * 96)
    print(
        f"{'':>5s}  {'trim':>9s}  {'min(t)':>9s}  {'max(t)':>9s}  "
        f"{'размах%':>8s}  {'оценка':>9s}  {'Δ(t)':>9s}  {'Δtrim':>9s}  {'3σ':>8s}"
    )
    print("-" * 96)
    for k, name in enumerate(PARAM_NAMES):
        base = max(abs(th_trim[k]), 1e-12)
        print(
            f"{name:>5s}  {th_trim[k]:9.4f}  {th[k].min():9.4f}  {th[k].max():9.4f}  "
            f"{100 * np.ptp(th[k]) / base:8.1f}  {est[k, -1]:9.4f}  "
            f"{est[k, -1] - th[k, -1]:9.4f}  {est[k, -1] - th_trim[k]:9.4f}  "
            f"{3 * std[k, -1]:8.4f}"
        )
    print("-" * 96)


def plot_ofk2_error_start_vs_end(data, out_path=None):
    """Кривые Δ(t): оценка − trim; пунктир — дрейф эталона FX1(t) − trim (без Lθ, Mθ)."""
    from ..filtering.ofk2_theory import REPORT_PARAM_INDICES, REPORT_PARAM_NAMES

    path = Path(out_path or "ofk2_error_start_end.png")
    err_trim = np.asarray(data["ofk2_d_params_trim"], dtype=float)
    th_inst = np.asarray(data["ofk2_theory"], dtype=float)
    th_trim = np.asarray(data.get("sp_theory_vec_trim", data.get("sp_theory_vec", [])), dtype=float)
    drift = th_inst - th_trim.reshape(-1, 1)
    t = np.asarray(data["ofk2_time"], dtype=float)

    names = REPORT_PARAM_NAMES
    n = len(names)
    ncols = 2
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(12, 2.5 * nrows), sharex=True)
    axes_flat = np.atleast_1d(axes).ravel()

    start_err = float(data.get("coeff_start_err", 0.3))
    for ax, pi, name in zip(axes_flat, REPORT_PARAM_INDICES, names):
        ax.plot(t, err_trim[pi], color="C0", lw=1.15, label="ОФК-2")
        ax.plot(
            t, drift[pi], color="k", lw=1.0, ls="--", alpha=0.85,
            label="вычисляемый эталон",
        )
        ax.axhline(0.0, color="darkorange", lw=1.0, ls=":", label="эталон")
        ax.plot(t[0], err_trim[pi, 0], "o", color="C3", ms=5)
        ax.plot(t[-1], err_trim[pi, -1], "s", color="C2", ms=5)
        ax.set_ylabel(name)
        ax.set_title(name, fontsize=9)
        ax.grid(True, alpha=0.3)
        if pi == REPORT_PARAM_INDICES[0]:
            ax.legend(fontsize=6.5, loc="upper right")

    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)
    for ax in axes_flat[max(0, n - ncols) : n]:
        ax.set_xlabel("Время (с)")

    fig.suptitle(
        f"ОФК-2: ошибка оценки и дрейф вычисляемого эталона FX1(t)  "
        f"(старт +{100 * start_err:.0f}% от балансировки)",
        fontsize=12,
    )
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)

    print(f"\nPlot saved to {path}")
    print(f"{'параметр':<8s}  {'trim':>10s}  {'|Δ|старт':>10s}  {'|Δ|итог':>10s}  {'FX1 размах':>12s}")
    print("-" * 58)
    for pi, name in zip(REPORT_PARAM_INDICES, names):
        err0 = abs(err_trim[pi, 0])
        err1 = abs(err_trim[pi, -1])
        span = float(np.ptp(th_inst[pi]))
        print(
            f"{name:<8s}  {th_trim[pi]:10.4g}  {err0:10.6f}  {err1:10.6f}  {span:12.6f}"
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
    axes[2, 0].plot(t, data["sp_delta"][2], label=r"$\delta_{\dot V}$")
    axes[2, 0].plot(t, data["sp_delta"][3], label=r"$\delta_{az}$")
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


def plot_ofk2_ic_sweep(runs: list[dict], out_path=None):
    """Старты θ̂(0)=k·θ_trim: кривые и |ошибка| в %: старт → конец."""
    from ..filtering.ofk2_theory import REPORT_PARAM_INDICES, REPORT_PARAM_NAMES

    path = Path(out_path or "ofk2_ic_sweep.png")
    n = len(REPORT_PARAM_NAMES)
    ncols = 2
    nrows = int(np.ceil(n / ncols))
    labels = [_ic_label(run) for run in runs]
    fig = plt.figure(figsize=(16, 2.35 * nrows + 5.0))
    gs = fig.add_gridspec(
        nrows + 2,
        ncols,
        height_ratios=[1.0] * nrows + [0.22, 1.05],
        hspace=0.42,
        top=0.96,
        bottom=0.04,
        left=0.07,
        right=0.98,
    )

    ref = runs[0]
    th = np.asarray(ref["ofk2_theory"], dtype=float)
    t_ref = np.asarray(ref["ofk2_time"], dtype=float)
    th_trim = np.asarray(
        ref.get("sp_theory_vec_trim", ref.get("sp_theory_vec")), dtype=float
    )

    def _start_pct(run: dict) -> float:
        sc = run.get("ofk2_start_scale")
        if sc is None:
            return 100.0 * abs(float(run.get("coeff_start_err", 0.3)))
        return 100.0 * abs(float(sc) - 1.0)

    def _end_pct(err_vec: np.ndarray, pi: int) -> float:
        den = max(abs(float(th_trim[pi])), 1e-12)
        return 100.0 * abs(float(err_vec[pi, -1])) / den

    axes_time = []
    for i in range(nrows):
        for j in range(ncols):
            axes_time.append(
                fig.add_subplot(gs[i, j], sharex=axes_time[0] if axes_time else None)
            )

    for k, (ax, pi, name) in enumerate(
        zip(axes_time, REPORT_PARAM_INDICES, REPORT_PARAM_NAMES)
    ):
        ax.plot(t_ref, th[pi], color="k", lw=1.4, label="эталон (балансировка / FX1)")
        for run, lab in zip(runs, labels):
            t = np.asarray(run["ofk2_time"], dtype=float)
            ekf = np.asarray(run["ofk2_params"], dtype=float)
            ax.plot(t, ekf[pi], lw=1.2, label=lab)
        ax.set_ylabel(name)
        ax.set_title(name)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=5.5, loc="best", ncol=2)
        if k >= n - ncols:
            ax.set_xlabel("Время (с)")

    for j in range(n, len(axes_time)):
        axes_time[j].set_visible(False)

    ax_cap = fig.add_subplot(gs[nrows, :])
    ax_cap.axis("off")
    ax_cap.text(
        0.5,
        0.35,
        "Ошибка в % от эталона: было на старте → стало в конце (модуль)",
        ha="center",
        va="center",
        fontsize=10,
    )
    ax_tab = fig.add_subplot(gs[nrows + 1, :])
    ax_tab.axis("off")
    col_labels = ["параметр"] + [lab.replace("старт ", "") for lab in labels]
    cell = []
    print("модуль ошибки |θ̂−trim| / |trim|, %   было → стало")
    for pi, name in zip(REPORT_PARAM_INDICES, REPORT_PARAM_NAMES):
        row = [name]
        bits = []
        for run in runs:
            err = np.asarray(
                run.get("ofk2_d_params_trim", run["ofk2_d_params"]), dtype=float
            )
            p0 = _start_pct(run)
            p1 = _end_pct(err, pi)
            row.append(f"{p0:.0f}→{p1:.1f}")
            bits.append(f"{p0:.0f}→{p1:.1f}")
        cell.append(row)
        print(f"  {name}: " + "  ".join(bits))
    table = ax_tab.table(
        cellText=cell,
        colLabels=col_labels,
        loc="center",
        cellLoc="center",
        bbox=[0.0, 0.05, 1.0, 0.95],
    )
    table.auto_set_font_size(False)
    table.set_fontsize(7)

    fig.suptitle(
        "ОФК-2: разные начальные значения. Сверху — коэффициент во времени, "
        "снизу — было / стало в процентах.",
        fontsize=11,
        y=0.995,
    )
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def _ic_label(run: dict) -> str:
    sc = run.get("ofk2_start_scale")
    if sc is None:
        return f"старт ×{1.0 + float(run.get('coeff_start_err', 0.3)):.2g}"
    return f"старт ×{float(sc):.2g}"


def plot_ofk2_ic_error_three_sigma(runs: list[dict], out_path=None):
    """Сетка: все L*/M*, столбцы — начальная ошибка; Δ и ±3σ."""
    from ..filtering.ofk2_theory import PARAM_NAMES

    path = Path(out_path or "ofk2_ic_error_three_sigma.png")
    n_par = len(PARAM_NAMES)
    n_ic = len(runs)
    fig, axes = plt.subplots(
        n_par,
        n_ic,
        figsize=(max(3.0 * n_ic, 10), 1.55 * n_par),
        sharex=True,
        squeeze=False,
    )
    for j, run in enumerate(runs):
        t = np.asarray(run["ofk2_time"], dtype=float)
        err = np.asarray(
            run.get("ofk2_d_params_trim", run["ofk2_d_params"]), dtype=float
        )
        std = np.asarray(run["ofk2_std"], dtype=float)
        lab = _ic_label(run)
        for i, name in enumerate(PARAM_NAMES):
            ax = axes[i, j]
            band = 3.0 * std[i]
            ax.fill_between(t, -band, band, alpha=0.22, color="mediumpurple")
            ax.plot(t, err[i], color="darkblue", lw=1.0)
            ax.axhline(0.0, color="gray", lw=0.6, ls=":")
            ax.grid(True, alpha=0.3)
            if i == 0:
                ax.set_title(lab, fontsize=10)
            if j == 0:
                ax.set_ylabel(name, fontsize=9)
            if i == n_par - 1:
                ax.set_xlabel("с", fontsize=8)

    fig.suptitle(
        "ОФК-2: ошибка (оценка − балансировка) и полоса ±3σ "
        "при разных начальных значениях",
        fontsize=12,
    )
    plt.tight_layout(rect=(0, 0, 1, 0.97))
    plt.savefig(path, dpi=140)
    plt.close(fig)
    print(f"\nPlot saved to {path}")


def plot_ofk2_rate_compare(runs: list[tuple[str, dict]], out_path=None):
    """Сравнение ОФК-2 при разном dt_ofk2 (один полёт, один старт)."""
    from ..filtering.ofk2_theory import REPORT_PARAM_INDICES, REPORT_PARAM_NAMES

    path = Path(out_path or "ofk2_rate_compare.png")
    n = len(REPORT_PARAM_NAMES)
    ncols = 2
    nrows = int(np.ceil(n / ncols))
    fig, axes = plt.subplots(nrows, ncols, figsize=(11, 2.5 * nrows), sharex=True)
    axes_flat = np.atleast_1d(axes).ravel()
    th_trim = np.asarray(runs[0][1].get("sp_theory_vec_trim", []), dtype=float)

    print("ОФК-2: частота vs |Δ|/|trim| на t_end")
    for ax, pi, name in zip(axes_flat, REPORT_PARAM_INDICES, REPORT_PARAM_NAMES):
        if th_trim.size > pi:
            ax.axhline(th_trim[pi], color="k", lw=1.2, label="эталон trim")
        for lab, run in runs:
            t = np.asarray(run["ofk2_time"], dtype=float)
            ekf = np.asarray(run["ofk2_params"], dtype=float)
            ax.plot(t, ekf[pi], lw=1.3, label=lab)
        ax.set_ylabel(name)
        ax.set_title(name)
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=7, loc="best")
    for j in range(n, len(axes_flat)):
        axes_flat[j].set_visible(False)
    for ax in axes_flat[max(0, n - ncols) : n]:
        ax.set_xlabel("Время (с)")

    for lab, run in runs:
        err = np.asarray(run.get("ofk2_d_params_trim", run["ofk2_d_params"]))
        bits = []
        for i, pi in enumerate(REPORT_PARAM_INDICES):
            den = max(abs(float(th_trim[pi])), 1e-12)
            bits.append(f"{REPORT_PARAM_NAMES[i]}={100*abs(err[pi,-1])/den:.1f}%")
        mae = float(np.mean(np.abs(err[REPORT_PARAM_INDICES, -1])))
        print(f"  {lab}: MAE={mae:.4f}  " + "  ".join(bits))

    fig.suptitle("ОФК-2: один и тот же полёт, разная частота фильтра", fontsize=12)
    fig.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)
    print(f"\nPlot saved to {path}")
