#!/usr/bin/env python3
"""PNG-рисунки для отчёта: структурная схема имитационной модели.

Запуск (окружение с matplotlib)::

    python docs/build_report_figures.py

Результат: ``docs/_report_arch.png`` — «Полная схема математической модели
для имитационного моделирования» в оформлении пояснительной записки.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib import font_manager as fm
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

_HERE = Path(__file__).resolve().parent
ARCH_PNG = _HERE / "_report_arch.png"

# Заливки блоков по функциональным группам (печать в оттенках серого читаема)
FILL = {
    "init": "#eef1f5",
    "plant": "#dce9f5",
    "sensor": "#e8e2f2",
    "bins": "#dff0e6",
    "gnss": "#d9efec",
    "ofk1": "#f7e0dd",
    "ofk2": "#e2ecf7",
    "ref": "#fbf0d9",
    "out": "#f0f0f0",
}
EDGE = "#1b2631"
TXT = "#000000"


def _rc() -> None:
    names = {f.name for f in fm.fontManager.ttflist}
    family = "Times New Roman" if "Times New Roman" in names else "DejaVu Sans"
    plt.rcParams.update(
        {
            "font.family": family,
            "font.size": 11,
            "axes.unicode_minus": False,
            "savefig.facecolor": "white",
        }
    )


def _box(ax, x, y, w, h, text, *, fc="#ffffff", fs=10.5, weight="normal"):
    """Блок схемы; (x, y) — левый нижний угол в координатах 0..100."""
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.0,rounding_size=0.8",
            facecolor=fc,
            edgecolor=EDGE,
            linewidth=1.1,
            mutation_aspect=1.0,
        )
    )
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fs,
        fontweight=weight,
        color=TXT,
        linespacing=1.35,
    )
    return (x, y, w, h)


def _arrow(ax, a, b, *, label=None, dx=0.0, dy=0.0, style="-|>", dashed=False, fs=9.5):
    ax.add_patch(
        FancyArrowPatch(
            a,
            b,
            arrowstyle=style,
            mutation_scale=13,
            linewidth=1.15,
            color=EDGE,
            linestyle="--" if dashed else "-",
            shrinkA=0,
            shrinkB=0,
        )
    )
    if label:
        ax.text(
            (a[0] + b[0]) / 2 + dx,
            (a[1] + b[1]) / 2 + dy,
            label,
            ha="center",
            va="center",
            fontsize=fs,
            color="#1b2631",
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"),
        )


def _elbow(ax, pts, *, label=None, dx=0.0, dy=0.0, dashed=False, fs=9.5):
    """Ломаная со стрелкой на последнем звене."""
    for i in range(len(pts) - 2):
        ax.add_patch(
            FancyArrowPatch(
                pts[i],
                pts[i + 1],
                arrowstyle="-",
                linewidth=1.15,
                color=EDGE,
                linestyle="--" if dashed else "-",
                shrinkA=0,
                shrinkB=0,
            )
        )
    _arrow(ax, pts[-2], pts[-1], dashed=dashed)
    if label:
        mx = sum(p[0] for p in pts) / len(pts)
        my = sum(p[1] for p in pts) / len(pts)
        ax.text(
            mx + dx,
            my + dy,
            label,
            ha="center",
            va="center",
            fontsize=fs,
            color="#1b2631",
            bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"),
        )


def build_architecture(out_path: Path = ARCH_PNG) -> Path:
    _rc()
    fig = plt.figure(figsize=(13.2, 9.2))
    ax = fig.add_axes([0.01, 0.01, 0.98, 0.98])
    ax.set_xlim(0, 100)
    ax.set_ylim(13, 100)
    ax.axis("off")

    # ---------------- уровень 0: инициализация -----------------------
    _box(
        ax,
        6, 90, 88, 8,
        "Инициализация и балансировка горизонтального полёта: $H_0$ = 500 м, $V_0$ = 80 м/с,\n"
        "начальная выставка БИНС, шаг интегрирования $\\Delta t$ = 1 мс, время прогона $t$ = 60 с",
        fc=FILL["init"],
        fs=10.5,
    )

    # ---------------- уровень 1: объект, датчики, БИНС ---------------
    a = _box(
        ax, 3, 73, 27, 12,
        "Модель пространственного\nдвижения самолёта (FX1)\nи автопилот, метод Рунге—Кутты\n4-го порядка, 1000 Гц",
        fc=FILL["plant"],
    )
    b = _box(
        ax, 36.5, 73, 27, 12,
        "Инерциальные датчики\nДУС и ДЛУ: смещение нуля\n0,5 °/ч и 5·10$^{-4}$ м/с$^2$,\nбелый шум",
        fc=FILL["sensor"],
    )
    c = _box(
        ax, 70, 73, 27, 12,
        "БИНС: механизация,\nинтегрирование ориентации\nи счисление координат,\n1000 Гц",
        fc=FILL["bins"],
    )

    _arrow(ax, (30, 79), (36.5, 79), label="$\\omega$, $a$\n(идеальные)", dy=6.0)
    _arrow(ax, (63.5, 79), (70, 79), label="$\\omega_m$, $a_m$", dy=4.0)

    # вертикальная связь: инициализация → объект
    _arrow(ax, (16.5, 90), (16.5, 85))

    # ---------------- уровень 2: СНС, ОФК-1, обратная связь ----------
    d = _box(
        ax, 3, 55, 27, 11,
        "Приёмник СНС, 10 Гц:\n$\\sigma_{\\varphi,\\lambda}$ = 5·10$^{-6}$ рад, $\\sigma_h$ = 1 м,\n$\\sigma_V$ = 0,2 м/с",
        fc=FILL["gnss"],
    )
    e = _box(
        ax, 36.5, 55, 27, 11,
        "ОФК-1 — фильтр Калмана\nошибок навигации, 15 состояний,\nтакт 10 Гц; невязка\n$z = np_{\\mathrm{БИНС}} - np_{\\mathrm{СНС}}$",
        fc=FILL["ofk1"],
    )
    f = _box(
        ax, 70, 55, 27, 11,
        "Обратная связь: коррекция\nвектора БИНС и обнуление\nвектора ошибок",
        fc=FILL["ofk1"],
    )

    _arrow(ax, (16.5, 73), (16.5, 66), label="истинные $\\varphi$, $\\lambda$, $h$, $V$", dy=0.0)
    _arrow(ax, (30, 60.5), (36.5, 60.5), label="$np_{\\mathrm{СНС}}$", dy=2.6)
    _elbow(
        ax,
        [(83.5, 73), (83.5, 70.6), (50, 70.6), (50, 66)],
        label="$np_{\\mathrm{БИНС}}$",
        dx=22.0,
        dy=1.2,
    )
    _arrow(ax, (63.5, 60.5), (70, 60.5), label="оценка\nошибок", dy=3.6)
    _elbow(
        ax,
        [(97, 60.5), (98.6, 60.5), (98.6, 79), (97, 79)],
        label="коррекция",
        dx=-4.2,
        dy=0.0,
    )

    # ---------------- уровень 3: БНК, ОФК-2, теория ------------------
    g = _box(
        ax, 3, 36, 27, 11,
        "Скорректированное\nнавигационное решение:\n$\\varphi$, $\\lambda$, $h$, $V_N$, $V_E$, $V_h$, углы",
        fc=FILL["bins"],
    )
    h = _box(
        ax, 36.5, 36, 27, 11,
        "ОФК-2 — идентификация\nкоэффициентов короткопериодического\nдвижения $L^*$, $M^*$, такт 50 Гц",
        fc=FILL["ofk2"],
    )
    i_box = _box(
        ax, 70, 36, 27, 11,
        "Теоретические $L^*$, $M^*$:\nлинеаризация модели FX1\nв точке балансировки",
        fc=FILL["ref"],
    )

    _elbow(ax, [(50, 55), (50, 51.3), (16.5, 51.3), (16.5, 47)], label="", dx=0, dy=0)
    ax.text(
        23.0, 52.2, "решение после ОФК-1", ha="center", va="bottom", fontsize=9.5,
        bbox=dict(boxstyle="round,pad=0.18", fc="white", ec="none"),
    )
    _arrow(ax, (30, 41.5), (36.5, 41.5), label="$\\alpha$, $V$, $\\theta$", dy=3.2)
    _elbow(
        ax,
        [(44, 73), (44, 68.2), (33.6, 68.2), (33.6, 44.5), (36.5, 44.5)],
        label="$q$, $a_z$ с ДУС и ДЛУ,  $\\delta_в$",
        dx=1.7,
        dy=8.0,
    )
    _arrow(ax, (70, 41.5), (63.5, 41.5), label="эталон $L^*$, $M^*$", dy=7.0)
    _elbow(ax, [(16.5, 73), (1.4, 73), (1.4, 24), (30, 24)], dashed=True)
    ax.text(
        2.6, 30.0, "истинное состояние ЛА —\nэталон для оценки ошибок",
        ha="left", va="center", fontsize=9.5, rotation=0,
        bbox=dict(boxstyle="round,pad=0.2", fc="white", ec="none"),
    )

    # ---------------- уровень 4: результаты --------------------------
    _box(
        ax, 30, 17, 55, 12,
        "Анализ результатов моделирования:\n"
        "ошибки счисления БИНС и ошибки после ОФК-1 в сравнении с полосой $\\pm 3\\sqrt{P_{ii}}$;\n"
        "сходимость оценок $L^*$, $M^*$ и отклонение $\\Delta$ = оценка $-$ теория",
        fc=FILL["out"],
        fs=10.5,
    )
    _arrow(ax, (50, 36), (50, 29))
    _elbow(ax, [(83.5, 36), (83.5, 32.5), (72, 32.5), (72, 29)])

    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path




TIMING_PNG = _HERE / "_report_timing.png"


def build_timing(out_path: Path = TIMING_PNG) -> Path:
    """Диаграмма тактов подсистем и профиль отклонения руля высоты."""
    import numpy as np

    _rc()
    fig, (ax_t, ax_z) = plt.subplots(
        2, 1, figsize=(11.0, 5.6), gridspec_kw={"height_ratios": [1.0, 1.25]}
    )
    fig.subplots_adjust(hspace=0.55, left=0.14, right=0.98, top=0.93, bottom=0.12)

    # --- (а) профиль манёвра на всём прогоне --------------------------
    t = np.linspace(0.0, 60.0, 6001)
    de = np.zeros_like(t)
    de[(t >= 10.0) & (t < 12.5)] = 5.0
    de[(t >= 12.5) & (t < 15.0)] = -5.0
    ax_t.plot(t, de, color="#1b2631", linewidth=1.4)
    ax_t.axvspan(10.0, 15.0, color="#dce9f5", zorder=0)
    ax_t.set_xlim(0, 60)
    ax_t.set_ylim(-7.5, 7.5)
    ax_t.set_xlabel("Время, с")
    ax_t.set_ylabel("$\\delta_в$, град")
    ax_t.set_title("а) профиль отклонения руля высоты (doublet $\\pm5^{\\circ}$, 10…15 с)", fontsize=11)
    ax_t.grid(alpha=0.3)

    # --- (б) такты подсистем на интервале 0…0,1 с ---------------------
    lanes = [
        ("FX1 + механизация БИНС, 1000 Гц", 0.001, "#1f4e79"),
        ("ОФК-2, 50 Гц", 0.02, "#1a5276"),
        ("Автопилот, 100 Гц", 0.01, "#7d6608"),
        ("ГНСС + ОФК-1, 10 Гц", 0.1, "#922b21"),
    ]
    t_max = 0.1
    for row, (name, period, color) in enumerate(lanes):
        y = len(lanes) - 1 - row
        ax_z.hlines(y, 0, t_max, color="#b3b6b7", linewidth=0.8, zorder=1)
        ticks = np.arange(period, t_max + 1e-9, period)
        ax_z.vlines(ticks, y - 0.28, y + 0.28, color=color, linewidth=1.3, zorder=2)
        ax_z.text(-0.004, y, name, ha="right", va="center", fontsize=10)
    ax_z.set_xlim(0, t_max)
    ax_z.set_ylim(-0.7, len(lanes) - 0.3)
    ax_z.set_yticks([])
    ax_z.set_xlabel("Время внутри одного такта ГНСС, с")
    ax_z.set_title("б) такты подсистем на интервале 0…0,1 с", fontsize=11)
    for side in ("top", "right", "left"):
        ax_z.spines[side].set_visible(False)

    fig.savefig(out_path, dpi=200, bbox_inches="tight")
    plt.close(fig)
    return out_path


if __name__ == "__main__":
    print(build_architecture())
    print(build_timing())
