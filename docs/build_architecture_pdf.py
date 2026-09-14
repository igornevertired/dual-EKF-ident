"""PDF: фактическая архитектура цикла моделирования БИНС/ГНСС + ОФК-1 + ОФК-2."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

OUT = Path(__file__).resolve().parent / "architecture_ofk1_ofk2.pdf"

C = {
    "fx1": "#1f4e79",
    "imu": "#5b2c6f",
    "bins": "#1a5276",
    "gnss": "#117a65",
    "ofk1": "#922b21",
    "ofk2": "#1a5276",
    "trim": "#7d6608",
    "bg": "#f4f6f7",
    "box": "#ffffff",
    "line": "#2c3e50",
    "muted": "#5d6d7e",
}


def _setup_rc():
    plt.rcParams.update(
        {
            "font.family": "DejaVu Sans",
            "font.size": 9,
            "axes.unicode_minus": False,
            "pdf.fonttype": 42,
        }
    )


def _page(fig, title: str):
    fig.patch.set_facecolor("white")
    fig.text(0.06, 0.955, title, fontsize=14, fontweight="bold", color="#1b2631")
    fig.text(0.06, 0.018, "По коду: run_full_sim.py → bins_gnss_simulation.run_simulation", fontsize=7, color=C["muted"])


def _box(ax, xy, w, h, text, *, fc="#fff", ec="#2c3e50", lw=1.1, fs=8, weight="normal", va="center"):
    x, y = xy
    p = FancyBboxPatch(
        (x, y), w, h,
        boxstyle="round,pad=0.012,rounding_size=0.04",
        facecolor=fc, edgecolor=ec, linewidth=lw, mutation_aspect=0.4,
    )
    ax.add_patch(p)
    ax.text(x + w / 2, y + h / 2, text, ha="center", va=va, fontsize=fs, fontweight=weight, color="#1b2631", wrap=True)
    return p


def _arrow(ax, a, b, color="#2c3e50"):
    ax.add_patch(
        FancyArrowPatch(
            a, b, arrowstyle="-|>", mutation_scale=10, lw=1.05, color=color, shrinkA=0, shrinkB=0
        )
    )


def page_title(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    _page(fig, "Цикл моделирования: ЛА → БИНС/ГНСС → ОФК-1 → ОФК-2")
    ax = fig.add_axes([0.06, 0.08, 0.88, 0.86])
    ax.axis("off")

    lines = [
        "Документ фиксирует, что реализовано в коде, а не план работ.",
        "",
        "Точка входа. python run_full_sim.py",
        "Ядро. src/model_python_port/simulation/bins_gnss_simulation.py → run_simulation()",
        "",
        "Сценарий по умолчанию (run_full_sim.py):",
        "  t = 60 с, dt = 1 мс (интегратор FX1 и механизация БИНС)",
        "  dt_gnss = 0.1 с  → ОФК-1 на 10 Гц",
        "  dt_ofk2 = 0.02 с → ОФК-2 на 50 Гц",
        "  манёвр руля высоты: doublet ±5° (канал δV автопилота заморожен на интервале)",
        "  балансировка: H = 500 м, V = 80 м/с, горизонтальный полёт",
        "",
        "Два фильтра в одном прогоне:",
        "  ОФК-1 — оценка ошибок навигации БИНС по измерениям ГНСС (loosely coupled),",
        "           обратная связь в вектор np_bins, error-state reset.",
        "  ОФК-2 — идентификация короткопериодических коэффициентов L*, M*",
        "           по выходам уже скорректированной навигации (БНК) и сырым ДУС/ДЛУ.",
        "           Параллельно крутится legacy Hoff (6 коэффициентов) только для сравнения.",
        "",
        "ОФК-2 не оценивает навигацию. ОФК-1 не оценивает аэродинамику.",
        "Связь односторонняя: ОФК-1 поправляет БИНС → из БНК собираются α, V, θ для ОФК-2.",
        "",
        "Эталон для ОФК-2 — численный якобиан модели FX1 (ofk2_jacobian_at_trim),",
        "не «истина из воздуха». Фильтр к эталону не привязан (нет theory-anchor).",
    ]
    ax.text(0.0, 0.98, "\n".join(lines), va="top", ha="left", fontsize=10.2, linespacing=1.35)
    pdf.savefig(fig)
    plt.close(fig)


def page_architecture(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    _page(fig, "Полный цикл одного шага dt = 1 мс и тактов фильтров")
    ax = fig.add_axes([0.02, 0.05, 0.96, 0.88])
    ax.set_xlim(0, 14)
    ax.set_ylim(0, 10)
    ax.axis("off")

    # Row 0 init
    _box(ax, (0.3, 8.7), 13.4, 0.9,
         "ЭТАП 0 (один раз): initsim / балансировка → x0, u0, θ_trim = якобиан FX1\n"
         "q, Cbn, np_bins = [Vn, Vh, Ve, h, φ, λ] без ошибок датчиков · InsErrorGen(seed=42) · RNG ГНСС seed=123",
         fc="#eaf2f8", ec=C["fx1"], fs=8)

    # FX1
    _box(ax, (0.3, 6.55), 3.3, 1.75,
         "ЭТАП 1 · 1000 Гц\nFX1 + RK4\nсостояние ЛА x (25)\nидеальные ω_bi^b , a_f^b\nавтопилот 100 Гц, doublet δe",
         fc="#d4e6f1", ec=C["fx1"], fs=8, weight="bold")

    # IMU
    _box(ax, (4.0, 6.55), 3.1, 1.75,
         "ЭТАП 2 · 1000 Гц\nInsErrorGen\nДУС: ω_m = ω + bω + nω\nДЛУ: a_m = a + ba + na\nbias: 0.5 °/ч , 5·10⁻⁴ м/с²",
         fc="#e8daef", ec=C["imu"], fs=8, weight="bold")

    # BINS
    _box(ax, (7.5, 6.55), 3.3, 1.75,
         "ЭТАП 3 · 1000 Гц\nbins_step\nмеханизация БИНС\nq, Cbn, np_bins\nиз (ω_m, a_m)",
         fc="#d5f5e3", ec=C["bins"], fs=8, weight="bold")

    # GNSS
    _box(ax, (11.1, 6.55), 2.6, 1.75,
         "ЭТАП 4b · 10 Гц\ngnss()\nσ_φ,λ = 5·10⁻⁶ рад\nσ_h = 1 м\nσ_V = 0.2 м/с",
         fc="#d1f2eb", ec=C["gnss"], fs=8, weight="bold")

    _arrow(ax, (3.6, 7.4), (4.0, 7.4))
    _arrow(ax, (7.1, 7.4), (7.5, 7.4))
    _arrow(ax, (10.8, 7.15), (11.1, 7.15))
    ax.text(10.95, 7.55, "истина\nφ λ h V", fontsize=6.5, ha="center", color=C["muted"])

    # OFK-1
    _box(ax, (0.3, 3.85), 6.6, 2.15,
         "ОФК-1  loosely coupled  ·  10 Гц  ·  filtering/loosely_coupled_ofk.py\n"
         "z = BINS − GNSS  (6 каналов: δφ, δλ, δVn, δVe, δVh, δh)\n"
         "состояние ошибок 15: 13 (BINS_OFK_2ch) + δVh, δh\n"
         "predict (Φ≈I+FΔt+…) → update → apply_bins_feedback(np_bins) → x_ofk := 0",
         fc="#fadbd8", ec=C["ofk1"], fs=8, weight="bold")

    # OFK-2
    _box(ax, (7.3, 3.85), 6.4, 2.15,
         "ОФК-2  equation-error EKF  ·  50 Гц  ·  filtering/ofk2_ekf.py\n"
         "после первого такта ОФК-1\n"
         "α,V из np_bins+Cbn · θ из Cbn · q,az из ω_m,a_m · δe из FX1 x[16]\n"
         "состояние 10: Lα Lq Lδe Lv Lθ Mα Mq Mδe Mv Mθ\n"
         "Z = [α̇_fd, q̇_fd, az]  ·  Q = 0  ·  обновление только при возбуждении",
         fc="#d6eaf8", ec=C["ofk2"], fs=8, weight="bold")

    _arrow(ax, (3.6, 6.55), (3.6, 6.0))
    ax.text(3.7, 6.2, "a_last, Cbn, np_bins", fontsize=6.5, color=C["muted"])
    _arrow(ax, (12.4, 6.55), (10.6, 6.0))
    ax.text(11.55, 6.22, "np_gnss", fontsize=6.5, color=C["muted"])

    _arrow(ax, (6.9, 4.9), (7.3, 4.9), color=C["ofk1"])
    ax.text(7.1, 5.15, "БНК:\nα V θ", fontsize=7, ha="center", color=C["ofk1"])

    _box(ax, (0.3, 1.55), 6.6, 1.85,
         "Обратная связь ОФК-1 в np_bins (не в x FX1):\n"
         "Vn −= x[3], Ve −= x[4], φ −= x[5], λ −= x[6],\n"
         "Vh −= x[13], h −= x[14]\n"
         "Ориентация q, Cbn этим шагом не корректируется.",
         fc="#fdebd0", ec=C["ofk1"], fs=8)

    _box(ax, (7.3, 1.55), 6.4, 1.85,
         "Эталон ОФК-2 (не вход фильтра):\n"
         "θ_trim — якобиан FX1 в t=0 (фиксирован)\n"
         "θ_FX1(t) — тот же якобиан на текущих (x,u) каждый такт 50 Гц\n"
         "legacy Hoff параллельно: 3 регрессора, 6 коэфф., те же α,q,δe,az",
         fc="#f9e79f", ec=C["trim"], fs=8)

    ax.text(7.0, 0.7,
            "Истина FX1 используется только как эталон логов и якобиана. В ОФК-1 и ОФК-2 она не подаётся.",
            ha="center", fontsize=8, color=C["muted"])
    pdf.savefig(fig)
    plt.close(fig)


def page_timing(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    _page(fig, "Тактовая сетка и потоки данных")
    ax = fig.add_axes([0.22, 0.42, 0.72, 0.48])
    ax.set_xlim(-0.5, 21)
    ax.set_ylim(-0.6, 5.2)
    ax.axis("off")

    ax.text(-0.3, 4.6, "FX1 + БИНС\n1000 Гц", fontsize=8, va="center", ha="right")
    ax.text(-0.3, 3.4, "ОФК-2  50 Гц\nкаждый 20 мс", fontsize=8, va="center", ha="right")
    ax.text(-0.3, 2.2, "ГНСС + ОФК-1\n10 Гц", fontsize=8, va="center", ha="right")
    ax.text(-0.3, 1.0, "автопилот\n100 Гц", fontsize=8, va="center", ha="right")

    ax.plot([0, 20], [4.6, 4.6], color=C["fx1"], lw=2)
    for i in range(21):
        ax.plot([i, i], [4.48, 4.72], color=C["fx1"], lw=0.6)

    ax.plot([0, 20], [3.4, 3.4], color=C["ofk2"], lw=0.8, alpha=0.4)
    for i in range(0, 21, 2):
        ax.plot(i, 3.4, "o", color=C["ofk2"], ms=5)

    ax.plot([0, 20], [2.2, 2.2], color=C["ofk1"], lw=0.8, alpha=0.4)
    for i in (0, 10, 20):
        ax.plot(i, 2.2, "s", color=C["ofk1"], ms=8)

    ax.plot([0, 20], [1.0, 1.0], color=C["trim"], lw=1.2)
    ax.text(10, 0.45, "окно 200 мс: 1 деление = 10 мс; квадрат — ГНСС/ОФК-1; кружок — ОФК-2", fontsize=8, ha="center")

    ax2 = fig.add_axes([0.07, 0.08, 0.86, 0.30])
    ax2.axis("off")
    ax2.set_xlim(0, 1)
    ax2.set_ylim(0, 1)
    txt = (
        "Порядок на шаге i (dt = 1 мс)\n"
        "1. RK4(FX1) → x, ω_bi^b, a_f^b.  2. Автопилот каждые 0.01 с → u (doublet δe).  "
        "3. InsErrorGen → ω_m, a_m.\n"
        "4. bins_step → q, Cbn, np_bins.\n"
        "5. Если (i+1) кратно 100: ГНСС от истины FX1; на первом такте выравнивание V и h БИНС по ГНСС;\n"
        "   z = np_bins − np_gnss; ofk_step; apply_bins_feedback; x_ofk := 0; лог навигации.\n"
        "6. Если gnss_idx>0 и (i+1) кратно 20: сбор регрессоров из БНК и датчиков → ekf_step ОФК-2 и legacy.\n"
        "\n"
        "Следствие. ОФК-2 работает на частоте выше ГНСС, но α,V,θ между тактами ОФК-1 меняются только\n"
        "из-за механизации БИНС (ошибки ДУС/ДЛУ), а не из-за новой поправки ГНСС. q и az — каждый 20 мс с IMU."
    )
    ax2.text(0, 1.0, txt, va="top", fontsize=9.2, linespacing=1.4)
    pdf.savefig(fig)
    plt.close(fig)


def page_ofk1(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    _page(fig, "ОФК-1: оценка ошибок БИНС по ГНСС")
    ax = fig.add_axes([0.06, 0.08, 0.88, 0.86])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(
        0, 1.0,
        "Назначение. Коррекция навигационного решения БИНС. Не идентификация ЛА.\n\n"
        "Тип. Error-state КФ, loosely coupled. Файлы: loosely_coupled_ofk.py, bins_ofk_2ch.py.\n\n"
        "Вектор БИНС np_bins = [Vn, Vh, Ve, h, φ, λ].\n"
        "Измерение ГНСС np_gnss = [φ, λ, h, Vn, Ve, Vh]  (истина FX1 + гауссов шум).\n"
        "Инновация z (порядок строк H):\n"
        "  [φ_bins−φ_gnss, λ_bins−λ_gnss, Vn_bins−Vn_gnss, Ve_bins−Ve_gnss, Vh_bins−Vh_gnss, h_bins−h_gnss].\n\n"
        "Состояние x_ofk ∈ R¹⁵. Первые 13 — модель ошибок БИНС (порт BINS_OFK_2ch.m):\n"
        "ориентация, скорости, положение, смещения ДУС/ДЛУ. Индексы 13–14: δVh, δh.\n"
        "Матрицы F,G,H,Q строятся на такте из a_last (тело), Cbn, np_bins, dt_gnss.\n\n"
        "P₀ диагональная (фрагмент): 10³ (первые 4), 10⁻² (следующие 6), 10⁻⁴ (остальные),\n"
        "P₀[13,13]=0.04 (σ_Vh ГНСС ≈ 0.2 м/с), P₀[14,14]=1 (σ_h ≈ 1 м).\n"
        "R = diag(σ² ГНСС) с полом и перестановкой под порядок H.\n\n"
        "Predict: Φ = I + F Δt + (F Δt)²/2, G_rus = G Δt, P ← ΦPΦᵀ + G_rus Q G_rusᵀ.\n"
        "Update: стандартный КФ по z, H, R.\n\n"
        "Обратная связь только в np_bins (см. схему). После неё x_ofk обнуляется (reset).\n"
        "q и Cbn ОФК-1 не правятся: ориентация для α и θ в ОФК-2 идёт из механизации БИНС.\n\n"
        "Первый такт ГНСС: Vn, Ve, Vh, h БИНС подставляются из ГНСС (грубое выравнивание),\n"
        "затем уже считается ОФК-1. ОФК-2 стартует только после этого такта (gnss_idx > 0).",
        va="top", fontsize=10, linespacing=1.32,
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_ofk2(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    _page(fig, "ОФК-2: идентификация L*, M*")
    ax = fig.add_axes([0.06, 0.08, 0.88, 0.86])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(
        0, 1.0,
        "Назначение. Оценка коэффициентов короткопериодической продольной модели.\n"
        "Не оценивает φ, λ, V навигации. Входы — уже после ОФК-1 (если такт ГНСС уже был).\n\n"
        "Модель (приращения от балансировки t=0):\n"
        "  α̇ = Lα δα + Lq q + Lδe δδe + Lv δV + Lθ δθ\n"
        "  q̇ = Mα δα + Mq q + Mδe δδe + Mv δV + Mθ δθ\n"
        "  az ≈ az0 − (V/g)(Lα δα + (Lq−1)q + Lδe δδe + Lv δV + Lθ δθ)\n\n"
        "Состояние: 10 коэффициентов. Измерение Z = [α̇_fd, q̇_fd, az], α̇ и q̇ — конечные разности за dt_ofk2.\n"
        "Регрессоры: δα = α−α0, q, δδe = δe−δe0, δV = V−V0, δθ = θ−θ0.\n"
        "α, V: reconstruct_alpha_from_nav(np_bins, Cbn).  θ: c_ang(Cbn).  q = ω_m,z.  az = a_m,y / g.\n"
        "δe: привод FX1 x[16] (градусы → рад).  az0 замораживается на первом измерении az.\n\n"
        "θ̂(0) = 1.3 · θ_trim  (намеренное смещение +30%).  Q = 0.  R = diag(0.025, 0.002, 0.023)².\n"
        "Обновление EKF только если есть возбуждение (|δδe|≥0.003 или |q|≥0.005 или |δα|≥0.008\n"
        "или |δV|≥0.05 или |δθ|≥0.003) и уже есть предыдущий такт для разностей.\n\n"
        "Эталон. θ_trim — якобиан FX1 в балансировке, фиксирован. θ_FX1(t) пересчитывается каждый такт\n"
        "ОФК-2 из текущего (x,u) FX1. Фильтр эталон не видит. На графиках: синяя = θ̂−trim,\n"
        "чёрная = θ_FX1(t)−trim, оранжевая = 0 (эталон-балансировка).\n\n"
        "Lθ, Mθ в фильтре есть (структура уравнений). На балансировке ≈ 0, слабо наблюдаемы.\n"
        "В отчётных графиках: Lα, Lq, Lδe, Lv, Mα, Mq, Mδe, Mv.\n\n"
        "Legacy (ofk2_ekf_legacy.py) в том же цикле: 3 регрессора δα,q,δδe и 6 коэффициентов Hoff.\n"
        "Нужен только как база сравнения; на навигацию и на основную ОФК-2 не влияет.",
        va="top", fontsize=9.6, linespacing=1.28,
    )
    pdf.savefig(fig)
    plt.close(fig)


def page_facts(pdf):
    fig = plt.figure(figsize=(11.69, 8.27))
    _page(fig, "Что сделано в коде и чего нет")
    ax = fig.add_axes([0.06, 0.08, 0.88, 0.86])
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(
        0, 1.0,
        "Сделано\n"
        "• Порт динамики FX1, балансировка, автопилот, doublet руля.\n"
        "• Цепочка датчики → механизация БИНС → ГНСС → ОФК-1 с обратной связью.\n"
        "• ОФК-2 на 10 коэффициентах; параллельный legacy Hoff.\n"
        "• Эталон: якобиан FX1 на trim и мгновенный якобиан на такте ОФК-2.\n"
        "• Выход run_full_sim.py: таблицы + графики в src/plots/ (навигация ОФК-1,\n"
        "  параметры и ошибки ОФК-2, сравнение с legacy, дрейф эталона).\n"
        "• Sweep амплитуды doublet (run_doublet_amp_sweep.py) — возбуждение, не ошибки БНС.\n\n"
        "Не сделано (по состоянию кода)\n"
        "• Sweep уровня ошибок ГНСС/БИНС: run_simulation не принимает множитель σ ГНСС.\n"
        "  Основной исследовательский эксперимент ВКР по влиянию ошибок БНС на идентификацию\n"
        "  в виде серии прогонов не реализован. Есть один номинальный уровень σ.\n"
        "• ОФК-1 не корректирует ориентацию (q, Cbn) — α и θ для ОФК-2 несут эту ошибку.\n"
        "• az0 не обновляется при уходе режима. Q ОФК-2 нулевой.\n"
        "• Lθ, Mθ остаются в состоянии фильтра, из отчёта исключены.\n\n"
        "Ключевые файлы\n"
        "  run_full_sim.py\n"
        "  simulation/bins_gnss_simulation.py, initsim.py\n"
        "  dynamics/fx1.py, autopilot_model.py\n"
        "  sensors/imu_error_generator.py, sensors/core.py (gnss)\n"
        "  navigation/bins_common.py (bins_step)\n"
        "  filtering/loosely_coupled_ofk.py, bins_ofk_2ch.py\n"
        "  filtering/ofk2_ekf.py, ofk2_ekf_legacy.py, ofk2_theory.py\n"
        "  output/full_sim_outputs.py\n",
        va="top", fontsize=10, linespacing=1.32,
    )
    pdf.savefig(fig)
    plt.close(fig)


def main():
    _setup_rc()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    with PdfPages(OUT) as pdf:
        page_title(pdf)
        page_architecture(pdf)
        page_timing(pdf)
        page_ofk1(pdf)
        page_ofk2(pdf)
        page_facts(pdf)
        d = pdf.infodict()
        d["Title"] = "Цикл моделирования БИНС/ГНСС ОФК-1 ОФК-2"
        d["Author"] = "university / model_python_port"
    print(f"PDF: {OUT}")


if __name__ == "__main__":
    main()
