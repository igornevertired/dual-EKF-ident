"""Математика FX1 + ОФК-2 для сверки (стиль изложения как в дипломе).

Запуск::

    poetry run python docs/build_ofk2_math_for_review.py
"""

from __future__ import annotations

import re
from pathlib import Path

import latex2mathml.converter
import mathml2omml
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import parse_xml
from docx.oxml.ns import qn
from docx.shared import Cm, Inches, Pt

M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
OUT = Path(__file__).resolve().parent / "ОФК-2_математика_для_сверки.docx"
PLOTS = Path(__file__).resolve().parents[1] / "src" / "plots"


def latex_to_omath_xml(latex: str) -> str:
    mml = latex2mathml.converter.convert(latex)
    omml = mathml2omml.convert(mml)
    if "xmlns:m=" not in omml:
        omml = omml.replace("<m:oMath>", f'<m:oMath xmlns:m="{M_NS}">', 1)
    return omml


def add_omath(paragraph, latex: str) -> None:
    omml = latex_to_omath_xml(latex)
    omml = re.sub(r'\sxmlns:m="[^"]*"', "", omml)
    wrapped = (
        f'<m:oMath xmlns:m="{M_NS}">'
        + omml.replace("<m:oMath>", "").replace("</m:oMath>", "")
        + "</m:oMath>"
    )
    paragraph._p.append(parse_xml(wrapped))


def add_display(doc: Document, latex: str) -> None:
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(6)
    add_omath(p, latex)


def add_runs_with_math(p, text: str) -> None:
    parts = re.split(r"(\$[^$]+\$)", text)
    for part in parts:
        if not part:
            continue
        if part.startswith("$") and part.endswith("$") and len(part) > 2:
            add_omath(p, part[1:-1])
        else:
            p.add_run(part)


def set_run_font(run, *, bold=False, size=12, name="Times New Roman"):
    run.bold = bold
    run.font.size = Pt(size)
    run.font.name = name
    r = run._element
    rpr = r.get_or_add_rPr()
    rfonts = rpr.get_or_add_rFonts()
    rfonts.set(qn("w:eastAsia"), name)
    rfonts.set(qn("w:cs"), name)


def style_doc(doc: Document) -> None:
    section = doc.sections[0]
    section.top_margin = Cm(2.0)
    section.bottom_margin = Cm(2.0)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(1.5)
    style = doc.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    pf = style.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.space_after = Pt(6)


def heading(doc: Document, text: str, level: int = 1) -> None:
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14 if level == 1 else 10 if level == 2 else 8)
    p.paragraph_format.space_after = Pt(6)
    add_runs_with_math(p, text)
    for run in p.runs:
        set_run_font(run, bold=True, size=14 if level == 1 else 13 if level == 2 else 12)


def para(doc: Document, text: str, *, first_indent: bool = True) -> None:
    p = doc.add_paragraph()
    if first_indent:
        p.paragraph_format.first_line_indent = Cm(1.25)
    add_runs_with_math(p, text)
    for run in p.runs:
        set_run_font(run)


def bullets(doc: Document, items: list[str]) -> None:
    for item in items:
        p = doc.add_paragraph(style="List Bullet")
        add_runs_with_math(p, item)
        for run in p.runs:
            set_run_font(run)


def add_figure(doc: Document, path: Path, caption: str, *, width_in: float = 5.8) -> None:
    if not path.is_file():
        para(doc, f"[рисунок не найден: {path.name}]", first_indent=False)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(width_in))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(caption)
    set_run_font(r, size=11)
    r.italic = True


