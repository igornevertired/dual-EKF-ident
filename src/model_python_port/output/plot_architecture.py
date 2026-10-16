"""Схемы контура БИНС / ГНСС / ОФК-1 / ОФК-2."""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Ellipse, FancyArrowPatch, FancyBboxPatch


def _box(ax, xy, w, h, text, *, fontsize=8.5):
    x, y = xy
    p = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.015,rounding_size=0.02",
        facecolor="white",
        edgecolor="black",
        linewidth=1.1,
    )
    ax.add_patch(p)
    ax.text(
        x + w / 2,
        y + h / 2,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        wrap=True,
    )
    return p


def _arrow(ax, start, end, text="", *, text_off=(0.0, 0.08), ls="-"):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=12,
            linewidth=1.3,
            color="#2b6cb0",
            linestyle=ls,
        )
    )
    if text:
        mx = 0.5 * (start[0] + end[0]) + text_off[0]
        my = 0.5 * (start[1] + end[1]) + text_off[1]
        ax.text(mx, my, text, ha="center", va="center", fontsize=7.2, color="#2b6cb0")


def plot_ofk1_scheme(out_path: Path | str | None = None) -> Path:
    path = Path(out_path or "src/plots/ofk1_scheme.png")
    fig, ax = plt.subplots(figsize=(12.5, 7.2))
    ax.set_xlim(0, 12.5)
    ax.set_ylim(0, 7.2)
    ax.axis("off")
    ax.set_title(
        "ОФК-1: БИНС по сырым ДУС/ДЛУ, оценки — потребителям",
        fontsize=13,
        pad=12,
    )
    _box(ax, (0.4, 2.6), 3.2, 2.2, "БИНС  1 кГц\nсырые ДУС, ДЛУ\nNP, $C_{bn}$")
    _box(ax, (4.6, 4.6), 3.2, 1.8, "СНС (ГНСС)\n10 Гц")
    ax.add_patch(Circle((6.2, 3.55), 0.28, fill=False, linewidth=1.2))
    ax.text(6.2, 3.55, "−", ha="center", va="center", fontsize=14)
    _box(
        ax,
        (8.6, 2.6),
        3.4,
        2.2,
        "ОФК-1  10 Гц\n15 оценок ошибок\n6 измерений",
    )
    _box(ax, (8.6, 0.45), 3.4, 1.5, "потребители\nОФК-2, САУ, индикация")
    _arrow(ax, (3.6, 3.7), (5.9, 3.7), r"$Y_{\mathrm{И}}$", text_off=(0.0, 0.18))
    _arrow(ax, (6.2, 4.6), (6.2, 3.85), r"$Y_{\mathrm{C}}$", text_off=(0.55, 0.0))
    _arrow(ax, (6.5, 3.55), (8.6, 3.55), r"$Z=Y_{\mathrm{И}}-Y_{\mathrm{C}}$", text_off=(0.0, 0.22))
    _arrow(ax, (10.3, 2.6), (10.3, 1.95), r"$\hat x$ (не в БИНС)", text_off=(1.15, 0.0))
    ax.text(
        6.25,
        0.28,
        r"$Y_{\mathrm{И}},Y_{\mathrm{C}}=[\varphi,\lambda,h,V_N,V_E,V_h]$"
        r"   $Z=[\delta\varphi,\delta\lambda,\delta V_N,\delta V_E,\delta V_h,\delta h]$"
        "\nБИНС считает NP и $C_{bn}$ сам; смещения в нём не оцениваются."
        "\nпотребителю: $NP-\\hat\\delta$,  $q=\\omega_m-\\widehat{\\Delta\\omega}$,"
        r"  $C_{bn}\leftarrow(I-[\hat\phi\times])C_{bn}$,  $a_m-\widehat{\Delta a}$",
        ha="center",
        va="bottom",
        fontsize=8,
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_ofk_full_scheme(out_path: Path | str | None = None) -> Path:
    path = Path(out_path or "src/plots/ofk_full_scheme.png")
    fig, ax = plt.subplots(figsize=(14.2, 8.6))
    ax.set_xlim(0, 14.2)
    ax.set_ylim(0, 8.6)
    ax.axis("off")
    ax.set_title("Полный контур: FX1 + БИНС + ГНСС + ОФК-1 + ОФК-2", fontsize=13, pad=10)

    _box(ax, (0.3, 6.15), 3.15, 1.7, "FX1  истина  1 кГц\nсостояние ЛА $x$ (25)\nидеальные ДУС и ДЛУ")
    _box(ax, (0.3, 4.15), 3.15, 1.35, "Автопилот  100 Гц\n+ doublet руля $\\pm5^\\circ$")
    _box(ax, (4.0, 6.15), 3.3, 1.7, "Ошибки датчиков\nмасштаб, перекос,\nbias, белый шум")
    _box(ax, (8.0, 6.15), 5.7, 1.7, "БИНС  1 кГц  без ОФК-1\nсырые ДУС, ДЛУ → $q$, $C_{bn}$, NP\nNP $=[V_N,V_h,V_E,h,\\varphi,\\lambda]$")
    _box(ax, (4.0, 3.85), 3.3, 1.45, "СНС / ГНСС  10 Гц\nистина + шум")
    ax.add_patch(Circle((7.0, 3.05), 0.26, fill=False, linewidth=1.2))
    ax.text(7.0, 3.05, "−", ha="center", va="center", fontsize=14)
    _box(
        ax,
        (8.0, 3.55),
        5.7,
        1.7,
        "ОФК-1  10 Гц\n15 оценок ошибок БИНС\nв механизацию не пишет",
    )
    _box(
        ax,
        (0.3, 0.35),
        13.4,
        2.35,
        "ОФК-2  10 Гц  (как ОФК-1)   потребитель, на полёт и БИНС не влияет\n"
        r"состояние: $L_*,M_*,X_*,\Theta_*$ и $\delta\alpha,\delta q,\delta V,\delta\theta$"
        "\n"
        r"прогноз: интеграл $\dot\alpha,\dot q,\dot V,\dot\theta$   "
        r"коррекция $Z=[\delta\alpha,\delta q,\delta V,\delta\theta]$ с ОФК-1"
        "\n"
        r"$\theta$: $\sin\theta=V_y/\sqrt{V_x^2+V_z^2}$ из NP ОФК-1;  без $X_q,M_V$"
        "\n"
        r"вход: $\alpha,V$ из $NP-\hat\delta$ и $C_{bn}$;  "
        r"$q=\omega_z-\widehat{\Delta\omega}_z$;  $\delta_e$ с привода FX1",
        fontsize=8.2,
    )

    _arrow(ax, (1.9, 6.15), (1.9, 5.5), r"$u$", text_off=(-0.28, 0.0))
    _arrow(ax, (2.4, 6.15), (2.4, 5.5), r"$x$", text_off=(0.28, 0.0))
    _arrow(ax, (3.45, 7.0), (4.0, 7.0), "идеал ДУС, ДЛУ", text_off=(0.0, 0.18))
    _arrow(ax, (7.3, 7.0), (8.0, 7.0), r"приборы $w,a$", text_off=(0.0, 0.18))
    _arrow(ax, (9.5, 6.15), (9.5, 5.25), r"$Y_{\mathrm{И}}$ из NP БИНС", text_off=(1.35, 0.0))
    _arrow(ax, (5.65, 3.85), (6.72, 3.2), r"$Y_{\mathrm{C}}$", text_off=(-0.55, -0.05))
    _arrow(ax, (7.28, 3.05), (8.0, 3.9), r"$Z=Y_{\mathrm{И}}-Y_{\mathrm{C}}$", text_off=(0.35, -0.35))
    _arrow(
        ax,
        (10.85, 3.55),
        (10.85, 2.7),
        r"потребителю: $NP-\hat\delta$, $\omega-\widehat{\Delta\omega}$,"
        "\n"
        r"$C_{bn}$ после $\hat\phi$, $a-\widehat{\Delta a}$",
        text_off=(2.15, 0.05),
    )
    _arrow(ax, (1.5, 4.15), (1.5, 2.7), r"$\delta_e$ из привода FX1", text_off=(1.15, 0.0), ls="--")

    ax.text(
        7.1,
        0.08,
        "Два разных $q$: в БИНС — кватернион; в ОФК-2 — угловая скорость тангажа. "
        "ОФК-1 в NP и $C_{bn}$ БИНС не пишет.",
        ha="center",
        fontsize=7.5,
        color="#555555",
    )
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_ofk_advisor_scheme(out_path: Path | str | None = None) -> Path:
    path = Path(out_path or "src/plots/ofk_advisor_scheme.png")
    fig, ax = plt.subplots(figsize=(13.6, 8.4))
    ax.set_xlim(0, 13.6)
    ax.set_ylim(0, 8.4)
    ax.axis("off")
    ax.set_title(
        "Контур БИНС / ГНСС / ОФК-1 / ОФК-2 (как на схеме с научным руководителем)",
        fontsize=12.5,
        pad=10,
    )
    _box(ax, (0.25, 5.55), 2.35, 2.05, "ЛА\nFX1  1 кГц\nсостояние $x$")
    _box(ax, (3.0, 6.55), 2.5, 1.15, "ошибки\nДУС / ДЛУ")
    _box(ax, (5.9, 5.85), 3.35, 1.85, "БИНС  1 кГц\nавтономен\n$q$, $C_{bn}$, NP")
    _box(ax, (5.9, 3.55), 3.35, 1.55, "ГНСС  10 Гц\nистина + шум")
    ax.add_patch(Circle((10.15, 5.35), 0.26, fill=False, linewidth=1.2))
    ax.text(10.15, 5.35, "−", ha="center", va="center", fontsize=14)
    _box(ax, (10.6, 5.55), 2.7, 1.85, "ОФК-1  10 Гц\n15 ошибок БИНС\nв БИНС не пишет")
    _box(ax, (10.6, 3.15), 2.7, 1.65, "ОФК-2  10 Гц\nидентификация\n$L_*,M_*,X_*$")

    ell = Ellipse(
        (6.7, 1.35),
        12.4,
        2.35,
        fill=False,
        linewidth=1.15,
        edgecolor="black",
    )
    ax.add_patch(ell)
    ax.text(
        6.7,
        1.95,
        "ОФК-2. Линейная продольная модель ($\\alpha,q,V,\\theta$)",
        ha="center",
        fontsize=8.5,
    )
    ax.text(
        6.7,
        1.2,
        r"$\dot\alpha = L_\alpha\delta\alpha + L_q\delta q + L_{\delta e}\delta\delta_e + L_V\delta V + L_\theta\delta\theta$"
        "\n"
        r"$\dot q = M_\alpha\delta\alpha + M_q\delta q + M_{\delta e}\delta\delta_e + M_V\delta V + M_\theta\delta\theta + M_{\dot\delta e}\dot{\delta}_e$"
        "\n"
        r"$\dot V = X_\alpha\delta\alpha + X_{\delta e}\delta\delta_e + X_V\delta V + X_\theta\delta\theta$"
        "\n"
        r"$\dot\theta = \Theta_\alpha\delta\alpha + \Theta_{\delta e}\delta\delta_e + \Theta_V\delta V + \Theta_\theta\delta\theta$",
        ha="center",
        va="center",
        fontsize=8.3,
    )
    ax.text(
        6.7,
        0.38,
        r"прогноз: интеграл ДУ → $\alpha,q,V,\theta$   "
        r"коррекция $Z=[\alpha,q,V,\theta]$ с ОФК-1   "
        r"оценка: $L_*,M_*,X_*,\Theta_*$",
        ha="center",
        fontsize=7.6,
        color="#333333",
    )

    _arrow(ax, (2.6, 7.1), (3.0, 7.1), r"$\omega,a$ идеал", text_off=(0.0, 0.16))
    _arrow(ax, (5.5, 7.1), (5.9, 7.1), r"$\omega_m,a_m$", text_off=(0.0, 0.16))
    _arrow(ax, (7.55, 5.85), (9.88, 5.45), r"$Y_{\mathrm{И}}=NP$", text_off=(-0.2, 0.22))
    _arrow(ax, (9.25, 4.35), (9.88, 5.15), r"$Y_{\mathrm{C}}$", text_off=(-0.55, 0.05))
    _arrow(ax, (10.42, 5.35), (10.6, 6.35), r"$Z=$ БИНС − ГНСС", text_off=(0.2, 0.22))
    _arrow(
        ax,
        (11.95, 5.55),
        (11.95, 4.8),
        r"$NP-\hat\delta$, $\omega-\widehat{\Delta\omega}$,"
        "\n"
        r"$C_{bn}$ после $\hat\phi$, $a-\widehat{\Delta a}$",
        text_off=(1.85, 0.0),
    )
    _arrow(ax, (1.4, 5.55), (5.9, 4.35), r"$\varphi,\lambda,h,V_N,V_E,V_h$", text_off=(-0.9, -0.15))

    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def _panel(ax, xy, w, h, title, lines, *, title_fs=9.5, body_fs=8.0, fc="#ffffff"):
    """Рамка с заголовком сверху и текстом слева (удобно читать формулы)."""
    x, y = xy
    ax.add_patch(
        FancyBboxPatch(
            (x, y),
            w,
            h,
            boxstyle="round,pad=0.012,rounding_size=0.025",
            facecolor=fc,
            edgecolor="#1a202c",
            linewidth=1.15,
        )
    )
    ax.text(
        x + 0.12,
        y + h - 0.22,
        title,
        ha="left",
        va="top",
        fontsize=title_fs,
        fontweight="bold",
        color="#1a202c",
    )
    body = "\n".join(lines)
    ax.text(
        x + 0.12,
        y + h - 0.48,
        body,
        ha="left",
        va="top",
        fontsize=body_fs,
        color="#2d3748",
        linespacing=1.35,
    )


def plot_ofk2_scheme(out_path: Path | str | None = None) -> Path:
    """Минималистичная схема ОФК-2: поток и формулы, мало текста."""
    path = Path(out_path or "src/plots/ofk2_scheme.png")
    fig, ax = plt.subplots(figsize=(14.0, 7.6))
    ax.set_xlim(0, 14.0)
    ax.set_ylim(0, 7.6)
    ax.axis("off")

    def box(xy, w, h, fc="#fff"):
        ax.add_patch(
            FancyBboxPatch(
                (xy[0], xy[1]),
                w,
                h,
                boxstyle="round,pad=0.02,rounding_size=0.04",
                facecolor=fc,
                edgecolor="#2d3748",
                linewidth=1.4,
            )
        )

    def mid(xy, w, h):
        return xy[0] + w / 2, xy[1] + h / 2

    # источники
    box((0.35, 5.35), 2.35, 1.7, "#edf2f7")
    ax.text(1.525, 6.55, "ОФК-1", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(
        1.525,
        5.95,
        r"$NP-\hat\delta$"
        "\n"
        r"$\omega-\widehat{\Delta\omega}$"
        "\n"
        r"$a-\widehat{\Delta a}$",
        ha="center",
        va="center",
        fontsize=10,
        linespacing=1.4,
    )

    box((0.35, 3.35), 2.35, 1.5, "#edf2f7")
    ax.text(1.525, 4.35, "БИНС", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(1.525, 3.75, r"$C_{bn}$", ha="center", va="center", fontsize=14)

    box((0.35, 1.35), 2.35, 1.5, "#edf2f7")
    ax.text(1.525, 2.35, "FX1", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(1.525, 1.75, r"$\delta_e$", ha="center", va="center", fontsize=14)

    # сборка
    box((3.35, 2.55), 3.4, 3.9, "#ebf8ff")
    ax.text(5.05, 6.05, "сигналы", ha="center", va="center", fontsize=12, fontweight="bold")
    ax.text(
        5.05,
        4.55,
        r"$\alpha,\,V$"
        "\n"
        r"из $NP,\,C_{bn}$"
        "\n\n"
        r"$q=\omega_z$"
        "\n\n"
        r"$\delta\delta_e=\delta_e-\delta_{e0}$",
        ha="center",
        va="center",
        fontsize=11,
        linespacing=1.25,
    )

    # Z
    box((7.35, 3.55), 1.7, 1.9, "#faf5ff")
    ax.text(8.2, 4.85, r"$Z$", ha="center", va="center", fontsize=16, fontweight="bold")
    ax.text(
        8.2,
        4.15,
        r"$[\alpha$"
        "\n"
        r"$q$"
        "\n"
        r"$V$"
        "\n"
        r"$\theta]$",
        ha="center",
        va="center",
        fontsize=12,
        linespacing=1.2,
    )

    # EKF
    box((9.65, 2.55), 4.0, 3.9, "#fff5f5")
    ax.text(11.65, 6.05, "ОФК-2  ·  EKF  ·  10 Гц", ha="center", va="center", fontsize=11, fontweight="bold")
    ax.text(
        11.65,
        4.85,
        "прогноз:  ∫ ДУ",
        ha="center",
        va="center",
        fontsize=11,
    )
    ax.text(
        11.65,
        4.25,
        r"коррекция:  $Z-\hat Z$",
        ha="center",
        va="center",
        fontsize=11,
    )
    ax.text(
        11.65,
        3.35,
        r"$\widehat{L}_*,\;\widehat{M}_*,\;\widehat{X}_*,\;\widehat{\Theta}_*$",
        ha="center",
        va="center",
        fontsize=13,
        fontweight="bold",
    )

    # стрелки источников → сборка
    _arrow(ax, (2.7, 6.2), (3.35, 5.5))
    _arrow(ax, (2.7, 4.1), (3.35, 4.5))
    _arrow(ax, (2.7, 2.1), (3.35, 3.4))
    _arrow(ax, (6.75, 4.5), (7.35, 4.5))
    _arrow(ax, (9.05, 4.5), (9.65, 4.5))

    # модель внизу
    box((0.35, 0.25), 13.3, 0.95, "#fffff0")
    ax.text(
        7.0,
        0.72,
        r"$\dot\alpha,\dot q,\dot V,\dot\theta$"
        r"      $Z=[\delta\alpha,\,\delta q,\,\delta V,\,\delta\theta]$"
        r"      $\theta$: $\sin\theta=V_y/\sqrt{V_x^2+V_z^2}$ с ОФК-1"
        r"      без $X_q,M_V$",
        ha="center",
        va="center",
        fontsize=12,
    )

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return path


def plot_all_architecture(out_dir: Path | str | None = None) -> list[Path]:
    base = Path(out_dir or "src/plots")
    paths = [
        plot_ofk1_scheme(base / "ofk1_scheme.png"),
        plot_ofk_full_scheme(base / "ofk_full_scheme.png"),
        plot_ofk_advisor_scheme(base / "ofk_advisor_scheme.png"),
        plot_ofk2_scheme(base / "ofk2_scheme.png"),
    ]
    for p in paths:
        print(f"Plot saved to {p}")
    return paths


if __name__ == "__main__":
    plot_all_architecture()
