"""
3D-визуализация полёта самолёта по результатам ``run_simulation``.

- ``plot_flight_3d``      — траектория в 3D с силуэтами самолёта и выделенным манёвром;
- ``plot_maneuvers_3d``   — сравнение траекторий при разных манёврах (полосы со сдвигом);
- ``animate_flight_3d``   — анимация полёта (GIF).

Высота по вертикальной оси растянута: за минуту полёта самолёт проходит ~5 км,
а высота меняется на десятки метров, без растяжения профиль не виден.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import animation
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

A_EARTH = 6378245.0


# ---------------------------------------------------------------------------
# Подготовка данных
# ---------------------------------------------------------------------------
def _track(data: dict) -> dict:
    """Истинная траектория в локальных осях: N, E (м) от точки старта, H (м), углы."""
    t = np.asarray(data["time"], float)
    fi, lam = np.asarray(data["true_fi"], float), np.asarray(data["true_lam"], float)
    north = (fi - fi[0]) * A_EARTH
    east = (lam - lam[0]) * A_EARTH * np.cos(fi[0])
    h = np.asarray(data["true_h"], float)
    psi = np.arctan2(np.asarray(data["true_ve"], float), np.asarray(data["true_vn"], float))
    # тангаж ЛА регистрируется на частоте ОФК-2 (ofk2_true_aq[3]) — интерполируем на сетку СНС
    pitch = np.interp(t, data["ofk2_time"], data["ofk2_true_aq"][3])
    de = np.asarray(data["u"][1], float) - float(data["u0"][1])
    return {"t": t, "n": north, "e": east, "h": h, "psi": psi, "pitch": pitch, "de": de}


def _aircraft_polys(n, e, h, psi, pitch, size, zscale):
    """Силуэт самолёта (фюзеляж-крыло-оперение) в точке (n, e, h) с курсом psi и тангажом pitch."""
    # локальные оси: x — вперёд, y — вправо, z — вверх; размеры в долях size
    wing = np.array([[0.15, 0, 0], [-0.15, -0.55, 0], [-0.3, -0.55, 0], [-0.1, 0, 0],
                     [-0.3, 0.55, 0], [-0.15, 0.55, 0]])
    body = np.array([[0.5, 0, 0], [-0.5, -0.04, 0], [-0.5, 0.04, 0]])
    tail = np.array([[-0.35, 0, 0], [-0.5, 0, 0.18], [-0.5, 0, 0]])
    stab = np.array([[-0.38, 0, 0], [-0.5, -0.2, 0], [-0.5, 0.2, 0]])
    cp, sp, cy, sy = np.cos(pitch), np.sin(pitch), np.cos(psi), np.sin(psi)
    rot_pitch = np.array([[cp, 0, -sp], [0, 1, 0], [sp, 0, cp]])
    out = []
    for poly in (wing, body, tail, stab):
        p = poly @ rot_pitch.T * size
        dn = p[:, 0] * cy - p[:, 1] * sy
        de = p[:, 0] * sy + p[:, 1] * cy
        dz = p[:, 2] * zscale
        out.append(list(zip(n + dn, e + de, h + dz)))
    return out


def _style_axes(ax, zlabel="H, м"):
    ax.set_xlabel("север N, м", labelpad=8)
    ax.set_ylabel("восток E, м", labelpad=8)
    ax.set_zlabel(zlabel, labelpad=6)
    ax.xaxis.pane.set_alpha(0.0)
    ax.yaxis.pane.set_alpha(0.0)


# ---------------------------------------------------------------------------
# 3D-траектория одного полёта
# ---------------------------------------------------------------------------
def plot_flight_3d(data: dict, out_path, *, t_max: float = 80.0, maneuver=(10.0, 15.0), every_s: float = 5.0):
    """Траектория в 3D: участок манёвра выделен цветом, силуэты самолёта через ``every_s`` секунд."""
    tr = _track(data)
    m = tr["t"] <= t_max
    t, n, e, h = tr["t"][m], tr["n"][m], tr["e"][m], tr["h"][m]
    span_e = max(600.0, (n.max() - n.min()) * 0.15)
    zscale = 1.0

    fig = plt.figure(figsize=(11, 6.5))
    ax = fig.add_subplot(111, projection="3d")
    man = (t >= maneuver[0]) & (t <= maneuver[1] + 10.0)
    ax.plot(n, e, h, color="#1f5fa8", lw=1.8, label="траектория")
    ax.plot(n[man], e[man], h[man], color="#c0392b", lw=3.0, label="манёвр и переходный процесс")
    # проекция на «землю» для глубины
    h_floor = h.min() - 0.4 * (h.max() - h.min() + 5)
    ax.plot(n, e, np.full_like(h, h_floor), color="gray", lw=1.0, alpha=0.5, ls="--", label="проекция на горизонт")
    size = (n.max() - n.min()) * 0.03
    for ti in np.arange(0.0, t_max + 1e-9, every_s):
        k = int(np.argmin(np.abs(t - ti)))
        for poly in _aircraft_polys(n[k], e[k], h[k], tr["psi"][m][k], tr["pitch"][m][k], size, zscale * 0.03):
            ax.add_collection3d(Poly3DCollection([poly], facecolor="#34495e", edgecolor="k", lw=0.3, alpha=0.9))
    ax.set_ylim(-span_e, span_e)
    ax.set_box_aspect((3.0, 1.0, 0.8))
    _style_axes(ax)
    ax.view_init(elev=18, azim=-60)
    ax.legend(loc="upper left", fontsize=9)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Сравнение манёвров
# ---------------------------------------------------------------------------
def plot_maneuvers_3d(runs: list[tuple[str, dict]], out_path, *, t_max: float = 80.0, lane_m: float = 600.0):
    """Траектории для нескольких манёвров на одном рисунке; каждая смещена по E на ``lane_m`` для наглядности."""
    fig = plt.figure(figsize=(11, 7))
    ax = fig.add_subplot(111, projection="3d")
    colors = plt.cm.tab10(np.linspace(0, 1, 10))
    for i, (label, data) in enumerate(runs):
        tr = _track(data)
        m = tr["t"] <= t_max
        lane = i * lane_m
        ax.plot(tr["n"][m], tr["e"][m] + lane, tr["h"][m], color=colors[i % 10], lw=1.8, label=label)
    ax.set_box_aspect((3.0, 1.4, 0.8))
    _style_axes(ax)
    ax.set_yticks([])
    ax.set_ylabel("манёвры (полосы со сдвигом)", labelpad=4)
    ax.view_init(elev=16, azim=-58)
    ax.legend(loc="upper left", fontsize=8)
    path = Path(out_path)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)
    return path


# ---------------------------------------------------------------------------
# Анимация
# ---------------------------------------------------------------------------
def animate_flight_3d(data: dict, out_path, *, t_max: float = 60.0, fps: int = 15, speedup: float = 4.0):
    """GIF: самолёт летит по траектории; справа — руль высоты и высота во времени."""
    tr = _track(data)
    m = tr["t"] <= t_max
    t, n, e, h, de = tr["t"][m], tr["n"][m], tr["e"][m], tr["h"][m], tr["de"][m]
    psi, pitch = tr["psi"][m], tr["pitch"][m]
    span_e = max(600.0, (n.max() - n.min()) * 0.15)
    size = (n.max() - n.min()) * 0.07
    frames = np.arange(0.0, t_max, speedup / fps)

    fig = plt.figure(figsize=(12.5, 5.6))
    gs = fig.add_gridspec(2, 2, width_ratios=[1.7, 1.0], wspace=0.15)
    ax = fig.add_subplot(gs[:, 0], projection="3d")
    ax2 = fig.add_subplot(gs[0, 1])
    ax3 = fig.add_subplot(gs[1, 1], sharex=ax2)
    ax.plot(n, e, h, color="#b9c9e8", lw=1.0)
    trail, = ax.plot([], [], [], color="#1f5fa8", lw=2.0)
    ax.set_xlim(n.min(), n.max()); ax.set_ylim(-span_e, span_e); ax.set_zlim(h.min() - 3, h.max() + 3)
    ax.set_box_aspect((3.0, 1.0, 0.9))
    _style_axes(ax)
    ax.set_yticks([-span_e, 0, span_e])
    ax.zaxis.set_major_locator(plt.MaxNLocator(4))
    ax.view_init(elev=22, azim=-62)
    ax2.plot(t, de, color="#1f5fa8"); ax2.set_ylabel("Δδв, °"); ax2.grid(alpha=0.3)
    ax3.plot(t, h, color="#1f5fa8"); ax3.set_ylabel("H, м"); ax3.set_xlabel("t, с"); ax3.grid(alpha=0.3)
    cur2 = ax2.axvline(0, color="#c0392b"); cur3 = ax3.axvline(0, color="#c0392b")
    title = fig.suptitle("")
    polys = []

    def update(tf):
        k = int(np.argmin(np.abs(t - tf)))
        trail.set_data(n[: k + 1], e[: k + 1])
        trail.set_3d_properties(h[: k + 1])
        for p in polys:
            p.remove()
        polys.clear()
        for poly in _aircraft_polys(n[k], e[k], h[k], psi[k], pitch[k], size, 0.06):
            pc = Poly3DCollection([poly], facecolor="#34495e", edgecolor="k", lw=0.3)
            ax.add_collection3d(pc)
            polys.append(pc)
        cur2.set_xdata([t[k], t[k]]); cur3.set_xdata([t[k], t[k]])
        title.set_text(f"t = {t[k]:5.1f} с   H = {h[k]:6.1f} м")
        return [trail, cur2, cur3, title, *polys]

    anim = animation.FuncAnimation(fig, update, frames=frames, interval=1000 / fps, blit=False)
    path = Path(out_path)
    anim.save(path, writer=animation.PillowWriter(fps=fps))
    plt.close(fig)
    return path