def build() -> Path:
    doc = Document()
    style_doc(doc)

    t = doc.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run(
        "Математические модели контура: FX1 и ОФК-2"
    )
    set_run_font(r, bold=True, size=16)

    st = doc.add_paragraph()
    st.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = st.add_run(
        "для сверки с научным руководителем "
        "(изложение по структуре диплома: нелинейная модель ЛА → линеаризация → ОФК-2)"
    )
    set_run_font(r, size=11)
    r.italic = True

    para(
        doc,
        "Ниже приведены математические модели так, как они реализованы в программе. "
        "Нелинейная модель пространственного движения самолёта (FX1) совпадает по структуре "
        "с моделью из дипломной работы (порт FX1.m). ОФК-2 — отдельный блок идентификации "
        "аэродинамических коэффициентов по линейной модели около балансировки. "
        "Прошу проверить уравнения.",
    )

    # =====================================================================
    heading(doc, "1. Модель пространственного движения самолёта (FX1)")
    para(
        doc,
        "Для формирования реалистичной траектории полёта используется нелинейная модель "
        "динамики самолёта. Моделирование включает инициализацию вектора состояния и управления, "
        "балансировку, интегрирование уравнений движения (RK4, шаг $10^{-3}$ с) и выдачу "
        "идеальных показаний ДУС/ДЛУ для последующего контура БИНС–ГНСС–ОФК-1–ОФК-2.",
    )

    # ---- 1.1 general ----
    heading(doc, "1.1. Уравнения динамики самолёта в общем виде", 2)
    para(
        doc,
        "Согласно второму закону Ньютона уравнение динамики центра масс объекта имеет вид:",
    )
    add_display(doc, r"m\frac{d\mathbf{V}_a}{dt}=\mathbf{P}+\mathbf{F}_{\mathrm{aero}}+m\mathbf{g}_{\Gamma}")
    para(
        doc,
        "где $\\mathbf{V}_a$ — абсолютная скорость центра масс самолёта; "
        "$\\mathbf{P}$ — сила тяги; $\\mathbf{F}_{\\mathrm{aero}}$ — аэродинамическая сила; "
        "$\\mathbf{g}_{\\Gamma}$ — ускорение гравитационного поля Земли.",
    )
    para(
        doc,
        "Связь абсолютной скорости $\\mathbf{V}_a$ с земной скоростью $\\mathbf{V}$ "
        "и вращением Земли $\\boldsymbol{\\omega}_e$:",
    )
    add_display(doc, r"\mathbf{V}_a=\mathbf{V}+\boldsymbol{\omega}_e\times\mathbf{r}")
    para(
        doc,
        "где $\\mathbf{r}$ — радиус-вектор центра масс в географической системе координат (ГСК). "
        "Поступательным движением Земли пренебрегаем. Тогда",
    )
    add_display(doc, r"\frac{d\mathbf{r}}{dt}=\mathbf{V}+\boldsymbol{\omega}_e\times\mathbf{r}")
    para(doc, "Подставляя связь скоростей, получаем:")
    add_display(
        doc,
        r"m\frac{d\mathbf{V}}{dt}=\mathbf{P}+\mathbf{F}_{\mathrm{aero}}+m\mathbf{g}_{\Gamma}"
        r"-m\boldsymbol{\omega}_e\times\mathbf{V}-m\boldsymbol{\omega}_e\times(\boldsymbol{\omega}_e\times\mathbf{r})",
    )
    para(
        doc,
        "Центробежный член учитывается в ускорении силы тяжести:",
    )
    add_display(doc, r"\mathbf{g}=\mathbf{g}_{\Gamma}-\boldsymbol{\omega}_e\times(\boldsymbol{\omega}_e\times\mathbf{r})")
    para(doc, "Итоговое уравнение движения центра масс:")
    add_display(
        doc,
        r"m\frac{d\mathbf{V}}{dt}=\mathbf{P}+\mathbf{F}_{\mathrm{aero}}+m\mathbf{g}"
        r"-m\boldsymbol{\omega}_e\times\mathbf{V}",
    )

    # ---- 1.2 body ----
    heading(doc, "1.2. Модель динамики самолёта в связанной системе координат (ССК)", 2)
    para(
        doc,
        "Уравнение движения центра масс проектируется на оси связанной системы координат. "
        "Абсолютная угловая скорость самолёта в ССК $\\boldsymbol{\\omega}_{bi}^{b}$ связана "
        "с угловой скоростью относительно Земли:",
    )
    add_display(
        doc,
        r"\boldsymbol{\omega}_{be}^{b}=\boldsymbol{\omega}_{bi}^{b}-\boldsymbol{\omega}_{ie}^{b},"
        r"\quad \boldsymbol{\omega}_{ie}^{b}=C_{gb}\boldsymbol{\omega}_{ie}^{g}",
    )
    para(
        doc,
        "где $C_{gb}$ — матрица направляющих косинусов перехода из ГСК в ССК; "
        "$\\boldsymbol{\\omega}_{ie}^{g}=[\\Omega_e\\cos\\varphi,\\,\\Omega_e\\sin\\varphi,\\,0]^{\\top}$.",
    )

    heading(doc, "1.2.1. Коэффициенты аэродинамических сил", 3)
    para(doc, "Уравнения для коэффициентов аэродинамических сил (как в FX1.m / коде):")
    add_display(
        doc,
        r"C_y=C_{y0}+C_y^{\alpha}\alpha^{\circ}+C_y^{\delta_V}\delta_V+C_y^{\varphi}\varphi_{\mathrm{st}}",
    )
    add_display(
        doc,
        r"C_x=C_{x0}+A C_y+B C_y^{2}"
        r"+\bigl(C_x^{\delta_V}+C_x^{\alpha\delta_V}\alpha^{\circ}+C_x^{\alpha^{2}\delta_V}(\alpha^{\circ})^{2}\bigr)\delta_V",
    )
    add_display(
        doc,
        r"+\bigl(C_x^{\varphi}+C_x^{\alpha\varphi}\alpha^{\circ}+C_x^{\alpha^{2}\varphi}(\alpha^{\circ})^{2}\bigr)\varphi_{\mathrm{st}}",
    )
    add_display(doc, r"C_z=C_z^{\beta}\beta^{\circ}+C_z^{\delta_N}\delta_N")
    para(
        doc,
        "где $C_x,C_y,C_z$ — коэффициенты лобовой, подъёмной и боковой силы; "
        "$A,B$ — параметры поляры; $\\alpha^{\\circ},\\beta^{\\circ}$ — угол атаки и скольжения в градусах "
        "(в коде: $\\alpha^{\\circ}=\\alpha\\cdot 180/\\pi+\\alpha_{\\mathrm{kr}}$); "
        "$\\delta_V,\\delta_N$ — руль высоты и руль направления; "
        "$\\varphi_{\\mathrm{st}}$ — угол установки стабилизатора.",
    )

    heading(doc, "1.2.2. Плотность, скорость, скоростной напор", 3)
    para(doc, "Плотность воздуха на высоте $H$:")
    add_display(
        doc,
        r"\rho(H)=\rho_0\left(\frac{288.16-0.0066\,H}{288.16}\right)^{4.255}",
    )
    para(doc, "Модуль вектора земной скорости центра масс:")
    add_display(doc, r"V=\sqrt{V_x^{2}+V_y^{2}+V_z^{2}}")
    para(doc, "Скоростной напор:")
    add_display(doc, r"q_{\mathrm{dyn}}=\tfrac12\rho(H)\,V^{2}\,S\,\|\mathbf{g}_g\|")
    para(
        doc,
        "где $S$ — площадь крыла; в коде множитель $\\|\\mathbf{g}_g\\|$ берётся из модели Земли "
        "($\\|\\mathrm{gtg}\\|$).",
    )

    heading(doc, "1.2.3. Аэродинамические силы и тяга в ССК", 3)
    para(doc, "Воздушная скорость относительно ветра и углы:")
    add_display(
        doc,
        r"v_{ax}=V_x-V_{wx},\quad v_{ay}=V_y-V_{wy},\quad v_{az}=V_z-V_{wz}",
    )
    add_display(
        doc,
        r"\alpha=-\mathrm{atan2}(v_{ay},v_{ax}),\quad"
        r"\beta=\arcsin(v_{az}/V_a),\quad"
        r"V_a=\sqrt{v_{ax}^{2}+v_{ay}^{2}+v_{az}^{2}}",
    )
    para(doc, "Аэродинамические силы в проекции на оси ССК:")
    add_display(
        doc,
        r"F_x^{b}=C_x q_{\mathrm{dyn}}\cos\alpha-C_y q_{\mathrm{dyn}}\sin\alpha",
    )
    add_display(
        doc,
        r"F_y^{b}=C_x q_{\mathrm{dyn}}\sin\alpha+C_y q_{\mathrm{dyn}}\cos\alpha",
    )
    add_display(doc, r"F_z^{b}=C_z q_{\mathrm{dyn}}")
    para(doc, "Сила тяги:")
    add_display(doc, r"P=\delta_T P_{\max}\left(\frac{\rho(H)}{\rho_0}\right)^{0.75}")

    heading(doc, "1.2.4. Уравнение движения центра масс в ССК", 3)
    para(doc, "Матричное уравнение движения центра масс в ССК:")
    add_display(
        doc,
        r"\frac{d}{dt}\begin{bmatrix}V_x\\V_y\\V_z\end{bmatrix}"
        r"=\frac1m\begin{bmatrix}P\cos\varphi_P-F_x^{b}\\P\sin\varphi_P+F_y^{b}\\F_z^{b}\end{bmatrix}"
        r"+C_{gb}\bigl(-\boldsymbol{\omega}_{ie}^{g}\times(\boldsymbol{\omega}_{ie}^{g}\times\mathbf{r}_g)\bigr)",
    )
    add_display(
        doc,
        r"-2 C_{gb}\boldsymbol{\omega}_{ie}^{g}\times\mathbf{V}^{b}"
        r"-(\boldsymbol{\omega}_{bi}^{b}-C_{gb}\boldsymbol{\omega}_{ie}^{g})\times\mathbf{V}^{b}"
        r"+C_{gb}\mathbf{g}_g",
    )
    para(
        doc,
        "где $\\varphi_P$ — угол установки двигателей; $\\mathbf{V}^{b}=[V_x,V_y,V_z]^{\\top}$; "
        "$\\mathbf{g}_g$ — ускорение силы тяжести в ГСК.",
    )
    para(doc, "Для подсистемы БИНС выдаётся удельное ускорение без гравитации и переносных членов:")
    add_display(
        doc,
        r"\mathbf{a}_f^{b}=\frac1m\begin{bmatrix}P\cos\varphi_P-F_x^{b}\\P\sin\varphi_P+F_y^{b}\\F_z^{b}\end{bmatrix}",
    )

    heading(doc, "1.2.5. Матрица $C_{gb}$ и радиус-вектор в ГСК", 3)
    para(
        doc,
        "Матрица направляющих косинусов $C_{gb}$ переводит вектор из географической СК "
        "в связанную: $\\mathbf{v}^{b}=C_{gb}\\mathbf{v}^{g}$. "
        "Оси ГСК в модели FX1: $X_g$ — на север, $Y_g$ — вверх по местной вертикали, "
        "$Z_g$ — на восток (гравитация $\\mathbf{g}_g=[0,-g,0]^{\\top}$).",
    )
    para(
        doc,
        "Ориентация ССК относительно ГСК задаётся тремя углами Крылова "
        "(курс $\\psi$, тангаж $\\vartheta$, крен $\\gamma$). "
        "Переход ГСК$\\to$ССК — произведение трёх элементарных поворотов "
        "в порядке: сначала курс вокруг вертикали $Y_g$, затем тангаж вокруг "
        "промежуточной оси $Z'$, затем крен вокруг продольной оси $X''$:",
    )
    add_display(doc, r"C_{gb}=R_x(\gamma)\,R_z(\vartheta)\,R_y(\psi).")
    para(doc, "Элементарные матрицы поворота (правая система, столбец-вектор слева):")
    add_display(
        doc,
        r"R_y(\psi)=\begin{bmatrix}"
        r"\cos\psi & 0 & -\sin\psi \\"
        r"0 & 1 & 0 \\"
        r"\sin\psi & 0 & \cos\psi"
        r"\end{bmatrix},\quad"
        r"R_z(\vartheta)=\begin{bmatrix}"
        r"\cos\vartheta & \sin\vartheta & 0 \\"
        r"-\sin\vartheta & \cos\vartheta & 0 \\"
        r"0 & 0 & 1"
        r"\end{bmatrix},\quad"
        r"R_x(\gamma)=\begin{bmatrix}"
        r"1 & 0 & 0 \\"
        r"0 & \cos\gamma & \sin\gamma \\"
        r"0 & -\sin\gamma & \cos\gamma"
        r"\end{bmatrix}.",
    )
    para(
        doc,
        "Перемножая $R_x(\\gamma)\\,R_z(\\vartheta)\\,R_y(\\psi)$ и раскрывая произведения "
        "тригонометрических функций, получаем явную матрицу направляющих косинусов "
        "(та же, что в функции ``c_gb`` модели FX1):",
    )
    add_display(
        doc,
        r"C_{gb}="
        r"\begin{bmatrix}"
        r"\cos\psi\cos\vartheta & \sin\vartheta & -\sin\psi\cos\vartheta \\"
        r"-\cos\psi\sin\vartheta\cos\gamma+\sin\psi\sin\gamma & "
        r"\cos\vartheta\cos\gamma & "
        r"\cos\psi\sin\gamma+\sin\psi\sin\vartheta\cos\gamma \\"
        r"\cos\psi\sin\vartheta\sin\gamma+\sin\psi\cos\gamma & "
        r"-\cos\vartheta\sin\gamma & "
        r"\cos\psi\cos\gamma-\sin\psi\sin\vartheta\sin\gamma"
        r"\end{bmatrix}.",
    )
    para(
        doc,
        "Обратный переход ССК$\\to$ГСК: $C_{bg}=C_{gb}^{\\top}$ "
        "(матрица ортогональна, $\\det C_{gb}=1$).",
    )
    para(doc, "Радиус-вектор в ГСК:")
    add_display(
        doc,
        r"\mathbf{r}_g=\begin{bmatrix}"
        r"-R_1 e^{2}\sin\varphi\cos\varphi \\"
        r"R_1(1-e^{2}\sin^{2}\varphi) \\"
        r"0"
        r"\end{bmatrix}",
    )
    para(
        doc,
        "где $e^{2}$ — квадрат эксцентриситета эллипсоида Земли; "
        "$R_1,R_2$ — радиусы кривизны из модели Земли на текущих $(H,\\varphi,\\lambda)$.",
    )

    heading(doc, "1.2.6. Производные углов атаки и скольжения", 3)
    add_display(
        doc,
        r"\dot\alpha=-\frac{\dot V_y\,v_{ax}-\dot V_x\,v_{ay}}{v_{ax}^{2}+v_{ay}^{2}}",
    )
    add_display(
        doc,
        r"\dot\beta=\frac{\dot V_z V_a^{2}-v_{az}(v_{ax}\dot V_x+v_{ay}\dot V_y+v_{az}\dot V_z)}"
        r"{\sqrt{v_{ax}^{2}+v_{ay}^{2}}\,V_a^{2}}",
    )
    para(doc, "Угловые скорости в скоростной СК:")
    add_display(
        doc,
        r"\omega_{\alpha x}=\omega_{be,x}\cos\alpha-\omega_{be,y}\sin\alpha,\quad"
        r"\omega_{\alpha y}=\omega_{be,x}\sin\alpha+\omega_{be,y}\cos\alpha,\quad"
        r"\omega_{\alpha z}=\omega_{be,z}",
    )

    heading(doc, "1.2.7. Аэродинамические моменты", 3)
    para(doc, "Безразмерные коэффициенты моментов:")
    add_display(
        doc,
        r"m_x=(m_x^{\delta_N}+m_x^{\alpha\delta_N}\alpha^{\circ})\delta_N"
        r"+(m_x^{\beta}+m_x^{\alpha\beta}\alpha^{\circ})\beta^{\circ}+m_x^{\delta_E}\delta_E",
    )
    add_display(
        doc,
        r"+(m_x^{\omega_x}+m_x^{\alpha\omega_x}\alpha^{\circ}+m_x^{\alpha^{2}\omega_x}(\alpha^{\circ})^{2})"
        r"\omega_{\alpha x}\frac{\ell}{2V}"
        r"+(m_x^{\omega_y}+m_x^{\alpha\omega_y}\alpha^{\circ})\omega_{\alpha y}\frac{\ell}{2V}",
    )
    add_display(
        doc,
        r"m_y=m_y^{\beta}\beta^{\circ}+m_y^{\delta_N}\delta_N"
        r"+(m_y^{\omega_x}+m_y^{\alpha\omega_x}\alpha^{\circ}+m_y^{\alpha^{2}\omega_x}(\alpha^{\circ})^{2})"
        r"\omega_{\alpha x}\frac{\ell}{2V}",
    )
    add_display(
        doc,
        r"+(m_y^{\omega_y}+m_y^{\alpha\omega_y}\alpha^{\circ}+m_y^{\alpha^{2}\omega_y}(\alpha^{\circ})^{2})"
        r"\omega_{\alpha y}\frac{\ell}{2V}+m_y^{\dot\beta}\dot\beta\frac{\ell}{2V}",
    )
    add_display(
        doc,
        r"m_z=m_{z0}+m_z^{\alpha}\alpha^{\circ}+m_z^{\alpha^{2}}(\alpha^{\circ})^{2}"
        r"+m_z^{\delta_V}\delta_V+m_z^{\varphi}\varphi_{\mathrm{st}}",
    )
    add_display(
        doc,
        r"+m_z^{\omega_z}\omega_{\alpha z}\frac{b_a}{V}+m_z^{\dot\alpha}\dot\alpha\frac{b_a}{V}"
        r"+(x_T-25)\,C_y\cdot 0.01",
    )
    para(doc, "Моменты в связанной СК:")
    add_display(
        doc,
        r"M_x=m_x q_{\mathrm{dyn}}\ell\cos\alpha+m_y q_{\mathrm{dyn}}\ell\sin\alpha",
    )
    add_display(
        doc,
        r"M_y=-m_x q_{\mathrm{dyn}}\ell\sin\alpha+m_y q_{\mathrm{dyn}}\ell\cos\alpha",
    )
    add_display(doc, r"M_z=m_z q_{\mathrm{dyn}} b_a")
    para(
        doc,
        "где $\\ell$ — размах крыла; $b_a$ — средняя аэродинамическая хорда; "
        "$\\delta_E$ — элероны.",
    )

    heading(doc, "1.2.8. Уравнения вращательного движения", 3)
    add_display(doc, r"\Delta_J=J_{xx}J_{yy}-J_{xy}^{2}")
    add_display(
        doc,
        r"\dot\omega_x=\frac1{\Delta_J}\Bigl("
        r"J_{yy}M_x+J_{xy}M_y+J_{xy}(J_{xx}+J_{yy}-J_{zz})\omega_x\omega_z"
        r"+(J_{yy}^{2}-J_{yy}J_{zz}+J_{xy}^{2})\omega_y\omega_z\Bigr)",
    )
    add_display(
        doc,
        r"\dot\omega_y=\frac1{\Delta_J}\Bigl("
        r"J_{xy}M_x+J_{xx}M_y-(J_{xx}^{2}-J_{xx}J_{zz}+J_{xy}^{2})\omega_x\omega_z"
        r"+J_{xy}(J_{xx}+J_{yy}-J_{zz})\omega_y\omega_z\Bigr)",
    )
    add_display(
        doc,
        r"\dot\omega_z=\frac1{J_{zz}}\Bigl("
        r"M_z-(J_{yy}-J_{xx})\omega_x\omega_y-J_{xy}(\omega_y^{2}-\omega_x^{2})\Bigr)",
    )

    heading(doc, "1.2.9. Кинематика траектории и углов ориентации", 3)
    para(doc, "Проекции земной скорости на оси ГСК:")
    add_display(
        doc,
        r"V_{xg}=V_x\cos\psi\cos\vartheta"
        r"-V_y(\cos\psi\sin\vartheta\cos\gamma-\sin\psi\sin\gamma)"
        r"+V_z(\sin\psi\cos\gamma+\cos\psi\sin\vartheta\sin\gamma)",
    )
    add_display(
        doc,
        r"V_{yg}=V_x\sin\vartheta+V_y\cos\vartheta\cos\gamma-V_z\cos\vartheta\sin\gamma",
    )
    add_display(
        doc,
        r"V_{zg}=-V_x\sin\psi\cos\vartheta"
        r"+V_y(\cos\psi\sin\gamma+\sin\psi\sin\vartheta\cos\gamma)"
        r"+V_z(\cos\psi\cos\gamma-\sin\psi\sin\vartheta\sin\gamma)",
    )
    para(doc, "Угловая скорость ССК относительно ГСК:")
    add_display(
        doc,
        r"\boldsymbol{\omega}_{ge}^{g}=\begin{bmatrix}"
        r"V_{zg}/R_1 \\ V_{zg}\tan\varphi/R_1 \\ -V_{xg}/R_2"
        r"\end{bmatrix}",
    )
    add_display(
        doc,
        r"\boldsymbol{\omega}_{bg}^{b}=\boldsymbol{\omega}_{bi}^{b}"
        r"-C_{gb}(\boldsymbol{\omega}_{ge}^{g}+\boldsymbol{\omega}_{ie}^{g})",
    )
    para(doc, "Производные углов ориентации:")
    add_display(
        doc,
        r"\dot\psi=\frac{\omega_{bg,y}\cos\gamma-\omega_{bg,z}\sin\gamma}{\cos\vartheta}",
    )
    add_display(
        doc,
        r"\dot\vartheta=\omega_{bg,z}\cos\gamma+\omega_{bg,y}\sin\gamma",
    )
    add_display(doc, r"\dot\gamma=\omega_{bg,x}-\dot\psi\sin\vartheta")
    para(doc, "Производные географических координат:")
    add_display(
        doc,
        r"\dot\varphi=\frac{V_{xg}}{R_2},\quad"
        r"\dot\lambda=\frac{V_{zg}}{R_1\cos\varphi},\quad"
        r"\dot H=V_{yg}",
    )

    heading(doc, "1.2.10. Динамика приводов", 3)
    add_display(
        doc,
        r"\dot\delta_T=\frac{u_0-\delta_T}{\tau_T},\ "
        r"\dot\delta_V=\frac{u_1-\delta_V}{\tau_V},\ "
        r"\dot\delta_N=\frac{u_2-\delta_N}{\tau_N},\ "
        r"\dot\delta_E=\frac{u_3-\delta_E}{\tau_E}",
    )
    para(
        doc,
        "Ветер в модели: $\\dot{\\mathbf{V}}_w=\\mathbf{0}$. "
        "При $h\\le 15$ м включается упрощённая посадочная логика (как в FX1.m).",
    )

    # ---- init / trim ----
    heading(doc, "1.3. Инициализация модели", 2)
    para(doc, "Инициализация выполняется в несколько шагов:")
    bullets(
        doc,
        [
            "задаются конструктивные и аэродинамические параметры самолёта (вектор PAR);",
            "задаются шаг и время моделирования;",
            "инициализируется начальный вектор состояния;",
            "выполняется балансировка и формируется начальный вектор управления;",
            "инициализируется БИНС (и далее контур ГНСС/ОФК).",
        ],
    )
    para(doc, "Начальный вектор состояния (основные компоненты, как в коде $x\\in\\mathbb{R}^{25}$):")
    add_display(
        doc,
        r"\mathbf{x}_0=\bigl["
        r"V_x,V_y,V_z,\omega_x,\omega_y,\omega_z,\gamma,\psi,\vartheta,"
        r"X_g,H,Z_g,\varphi,\lambda,\ldots,"
        r"\delta_T,\delta_V,\delta_N,\delta_E,\ldots"
        r"\bigr]^{\top}",
    )

    heading(doc, "1.4. Балансировка самолёта", 2)
    para(
        doc,
        "Балансировка обеспечивает установившийся режим полёта. Ищутся балансировочные "
        "значения управления и угла атаки при заданных характерных параметрах "
        "$(V,H,\\ldots)$. Условия баланса сил и моментов сводятся к минимизации критерия",
    )
    add_display(
        doc,
        r"J=J_1^{2}+J_2^{2}+J_3^{2}+J_4^{2}+J_5^{2}+J_6^{2}",
    )
    para(
        doc,
        "где $J_1,J_2,J_3$ — невязки поступательного движения (ускорения по осям ССК), "
        "$J_4,J_5,J_6$ — невязки вращательного движения (как в уравнениях для "
        "$\\dot\\omega_x,\\dot\\omega_y,\\dot\\omega_z$ при требуемых угловых скоростях). "
        "Минимизация ведётся по $(\\delta_T,\\alpha,\\delta_V,\\delta_N,\\delta_E)$ "
        "(координатный спуск в программе).",
    )
    para(
        doc,
        "Манёвр для ОФК-2 задаётся программой управления на входе в FX1 "
        "(дублет руля высоты), а не отдельным блоком внутри $f(x,u,t)$.",
    )

    # =====================================================================
    heading(doc, "2. Связь FX1 с контуром ОФК-1 / ОФК-2")
    bullets(
        doc,
        [
            "FX1 интегрируется с шагом $10^{-3}$ с и выдаёт идеальные "
            "$\\boldsymbol{\\omega}_{bi}^{b}$, $\\mathbf{a}_f^{b}$.",
            "На них навешиваются ошибки ДУС/ДЛУ; БИНС считает NP и $C_b^n$.",
            "ГНСС — истина FX1 плюс шум; ОФК-1 оценивает ошибки БИНС (10 Гц).",
            "На ОФК-2: NP/$\\omega$/$a$ после ОФК-1, $C_{bn}$ с БИНС; "
            "$\\alpha$, $V$ из NP+$C_{bn}$; $q=\\omega_z$; $\\delta_e=\\delta_V$ из FX1.",
            "«Теория на балансировке» для ОФК-2 — численный якобиан FX1 в точке балансировки: "
            "частные производные $(\\dot\\alpha,\\dot q,\\dot V)$ по "
            "$(\\alpha,q,\\delta_e,V,\\vartheta)$.",
        ],
    )

    # =====================================================================
    heading(doc, "3. Линейная модель ОФК-2")
    para(
        doc,
        "Линейная модель ОФК-2 имеет ту же структуру, что и «теория на балансировке». "
        "Это линеаризация продольного движения FX1 около установившегося режима. "
        "В уравнениях фигурируют приращения от балансировочных значений "
        "$(\\alpha_0,q_0,V_0,\\delta_{e0},\\vartheta_0)$:",
    )
    add_display(
        doc,
        r"\delta\alpha=\alpha-\alpha_0,\quad"
        r"\delta q=q-q_0,\quad"
        r"\delta V=V-V_0",
    )
    add_display(
        doc,
        r"\delta\delta_e=\delta_e-\delta_{e0},\quad"
        r"\delta\vartheta=\vartheta-\vartheta_0",
    )
    para(doc, "Регрессор:")
    add_display(doc, r"\varphi=[\delta\alpha,\ \delta q,\ \delta\delta_e,\ \delta V]^{\top}")
    para(doc, "Три линейных дифференциальных уравнения:")
    add_display(
        doc,
        r"\dot{\alpha}=L_\alpha\delta\alpha+L_q\delta q+L_{\delta e}\delta\delta_e+L_V\delta V",
    )
    add_display(
        doc,
        r"\dot{q}=M_\alpha\delta\alpha+M_q\delta q+M_{\delta e}\delta\delta_e+M_V\delta V",
    )
    add_display(
        doc,
        r"\dot{V}=X_\alpha\delta\alpha+X_q\delta q+X_{\delta e}\delta\delta_e+X_V\delta V"
        r"+X_\vartheta\delta\vartheta",
    )
    bullets(
        doc,
        [
            "$X_\\vartheta$ — из якобиана FX1 ($\\approx -g$), не оценивается.",
            "$\\delta\\vartheta$: $\\vartheta\\approx\\alpha+\\arcsin(V_h/V)$ из NP после ОФК-1.",
            "Малые в балансировке коэффициенты не оцениваются (константы trim): "
            "$L_V$, $M_V$, $X_q$.",
            "Оцениваются: $L_\\alpha,L_q,L_{\\delta e},M_\\alpha,M_q,M_{\\delta e},"
            "X_\\alpha,X_{\\delta e},X_V$.",
        ],
    )

    heading(doc, "4. Измерение ОФК-2")
    para(
        doc,
        "Поскольку в линейной модели $\\alpha$, $q$, $V$ — приращения от установившегося режима, "
        "измерение формируется как отклонения от балансировки:",
    )
    add_display(
        doc,
        r"Z=[\delta\alpha,\ \delta q,\ \delta V]^{\top}"
        r"=[\alpha-\alpha_0,\ q-q_0,\ V-V_0]^{\top}",
    )
    para(doc, "Прогноз измерения из состояния фильтра:")
    add_display(doc, r"\hat{Z}=[\delta\hat\alpha,\ \delta\hat q,\ \delta\hat V]^{\top}")

    heading(doc, "5. Состояние и алгоритм ОФК-2 (EKF)")
    add_display(
        doc,
        r"\mathbf{x}=["
        r"L_\alpha,L_q,L_{\delta e},L_V,"
        r"M_\alpha,M_q,M_{\delta e},M_V,"
        r"X_\alpha,X_q,X_{\delta e},X_V,"
        r"\delta\alpha,\delta q,\delta V"
        r"]^{\top}",
    )
    para(
        doc,
        "Коэффициенты $L_*$, $M_*$, $X_*$ — неизвестные константы. "
        "В модели процесса их производные по времени нулевые: "
        "$\\dot L=\\dot M=\\dot X=0$ (на прогнозе не меняются сами; "
        "изменяет их коррекция по измерению $Z$). Прогноз отклонений:",
    )
    add_display(doc, r"\delta\alpha_{k+1}=\delta\alpha_k+\Delta t\,L\cdot\varphi_k")
    add_display(doc, r"\delta q_{k+1}=\delta q_k+\Delta t\,M\cdot\varphi_k")
    add_display(
        doc,
        r"\delta V_{k+1}=\delta V_k+\Delta t\,(X\cdot\varphi_k+X_\vartheta\delta\vartheta_k)",
    )
    para(
        doc,
        "Коррекция по невязке $\\nu=Z-\\hat Z$; обновление ковариации $P$ — по формуле Джозефа. "
        "Замороженные $L_V,M_V,X_q$ после шага возвращаются на значения балансировки, "
        "соответствующие строки и столбцы $P$ обнуляются.",
    )

    heading(doc, "6. Манёвр идентификации")
    para(
        doc,
        "Сейчас используется дублет руля высоты на входе в FX1: с момента $t=10$ с "
        "сначала $+5^{\\circ}$ в течение $2.5$ с, затем $-5^{\\circ}$ в течение $2.5$ с. "
        "На интервале импульса канал автопилота по рулю заморожен. "
        "Далее по плану исследования — другие манёвры (в том числе 3-2-1-1) "
        "и сравнение точности идентификации.",
    )

    heading(doc, "7. Текущие результаты (графики)")
    add_figure(
        doc,
        PLOTS / "ofk2_error_vs_three_sigma_P.png",
        "Рисунок — ошибка оцениваемых параметров ОФК-2 (оценка − балансировка) и полосы ±3σ",
    )
    add_figure(
        doc,
        PLOTS / "ofk2_params_time.png",
        "Рисунок — оценки параметров во времени против теории FX1(t) и балансировки",
    )

    note = doc.add_paragraph()
    note.paragraph_format.space_before = Pt(16)
    r = note.add_run(
        "Прошу отметить замечания по уравнениям FX1 и ОФК-2. "
        "После сверки — прогоны с другими манёврами."
    )
    set_run_font(r)
    r.italic = True

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(OUT)
    return OUT


if __name__ == "__main__":
    path = build()
    print(f"saved: {path}")
