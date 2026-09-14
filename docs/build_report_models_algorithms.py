#!/usr/bin/env python3
"""Отчёт для руководителя: модели и алгоритмы (по коду, OMML)."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.shared import Cm, Pt

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from build_chapter1_docx import (  # noqa: E402
    D,
    E,
    add_body,
    add_heading,
    add_table,
    set_paragraph_format,
    set_run_font,
)
OUT = _HERE / "Отчет_модели_и_алгоритмы.docx"
FIG = _HERE / "_teacher_arch.png"
PLOTS = _HERE.parent / "src" / "plots"
STATS = _HERE / "_report_stats.json"


def _fmt(value: float, digits: int = 3) -> str:
    """Число в русской записи: разделитель — запятая."""
    if value != 0 and (abs(value) < 1e-3 or abs(value) >= 1e5):
        return f"{value:.{digits}e}".replace(".", ",")
    return f"{value:.{digits}f}".replace(".", ",")


def figure(doc, path: Path, width_cm: float = 16.0) -> None:
    if not path.exists():
        raise SystemExit(f"Нет рисунка {path}")
    p = doc.add_paragraph()
    set_paragraph_format(p, first_line=False, align="center", space_after=4)
    p.add_run().add_picture(str(path), width=Cm(width_cm))


def caption(doc, text):
    p = doc.add_paragraph()
    set_paragraph_format(p, first_line=False, align="center", space_after=12)
    run = p.add_run(text)
    set_run_font(run, size=12, bold=True)


def build() -> Path:
    if not FIG.exists():
        # matplotlib нужен только когда схему приходится рисовать заново
        from build_teacher_brief_docx import draw_arch

        draw_arch()
    if not STATS.exists():
        raise SystemExit(f"Нет {STATS}. Сначала: python docs/_report_stats.py")
    st = json.loads(STATS.read_text(encoding="utf-8"))
    nav, coeff = st["nav"], st["coeff"]

    doc = Document()
    sec = doc.sections[0]
    sec.top_margin = Cm(2)
    sec.bottom_margin = Cm(2)
    sec.left_margin = Cm(3)
    sec.right_margin = Cm(1.5)
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(14)
    style._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")

    p = doc.add_paragraph()
    set_paragraph_format(p, first_line=False, align="center", space_after=6)
    run = p.add_run("Модели и алгоритмы численного моделирования БНК и идентификации")
    set_run_font(run, size=16, bold=True)
    p = doc.add_paragraph()
    set_paragraph_format(p, first_line=False, align="center", space_after=16)
    run = p.add_run(
        "Реализация: run_full_sim.py → bins_gnss_simulation.run_simulation. "
        "Ниже — как сделано в коде, не план."
    )
    set_run_font(run, size=12)

    add_heading(doc, "1. Назначение контура", 1)
    add_body(
        doc,
        "Имитационный контур одновременно воспроизводит динамику летательного аппарата, "
        "ошибки инерциальных датчиков, механизацию БИНС, упрощённые измерения ГНСС, "
        "оценку ошибок навигации (ОФК-1) и идентификацию коэффициентов короткопериодического "
        "продольного движения (ОФК-2). ОФК-1 не оценивает аэродинамику. ОФК-2 не оценивает "
        "координаты и скорость. Связь односторонняя: ОФК-1 корректирует навигационный вектор "
        "БИНС; из скорректированного решения собираются угол атаки, скорость и тангаж для ОФК-2. "
        "Истинное состояние модели FX1 в оба фильтра не подаётся и используется только как эталон "
        "для логов и для численного якобиана коэффициентов.",
    )
    p = doc.add_paragraph()
    set_paragraph_format(p, first_line=False, align="center", space_after=4)
    p.add_run().add_picture(str(FIG), width=Cm(16.2))
    caption(doc, "Рисунок 1 — Поток данных")

    add_heading(doc, "2. Модель летательного аппарата FX1", 1)
    add_body(
        doc,
        "Порт FX1.m. Нелинейные уравнения движения шести степеней свободы: аэродинамика, тяга, "
        "гравитация и переносные/кориолисовы ускорения модели Земли, кинематика углов и координат, "
        "динамика приводов. Состояние "
        + E(r"x\in\mathbb{R}^{25}")
        + ": скорость и угловая скорость в связанной СК, крен, курс, тангаж, дальность, высота, "
        "боковое отклонение, широта, долгота, положения приводов "
        + E(r"\delta T,\,\delta V,\,\delta N,\,\delta E")
        + ", ветер, вспомогательные переменные. Управление "
        + E(r"u=[\delta T,\,\delta V,\,\delta N,\,\delta E]^{\mathsf{T}}")
        + ".",
    )
    add_body(
        doc,
        "Правая часть "
        + E(r"\dot{x}=f(x,u,t)")
        + " возвращает также идеальные выходы инерциальных приборов в связанной СК: "
        "абсолютную угловую скорость "
        + E(r"\omega_{bi}^{b}")
        + " и кажущееся ускорение без гравитации "
        + E(r"a_{f}^{b}")
        + " (то, что измерили бы идеальные ДУС и ДЛУ).",
    )
    add_body(
        doc,
        "Аэродинамические силы считаются через скоростной напор "
        + E(r"\bar{q}=\tfrac{1}{2}\rho V^{2}S\|g\|")
        + " и безразмерные коэффициенты; плотность — по стандартной атмосфере "
        + E(r"\rho=\rho_{0}\left((288{,}16-0{,}0066h)/288{,}16\right)^{4{,}255}")
        + ":",
    )
    add_body(
        doc,
        D(
            r"c_{y}=c_{y0}+c_{y}^{\alpha}\alpha+c_{y}^{\delta V}\delta V+c_{y}^{\varphi_{st}}\varphi_{st}"
        ),
    )
    add_body(
        doc,
        D(
            r"c_{x}=c_{x0}+Ac_{y}+Bc_{y}^{2}"
            r"+\left(c_{x}^{\delta V}+c_{x}^{\alpha\delta V}\alpha+c_{x}^{\alpha^{2}\delta V}\alpha^{2}\right)\delta V"
            r"+\left(c_{x}^{\varphi}+c_{x}^{\alpha\varphi}\alpha+c_{x}^{\alpha^{2}\varphi}\alpha^{2}\right)\varphi_{st}"
        ),
    )
    add_body(
        doc,
        D(
            r"m_{z}=m_{z0}+m_{z}^{\alpha}\alpha+m_{z}^{\alpha^{2}}\alpha^{2}"
            r"+m_{z}^{\delta V}\delta V+m_{z}^{\varphi_{st}}\varphi_{st}"
            r"+m_{z}^{\omega_{z}}\frac{\omega_{z}b_{a}}{V}"
            r"+m_{z}^{\dot{\alpha}}\frac{\dot{\alpha}b_{a}}{V}"
        ),
    )
    add_body(
        doc,
        "Силы разворачиваются из скоростной СК в связанную по углу атаки, тяга задаётся положением "
        "РУД и плотностью:",
    )
    add_body(
        doc,
        D(
            r"F_{x1}=X\cos\alpha-Y\sin\alpha,\qquad "
            r"F_{y1}=X\sin\alpha+Y\cos\alpha,\qquad "
            r"F_{z1}=Z,\qquad P=\delta T\,P_{\max}\left(\rho/\rho_{0}\right)^{0{,}75}"
        ),
    )
    add_body(
        doc,
        "Уравнения поступательного движения в связанной СК (гравитация и переносные ускорения "
        "пересчитываются в связанную СК матрицей "
        + E(r"C_{gb}")
        + "):",
    )
    add_body(
        doc,
        D(
            r"\dot{V}_{x1}=\frac{1}{m}\left(P\cos\varphi_{p}-F_{x1}\right)+a_{p,x}+a_{k,x}+a_{t,x}+g_{x}^{b}"
        ),
    )
    add_body(
        doc,
        D(
            r"\dot{V}_{y1}=\frac{1}{m}\left(P\sin\varphi_{p}+F_{y1}\right)+a_{p,y}+a_{k,y}+a_{t,y}+g_{y}^{b}"
        ),
    )
    add_body(
        doc,
        D(r"\dot{V}_{z1}=\frac{F_{z1}}{m}+a_{p,z}+a_{t,z}+g_{z}^{b}"),
    )
    add_body(
        doc,
        "где переносное, кориолисово и вращательное ускорения:",
    )
    add_body(
        doc,
        D(
            r"a_{p}=-\omega_{ei}\times\left(\omega_{ei}\times r\right),\qquad "
            r"a_{k}=-2\,\omega_{ei}\times V^{b},\qquad "
            r"a_{t}=-\left(\omega_{bi}^{b}-\omega_{ei}^{b}\right)\times V^{b}"
        ),
    )
    add_body(
        doc,
        "Вращательное движение — уравнения Эйлера с центробежным моментом инерции "
        + E(r"J_{xy}")
        + "; канал тангажа определяет короткопериодическое движение:",
    )
    add_body(
        doc,
        D(
            r"\dot{\omega}_{z1}=\frac{1}{J_{zz}}\left[M_{z}"
            r"-\left(J_{yy}-J_{xx}\right)\omega_{x1}\omega_{y1}"
            r"-J_{xy}\left(\omega_{y1}^{2}-\omega_{x1}^{2}\right)\right]"
        ),
    )
    add_body(
        doc,
        "Каналы крена и рыскания связаны через "
        + E(r"J_{xy}")
        + " и решаются совместно с определителем "
        + E(r"\det J=J_{xx}J_{yy}-J_{xy}^{2}")
        + ". Кинематика углов ориентации и координат:",
    )
    add_body(
        doc,
        D(
            r"\dot{\psi}=\frac{\omega_{y}^{bg}\cos\gamma-\omega_{z}^{bg}\sin\gamma}{\cos\vartheta},\qquad "
            r"\dot{\vartheta}=\omega_{z}^{bg}\cos\gamma+\omega_{y}^{bg}\sin\gamma,\qquad "
            r"\dot{\gamma}=\omega_{x}^{bg}-\dot{\psi}\sin\vartheta"
        ),
    )
    add_body(
        doc,
        D(
            r"\dot{\varphi}=\frac{\dot{x}_{g}}{R_{N}},\qquad "
            r"\dot{\lambda}=\frac{\dot{z}_{g}}{R_{E}\cos\varphi},\qquad "
            r"\dot{h}=V_{x1}\sin\vartheta+V_{y1}\cos\vartheta\cos\gamma-V_{z1}\cos\vartheta\sin\gamma"
        ),
    )
    add_body(
        doc,
        "Приводы органов управления — апериодические звенья первого порядка:",
    )
    add_body(
        doc,
        D(
            r"\dot{\delta}_{i}=\frac{u_{i}-\delta_{i}}{T_{i}},\qquad "
            r"i\in\{T,V,N,E\}"
        ),
    )
    add_body(
        doc,
        "Интегрирование — метод Рунге–Кутты 4-го порядка с шагом "
        + E(r"\Delta t=10^{-3}")
        + " с. Дополнительные выходы "
        + E(r"\omega_{bi}^{b}")
        + " и "
        + E(r"a_{f}^{b}")
        + " берутся из последнего вызова правой части на шаге (конец интервала).",
    )
    add_body(
        doc,
        "Автопилот (порты VHHOLD / HEADINGHOLD) удерживает высоту 500 м и скорость 80 м/с, "
        "такт 0,01 с. С "
        + E(r"t=10")
        + " с по "
        + E(r"t=15")
        + " с на руль высоты накладывается doublet: "
        + E(r"+5^{\circ}")
        + " в течение 2,5 с, затем "
        + E(r"-5^{\circ}")
        + " в течение 2,5 с. На интервале манёвра канал "
        + E(r"\delta V")
        + " автопилота заморожен, чтобы не гасить вход идентификации.",
    )

    add_heading(doc, "3. Модели датчиков", 1)
    add_heading(doc, "3.1. ДУС и ДЛУ", 2)
    add_body(
        doc,
        "Класс InsErrorGen (порт GENERATOR_SV.m). Ошибки добавляются после FX1 и до механизации БИНС:",
    )
    add_body(
        doc,
        D(
            r"\omega_{m}=\omega_{bi}^{b}+b_{\omega}+n_{\omega},\qquad "
            r"a_{m}=a_{f}^{b}+b_{a}+n_{a}"
        ),
    )
    add_body(
        doc,
        "Смещения постоянны на весь прогон, "
        + E(r"b_{\omega}\sim\mathcal{N}(0,\,(0{,}5^{\circ}/\mathrm{ч})^{2})")
        + " по трём осям, "
        + E(r"b_{a}\sim\mathcal{N}(0,\,(5\cdot 10^{-4}\ \mathrm{м/с}^{2})^{2})")
        + ", seed 42. Белый шум независим на каждом шаге "
        + E(r"\Delta t")
        + ": "
        + E(r"\sigma_{\omega}=10^{-5}")
        + " (вход модели угловой скорости), "
        + E(r"\sigma_{a}=5\cdot 10^{-5}")
        + " м/с², seed 43. Масштабные коэффициенты, рассогласование осей и случайные блуждания "
        "сверх этой модели не вводятся.",
    )
    add_body(
        doc,
        "Перевод паспортной величины дрейфа гироскопа в единицы модели:",
    )
    add_body(
        doc,
        D(
            r"\sigma_{b_{\omega}}=0{,}5\ \frac{\text{град}}{\text{ч}}"
            r"=0{,}5\cdot\frac{\pi}{180\cdot 3600}=2{,}42\cdot 10^{-6}\ \frac{\text{рад}}{\text{с}}"
        ),
    )

    add_heading(doc, "3.2. ГНСС", 2)
    add_body(
        doc,
        "Псевдодальности и эфемериды не моделируются. Каждые "
        + E(r"\Delta t_{\mathrm{GNSS}}=0{,}1")
        + " с к истинным "
        + E(r"\varphi,\,\lambda,\,h,\,V_{N},\,V_{E},\,V_{h}")
        + " из FX1 добавляется независимый гауссов шум (seed 123):",
    )
    add_body(
        doc,
        D(
            r"y_{\mathrm{GNSS}}=y_{\mathrm{true}}+\mathrm{diag}(\sigma)\,\xi,\qquad "
            r"\xi\sim\mathcal{N}(0,I_{6})"
        ),
    )
    add_table(
        doc,
        ["Канал", "СКО"],
        [
            ["φ, λ", "5·10⁻⁶ рад"],
            ["h", "1 м"],
            ["Vn, Ve, Vh", "0,2 м/с"],
        ],
    )

    add_heading(doc, "4. Алгоритм механизации БИНС", 1)
    add_body(
        doc,
        "Навигационный вектор "
        + E(r"n_{p}=[V_{N},\,V_{h},\,V_{E},\,h,\,\varphi,\,\lambda]^{\mathsf{T}}")
        + ". Один шаг bins_step: сначала навигация по "
        + E(r"a_{m}")
        + ", затем ориентация по "
        + E(r"\omega_{m}")
        + " (как BINS1.m).",
    )
    add_body(
        doc,
        "Ускорение в географической СК и динамика скорости:",
    )
    add_body(
        doc,
        D(
            r"a_{\mathrm{nav}}=C_{bn}a_{m},\qquad "
            r"\dot{v}^{n}=a_{\mathrm{nav}}+a_{p}+a_{k}+a_{t}+g"
        ),
    )
    add_body(
        doc,
        "Угловые скорости, входящие в переносные члены:",
    )
    add_body(
        doc,
        D(
            r"\omega_{ei}^{n}=\left[U_{e}\cos\varphi,\ U_{e}\sin\varphi,\ 0\right]^{\mathsf{T}},\qquad "
            r"\omega_{ge}^{n}=\left[\frac{V_{E}}{R_{E}},\ \frac{V_{E}\tan\varphi}{R_{E}},"
            r"\ -\frac{V_{N}}{R_{N}}\right]^{\mathsf{T}}"
        ),
    )
    add_body(
        doc,
        D(
            r"a_{p}=-\omega_{ei}^{n}\times\left(\omega_{ei}^{n}\times r^{n}\right),\qquad "
            r"a_{k}=-2\,\omega_{ei}^{n}\times v^{n},\qquad "
            r"a_{t}=-\omega_{ge}^{n}\times v^{n}"
        ),
    )
    add_body(
        doc,
        "где "
        + E(r"a_{p}")
        + " — переносное ускорение от вращения Земли, "
        + E(r"a_{k}")
        + " — кориолисово, "
        + E(r"a_{t}")
        + " — от вращения географической СК, "
        + E("g")
        + " — гравитация earthmodel. Кинематика:",
    )
    add_body(
        doc,
        D(
            r"\dot{h}=V_{h},\qquad "
            r"\dot{\varphi}=\frac{V_{N}}{R_{N}},\qquad "
            r"\dot{\lambda}=\frac{V_{E}}{R_{E}\cos\varphi}"
        ),
    )
    add_body(
        doc,
        "Ориентация. Угловая скорость географической СК относительно инерциальной переводится в связанную; "
        "относительная угловая скорость прибора:",
    )
    add_body(
        doc,
        D(
            r"\omega_{ni}^{n}=\omega_{ei}^{n}+\omega_{ne}^{n},\qquad "
            r"\omega_{ni}^{b}=C_{bn}^{\mathsf{T}}\omega_{ni}^{n},\qquad "
            r"\omega_{bnb}^{b}=\omega_{m}-\omega_{ni}^{b}"
        ),
    )
    add_body(doc, "Уравнение кватерниона с нормировочной поправкой:")
    add_body(
        doc,
        D(
            r"\dot{q}=\tfrac{1}{2}\,q\circ\omega_{bnb}^{b}"
            r"+\tfrac{1}{2}\left(1-\|q\|^{2}\right)q"
        ),
    )
    add_body(doc, "Матрица ориентации восстанавливается из кватерниона:")
    add_body(
        doc,
        D(
            r"C_{nb}=\begin{bmatrix}"
            r"1-2(q_{2}^{2}+q_{3}^{2}) & 2(q_{1}q_{2}+q_{3}q_{0}) & 2(q_{1}q_{3}-q_{2}q_{0})\\"
            r"2(q_{1}q_{2}-q_{3}q_{0}) & 1-2(q_{1}^{2}+q_{3}^{2}) & 2(q_{2}q_{3}+q_{1}q_{0})\\"
            r"2(q_{1}q_{3}+q_{2}q_{0}) & 2(q_{2}q_{3}-q_{1}q_{0}) & 1-2(q_{1}^{2}+q_{2}^{2})"
            r"\end{bmatrix},\qquad C_{bn}=C_{nb}^{\mathsf{T}}"
        ),
    )
    add_body(
        doc,
        "Кватернион интегрируется с нормировочной поправкой "
        + E(r"(1-\|q\|^{2})")
        + ", матрица "
        + E(r"C_{bn}")
        + " восстанавливается из кватерниона. ОФК-1 "
        + E("q")
        + " и "
        + E(r"C_{bn}")
        + " не корректирует.",
    )
    add_body(
        doc,
        "Инициализация: "
        + E("q")
        + ", "
        + E(r"C_{bn}")
        + " и "
        + E(r"n_{p}")
        + " совпадают с истиной FX1 (без ошибок датчиков). Далее расхождение накапливается только из этапа 3.1.",
    )

    add_heading(doc, "5. Алгоритм ОФК-1 (навигация)", 1)
    add_body(
        doc,
        "Тип: error-state фильтр Калмана, loosely coupled. Состояние "
        + E(r"x_{\mathrm{I}}\in\mathbb{R}^{15}")
        + ": первые 13 — порт модели ошибок БИНС (BINS_OFK_2ch.m: ориентация, "
        + E(r"\delta V_{N},\,\delta V_{E}")
        + ", "
        + E(r"\delta\varphi,\,\delta\lambda")
        + ", смещения ДУС и ДЛУ); индексы 13–14 — "
        + E(r"\delta V_{h}")
        + " и "
        + E(r"\delta h")
        + ".",
    )
    add_body(doc, "Инновация (порядок строк H):")
    add_body(
        doc,
        D(
            r"z=\bigl["
            r"\varphi_{B}-\varphi_{G},\;"
            r"\lambda_{B}-\lambda_{G},\;"
            r"V_{N,B}-V_{N,G},\;"
            r"V_{E,B}-V_{E,G},\;"
            r"V_{h,B}-V_{h,G},\;"
            r"h_{B}-h_{G}"
            r"\bigr]^{\mathsf{T}}"
        ),
    )
    add_body(
        doc,
        "Непрерывная модель ошибок на такте ГНСС:",
    )
    add_body(
        doc,
        D(r"\dot{x}_{\mathrm{I}}=F x_{\mathrm{I}}+G w,\qquad z=H x_{\mathrm{I}}+\nu"),
    )
    add_body(
        doc,
        "Разбиение вектора состояния и структура "
        + E("F")
        + " по строкам (как в BINS_OFK_2ch.m):",
    )
    add_body(
        doc,
        D(
            r"x_{\mathrm{I}}=\bigl[\underbrace{\alpha_{x},\alpha_{y},\alpha_{z}}_{3},\ "
            r"\underbrace{\delta V_{N},\delta V_{E}}_{2},\ "
            r"\underbrace{\delta\varphi,\delta\lambda}_{2},\ "
            r"\underbrace{b_{a}}_{3},\ \underbrace{b_{\omega}}_{3},\ "
            r"\delta V_{h},\ \delta h\bigr]^{\mathsf{T}}"
        ),
    )
    add_body(
        doc,
        D(
            r"\dot{\alpha}=-\left[\omega_{f}\times\right]\alpha"
            r"+F_{12}\,\delta V+F_{13}\,\delta r+C_{2}b_{\omega}"
        ),
    )
    add_body(
        doc,
        D(
            r"\delta\dot{V}=-\left[n\times\right]_{1:2}\alpha"
            r"+F_{22}\,\delta V+F_{23}\,\delta r+\left(C_{2}\right)_{1:2}b_{a}"
        ),
    )
    add_body(
        doc,
        D(
            r"\delta\dot{r}=F_{32}\,\delta V+F_{33}\,\delta r,\qquad "
            r"\dot{b}_{a}=0,\qquad \dot{b}_{\omega}=0"
        ),
    )
    add_body(
        doc,
        D(
            r"\delta\dot{V}_{h}=n_{y}\alpha_{x}-n_{x}\alpha_{y}"
            r"+\left(C_{2}b_{a}\right)_{z},\qquad \delta\dot{h}=\delta V_{h}"
        ),
    )
    add_body(
        doc,
        "где "
        + E(r"\omega_{f}=\omega_{ei}^{n}+\omega_{ge}^{n}")
        + " — угловая скорость сопровождающего трёхгранника, "
        + E(r"n=C_{2}a_{m}")
        + " — удельная сила в географической СК, "
        + E(r"\delta r=[\delta\varphi,\delta\lambda]^{\mathsf{T}}")
        + ", "
        + E(r"\left[\,\cdot\times\right]")
        + " — кососимметрическая матрица векторного произведения. Матрица измерений:",
    )
    add_body(
        doc,
        D(
            r"H=\begin{bmatrix}"
            r"e_{6}^{\mathsf{T}}\\ e_{7}^{\mathsf{T}}\\ e_{4}^{\mathsf{T}}\\ "
            r"e_{5}^{\mathsf{T}}\\ e_{14}^{\mathsf{T}}\\ e_{15}^{\mathsf{T}}"
            r"\end{bmatrix}\in\mathbb{R}^{6\times 15}"
        ),
    )
    add_body(
        doc,
        "где "
        + E(r"e_{i}")
        + " — орт "
        + E("i")
        + "-й компоненты состояния (нумерация с единицы): "
        + E(r"\delta\varphi,\ \delta\lambda,\ \delta V_{N},\ \delta V_{E},\ \delta V_{h},\ \delta h")
        + ".",
    )
    add_body(
        doc,
        "Матрицы "
        + E("F,G,H,Q")
        + " строятся из "
        + E(r"a_{m}")
        + " в связанной СК, "
        + E(r"C_{bn}")
        + " и "
        + E(r"n_{p}")
        + ". Для 13-мерного ядра "
        + E("H")
        + " выделяет "
        + E(r"\delta\varphi,\,\delta\lambda,\,\delta V_{N},\,\delta V_{E}")
        + ". Расширение: "
        + E(r"\delta\dot{h}=\delta V_{h}")
        + ", без кросс-связей вертикального канала с горизонтальными скоростями "
        "(ограничение кода, чтобы не портить горизонталь через ковариацию). "
        "Процессный шум:",
    )
    add_body(
        doc,
        D(
            r"Q=\mathrm{diag}(w_{q,i}^{2}/\Delta t_{\mathrm{GNSS}}),\quad "
            r"w_{q}=(20\cdot 10^{-10},\,20\cdot 10^{-10},\,20\cdot 10^{-10},"
            r"\,25\cdot 10^{-7},\,25\cdot 10^{-7},\,25\cdot 10^{-7})"
        ),
    )
    add_body(
        doc,
        "Ковариация измерения "
        + E("R")
        + " — диагональ из "
        + E(r"\sigma_{\mathrm{GNSS}}^{2}")
        + " с нижним полом и перестановкой под порядок "
        + E("H")
        + ".",
    )
    add_body(doc, "Предсказание (дискретизация как OFK.m), " + E(r"\Delta t=\Delta t_{\mathrm{GNSS}}") + ":")
    add_body(
        doc,
        D(
            r"\Phi=I+F\Delta t+\frac{(F\Delta t)^{2}}{2},\qquad "
            r"G_{\mathrm{rus}}=G\Delta t"
        ),
    )
    add_body(
        doc,
        D(
            r"\hat{x}^{-}=\Phi\hat{x}^{+},\qquad "
            r"P^{-}=\Phi P^{+}\Phi^{\mathsf{T}}+G_{\mathrm{rus}} Q G_{\mathrm{rus}}^{\mathsf{T}}"
        ),
    )
    add_body(doc, "Обновление (форма Джозефа для P):")
    add_body(
        doc,
        D(
            r"S=HP^{-}H^{\mathsf{T}}+R,\qquad "
            r"K=P^{-}H^{\mathsf{T}}S^{-1}"
        ),
    )
    add_body(
        doc,
        D(
            r"\hat{x}^{+}=\hat{x}^{-}+K(z-H\hat{x}^{-}),\qquad "
            r"P^{+}=(I-KH)P^{-}(I-KH)^{\mathsf{T}}+KRK^{\mathsf{T}}"
        ),
    )
    add_body(
        doc,
        "Обратная связь только в "
        + E(r"n_{p}")
        + " (не в состояние FX1). Индексация Python 0-based:",
    )
    add_body(
        doc,
        D(
            r"V_{N}\leftarrow V_{N}-\hat{x}_{[3]},\ "
            r"V_{E}\leftarrow V_{E}-\hat{x}_{[4]},\ "
            r"\varphi\leftarrow\varphi-\hat{x}_{[5]},\ "
            r"\lambda\leftarrow\lambda-\hat{x}_{[6]},\ "
            r"V_{h}\leftarrow V_{h}-\hat{x}_{[13]},\ "
            r"h\leftarrow h-\hat{x}_{[14]}"
        ),
    )
    add_body(
        doc,
        "После обратной связи "
        + E(r"\hat{x}_{\mathrm{I}}:=0")
        + " (error-state reset). На первом такте ГНСС скорости и высота БИНС подставляются из ГНСС, "
        "затем выполняется ОФК-1. Старт: "
        + E(r"\hat{x}_{\mathrm{I}}=0")
        + "; диагональ "
        + E(r"P_{0}")
        + ": 10³ (4 элемента), 10⁻² (6), 10⁻⁴ (5), с заменами "
        + E(r"P_{0}[13,13]=0{,}04")
        + ", "
        + E(r"P_{0}[14,14]=1")
        + ".",
    )

    add_heading(doc, "6. Модель и алгоритм ОФК-2 (идентификация)", 1)
    add_heading(doc, "6.1. Модель короткопериодического движения", 2)
    add_body(
        doc,
        "Линейная модель в приращениях от точки балансировки "
        + E(r"t=0")
        + ":",
    )
    add_body(
        doc,
        D(
            r"\dot{\alpha}=L_{\alpha}\delta\alpha+L_{q}q+L_{\delta e}\delta\delta e"
            r"+L_{V}\delta V+L_{\theta}\delta\theta"
        ),
    )
    add_body(
        doc,
        D(
            r"\dot{q}=M_{\alpha}\delta\alpha+M_{q}q+M_{\delta e}\delta\delta e"
            r"+M_{V}\delta V+M_{\theta}\delta\theta"
        ),
    )
    add_body(
        doc,
        D(
            r"a_{z}\approx a_{z0}-\frac{V}{g}\Bigl("
            r"L_{\alpha}\delta\alpha+(L_{q}-1)q+L_{\delta e}\delta\delta e"
            r"+L_{V}\delta V+L_{\theta}\delta\theta\Bigr)"
        ),
    )
    add_body(
        doc,
        "Член "
        + E(r"(L_{q}-1)q")
        + " отделяет кинематику "
        + E(r"\dot{\alpha}\approx q")
        + " от аэродинамического вклада в нормальную перегрузку. На балансировке якобиан FX1 даёт "
        + E(r"L_{q}=1")
        + ".",
    )
    add_body(
        doc,
        "Вектор состояния фильтра (десять коэффициентов):",
    )
    add_body(
        doc,
        D(
            r"\theta=\bigl[L_{\alpha},\,L_{q},\,L_{\delta e},\,L_{V},\,L_{\theta},"
            r"\,M_{\alpha},\,M_{q},\,M_{\delta e},\,M_{V},\,M_{\theta}\bigr]^{\mathsf{T}}"
        ),
    )
    add_body(doc, "Регрессор:")
    add_body(
        doc,
        D(
            r"\phi=\bigl[\alpha-\alpha_{0},\,q,\,\delta e-\delta e_{0},"
            r"\,V-V_{0},\,\theta-\theta_{0}\bigr]^{\mathsf{T}}"
        ),
    )
    add_body(
        doc,
        "Источники сигналов. Скорость в связанной СК "
        + E(r"v^{b}=C_{bn}^{\mathsf{T}}[V_{N},V_{h},V_{E}]^{\mathsf{T}}")
        + ", "
        + E(r"\alpha=-\mathrm{arctan2}(v_{y}^{b},v_{x}^{b})")
        + ", "
        + E(r"V=\|v^{b}\|")
        + ". Тангаж из "
        + E(r"C_{bn}")
        + " (c_ang). "
        + E(r"q=\omega_{m,z}")
        + ", "
        + E(r"a_{z}=a_{m,y}/g")
        + ", "
        + E(r"g=9{,}80665")
        + " м/с². Руль "
        + E(r"\delta e")
        + " — состояние привода FX1 (перевод градусов в радианы). "
        + E(r"a_{z0}")
        + " равен первому измеренному "
        + E(r"a_{z}")
        + " и далее не обновляется.",
    )

    add_heading(doc, "6.2. Эталон (численный якобиан FX1)", 2)
    add_body(
        doc,
        "Эталон не «таблица из литературы», а центральные разности правых частей FX1. "
        "При фиксированных остальных аргументах:",
    )
    add_body(
        doc,
        D(
            r"L_{\alpha}=\frac{\dot{\alpha}(\alpha_{0}+\Delta\alpha)-\dot{\alpha}(\alpha_{0}-\Delta\alpha)}{2\Delta\alpha}"
        ),
    )
    add_body(
        doc,
        "аналогично "
        + E(r"L_{q},L_{\delta e},L_{V},L_{\theta}")
        + " и все "
        + E("M_{*}")
        + " по "
        + E(r"\dot{q}")
        + ". Шаги: "
        + E(r"\Delta\alpha=\Delta q=\Delta\delta e=\Delta\theta=10^{-4}")
        + ", "
        + E(r"\Delta V=0{,}05")
        + " м/с. "
        + E(r"\theta_{\mathrm{trim}}")
        + " считается один раз в "
        + E(r"(x_{0},u_{0})")
        + ". "
        + E(r"\theta_{\mathrm{FX1}}(t)")
        + " пересчитывается каждый такт ОФК-2 из текущего "
        + E(r"(x,u)")
        + ". Фильтр эталон не использует (нет theory-anchor).",
    )
    add_table(
        doc,
        ["Параметр", "θ_trim", "Старт фильтра 1,3·θ_trim"],
        [
            ["α0, θ0", "0,212 рад", "—"],
            ["q0", "0", "—"],
            ["δe0", "−0,125 рад", "—"],
            ["V0", "80 м/с", "—"],
            ["Lα", "−0,4961", "−0,6449"],
            ["Lq", "1,000", "1,300"],
            ["Lδe", "−0,03118", "−0,04054"],
            ["Lv", "−0,002958", "−0,003845"],
            ["Lθ", "≈ 0", "≈ 0"],
            ["Mα", "−0,2791", "−0,3628"],
            ["Mq", "−0,6877", "−0,8940"],
            ["Mδe", "−0,4244", "−0,5517"],
            ["Mv", "0,000570", "0,000741"],
            ["Mθ", "≈ 0", "≈ 0"],
        ],
    )

    add_heading(doc, "6.3. Equation-error EKF", 2)
    add_body(
        doc,
        "Динамика: "
        + E(r"\dot{\theta}=0")
        + ", "
        + E(r"Q=0")
        + ". Производные — конечные разности за "
        + E(r"\Delta t_{2}=0{,}02")
        + " с:",
    )
    add_body(
        doc,
        D(
            r"\dot{\alpha}_{\mathrm{fd}}=\frac{\delta\alpha_{k}-\delta\alpha_{k-1}}{\Delta t_{2}},\qquad "
            r"\dot{q}_{\mathrm{fd}}=\frac{q_{k}-q_{k-1}}{\Delta t_{2}}"
        ),
    )
    add_body(
        doc,
        "Измерение "
        + E(r"Z=[\dot{\alpha}_{\mathrm{fd}},\,\dot{q}_{\mathrm{fd}},\,a_{z}]^{\mathsf{T}}")
        + ". Матрица наблюдения "
        + E(r"H\in\mathbb{R}^{3\times 10}")
        + ":",
    )
    add_body(
        doc,
        D(
            r"H=\begin{bmatrix}"
            r"\phi^{\mathsf{T}} & 0\\"
            r"0 & \phi^{\mathsf{T}}\\"
            r"k_{az}\phi^{\mathsf{T}} & 0"
            r"\end{bmatrix},\qquad k_{az}=-V/g"
        ),
    )
    add_body(
        doc,
        "Первая строка — уравнение "
        + E(r"\dot{\alpha}")
        + " (коэффициенты L), вторая — "
        + E(r"\dot{q}")
        + " (коэффициенты M), третья — "
        + E(r"a_{z}")
        + " только через L. "
        + E(r"R=\mathrm{diag}(0{,}025^{2},\,0{,}002^{2},\,0{,}023^{2})")
        + ". Начальная "
        + E(r"P_{0}")
        + " диагональная: 3σ покрывает смещение 30 % "
        + E(r"|\theta_{\mathrm{trim}}|")
        + " с абсолютным полом по каналам.",
    )
    add_body(
        doc,
        "Алгоритм шага. Предсказание: "
        + E(r"\hat{\theta}^{-}=\hat{\theta}^{+}")
        + ", "
        + E(r"P^{-}=P^{+}")
        + " (Q = 0). Если нет предыдущего такта или нет возбуждения, обновление не выполняется. "
        "Возбуждение, если хотя бы одно: "
        + E(r"|\delta\delta e|\ge 0{,}003")
        + ", "
        + E(r"|q|\ge 0{,}005")
        + ", "
        + E(r"|\delta\alpha|\ge 0{,}008")
        + ", "
        + E(r"|\delta V|\ge 0{,}05")
        + " м/с, "
        + E(r"|\delta\theta|\ge 0{,}003")
        + " (радианы, кроме V). Иначе шаг пропускается. Обновление:",
    )
    add_body(
        doc,
        D(
            r"S=H P^{-}H^{\mathsf{T}}+R,\qquad K=P^{-}H^{\mathsf{T}}S^{-1},\qquad "
            r"r=Z-H\hat{\theta}^{-}"
        ),
    )
    add_body(
        doc,
        D(
            r"\hat{\theta}^{+}=\hat{\theta}^{-}+Kr,\qquad "
            r"P^{+}=(I-KH)P^{-}(I-KH)^{\mathsf{T}}+KRK^{\mathsf{T}}"
        ),
    )
    add_body(
        doc,
        "Форма Джозефа для "
        + E("P")
        + " — та же, что в ОФК-1: она сохраняет симметрию и положительную определённость "
        "ковариации при большом числе тактов.",
    )
    add_body(
        doc,
        "Метрики: "
        + E(r"\Delta_{\mathrm{trim}}=\hat{\theta}-\theta_{\mathrm{trim}}")
        + ", "
        + E(r"\Delta_{\mathrm{inst}}=\hat{\theta}-\theta_{\mathrm{FX1}}(t)")
        + ". Lθ, Mθ остаются в состоянии фильтра (структура уравнений), на балансировке ≈ 0; "
        "в отчётных графиках: Lα, Lq, Lδe, Lv, Mα, Mq, Mδe, Mv.",
    )

    add_heading(doc, "6.4. Модель Hoff (legacy, только сравнение)", 2)
    add_body(
        doc,
        "Три регрессора "
        + E(r"\delta\alpha,\,q,\,\delta\delta e")
        + ", шесть коэффициентов. Уравнения без "
        + E(r"\delta V")
        + " и "
        + E(r"\delta\theta")
        + ". Те же "
        + E(r"\alpha,q,\delta e,a_{z}")
        + " и тот же старт +30 %. На навигацию и на основную ОФК-2 не влияет. "
        "Нужна как база: ошибки БНК по V и θ втекают в Lα, Lq, Mα.",
    )

    add_heading(doc, "7. Алгоритм полного цикла (псевдокод)", 1)
    add_body(
        doc,
        "Параметры прогона run_full_sim: "
        + E(r"T=60")
        + " с, "
        + E(r"\Delta t=10^{-3}")
        + " с, "
        + E(r"\Delta t_{\mathrm{GNSS}}=0{,}1")
        + " с, "
        + E(r"\Delta t_{2}=0{,}02")
        + " с.",
    )
    add_body(
        doc,
        "0) initsim: балансировка, x0, u0, q, Cbn, np_bins = истина. Якобиан → θ_trim. "
        "ОФК-1: x = 0, P = P0. ОФК-2 и Hoff: θ̂ = 1,3 θ_trim.",
    )
    add_body(
        doc,
        "Для i = 1…T/Δt: "
        "(1) RK4(FX1) → x, ω, a_f; каждые 0,01 с автопилот с doublet. "
        "(2) InsErrorGen → ω_m, a_m. "
        "(3) bins_step → q, Cbn, np_bins. "
        "(4) если i кратно 100: gnss(истина); на первом такте выравнивание V, h; z; ofk_step; "
        "feedback; x_I := 0; лог 10 Гц. "
        "(5) если уже был ОФК-1 и i кратно 20: собрать φ; якобиан FX1(t); ekf_step ОФК-2 и Hoff; лог 50 Гц.",
    )
    add_body(
        doc,
        "Следствие: между тактами ГНСС величины α, V, θ для ОФК-2 меняются только механизацией БИНС. "
        "q и az обновляются с IMU каждые 0,02 с.",
    )

    add_heading(doc, "8. Результаты прогона", 1)
    add_body(
        doc,
        "Ниже — результаты одного прогона с параметрами раздела 7 (60 с, doublet "
        + E(r"\pm 5^{\circ}")
        + " на интервале 10…15 с). Числа в таблицах получены тем же прогоном, что и графики.",
    )

    add_heading(doc, "8.1. Навигация: ОФК-1", 2)
    add_body(
        doc,
        "Траектория по истине FX1 приведена на рисунке 2, сравнение истина / БИНС / ОФК-1 / ГНСС "
        "по всем каналам — на рисунке 3.",
    )
    figure(doc, PLOTS / "latitude_vs_longitude.png", 11.5)
    caption(doc, "Рисунок 2 — Траектория полёта (истина FX1)")
    figure(doc, PLOTS / "bins_gnss_full.png", 16.2)
    caption(doc, "Рисунок 3 — Навигационные параметры: истина, БИНС, ОФК-1, ГНСС")
    add_body(
        doc,
        "Ошибка ОФК-1 относительно истины FX1 и полоса "
        + E(r"\pm 3\sqrt{P_{ii}}")
        + " по апостериорной ковариации — на рисунке 4. Согласованность ошибки с полосой означает, "
        "что "
        + E("Q")
        + " и "
        + E("R")
        + " настроены непротиворечиво: фильтр не занижает и не завышает свою точность.",
    )
    figure(doc, PLOTS / "ofk_error_vs_three_sigma_P.png", 15.2)
    caption(doc, "Рисунок 4 — Ошибка ОФК-1 и полоса ±3√Pii по шести каналам")
    order = ["fi", "lam", "h", "vn", "ve", "vh"]
    rows = []
    for key in order:
        st = nav[key]
        rows.append(
            [
                f"{st['name']}, {st['unit']}",
                _fmt(st["rms_ofk"]),
                _fmt(st["max_ofk"]),
                _fmt(st["sigma3_end"]),
                f"{st['inside']:.0f}",
            ]
        )
    add_table(
        doc,
        ["Канал", "СКО", "макс |ошибки|", "3σ в конце", "внутри ±3σ, %"],
        rows,
    )
    add_body(
        doc,
        "Ошибки координат пересчитаны в метры по радиусу Земли, интервал осреднения 5…60 с "
        "(после переходного процесса ковариации). Все шесть каналов лежат внутри "
        + E(r"\pm 3\sqrt{P_{ii}}")
        + ". Достигнутая точность существенно выше точности одиночного измерения ГНСС "
        "(≈32 м по координатам, 0,2 м/с по скорости) — это и есть эффект комплексирования. "
        "Обратная связь вводится каждые 0,1 с, поэтому дрейф БИНС между тактами мал; "
        "автономный уход БИНС этим прогоном не оценивается.",
    )

    add_heading(doc, "8.2. Идентификация: ОФК-2", 2)
    add_body(
        doc,
        "Сходимость оценок от старта "
        + E(r"1{,}3\,\theta_{\mathrm{trim}}")
        + " к эталону — на рисунке 5, те же оценки с полосой "
        + E(r"\pm 3\sigma")
        + " — на рисунке 6. Основное уточнение приходится на интервал doublet: вне манёвра "
        "условие возбуждения не выполняется и шаг обновления пропускается.",
    )
    figure(doc, PLOTS / "ofk2_params_time.png", 15.0)
    caption(doc, "Рисунок 5 — Сходимость оценок L*, M* к эталону")
    figure(doc, PLOTS / "ofk2_params_three_sigma.png", 15.0)
    caption(doc, "Рисунок 6 — Оценки L*, M* и полоса ±3σ")
    add_body(
        doc,
        "Входы фильтра (α, q, az), невязки equation-error и итоговое "
        + E(r"\Delta=\hat{\theta}-\theta_{\mathrm{trim}}")
        + " — на рисунке 7. Невязки без выраженного смещения: структура модели измерений адекватна.",
    )
    figure(doc, PLOTS / "ofk2_ekf.png", 15.0)
    caption(doc, "Рисунок 7 — Входы ОФК-2, невязки и Δ относительно эталона")
    add_body(
        doc,
        "Дрейф самого эталона "
        + E(r"\theta_{\mathrm{FX1}}(t)")
        + " относительно "
        + E(r"\theta_{\mathrm{trim}}")
        + " показан на рисунке 8: на манёвре точка линеаризации уходит, поэтому "
        + E(r"\Delta_{\mathrm{trim}}")
        + " и "
        + E(r"\Delta_{\mathrm{inst}}")
        + " различаются.",
    )
    figure(doc, PLOTS / "ofk2_theory_drift.png", 15.0)
    caption(doc, "Рисунок 8 — Дрейф эталона FX1 относительно балансировки")
    rows = []
    for c in coeff:
        rows.append(
            [
                c["name"],
                _fmt(c["theory"], 4),
                _fmt(c["start"], 4),
                _fmt(c["est"], 4),
                _fmt(c["delta"], 4),
                _fmt(c["sigma3"], 4),
                f"{c['rel']:.1f}".replace(".", ","),
            ]
        )
    add_table(
        doc,
        ["Коэфф.", "θ_trim", "старт", "оценка", "Δ_trim", "3σ", "|Δ|/|θ|, %"],
        rows,
    )
    add_body(
        doc,
        "Лучше всего восстанавливаются коэффициенты, прямо возбуждаемые рулём высоты: "
        + E(r"M_{\delta e},\ M_{q},\ L_{q},\ L_{\alpha}")
        + " — отклонение от эталона несколько процентов. Хуже всего "
        + E(r"M_{V},\ L_{\delta e},\ L_{V}")
        + ": они малы по абсолютной величине и слабо наблюдаемы на коротком продольном манёвре, "
        "поэтому относительная ошибка велика при малой абсолютной. Для большинства коэффициентов "
        + E(r"|\Delta|")
        + " сопоставимо с расчётным "
        + E(r"3\sigma")
        + ", то есть фильтр адекватно оценивает собственную точность.",
    )

    add_heading(doc, "9. Что не входит в текущий алгоритм", 1)
    add_body(
        doc,
        "Нет параметра-множителя ошибок ГНСС/БИНС и нет серии прогонов по уровню ошибок навигации. "
        "ОФК-1 не корректирует ориентацию. az0 заморожен. Q ОФК-2 нулевой. Lθ, Mθ неидентифицируемы на балансировке.",
    )

    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    print("DOCX:", build())
