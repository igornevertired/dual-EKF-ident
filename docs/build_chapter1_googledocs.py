#!/usr/bin/env python3
"""Глава 1 в .docx без OMML — совместимо с Google Docs."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

OUT = Path(__file__).resolve().parent / "Глава_1_Математические_модели_GoogleDocs.docx"

GREEK = {
    "alpha": "α",
    "beta": "β",
    "gamma": "γ",
    "delta": "δ",
    "theta": "θ",
    "psi": "ψ",
    "varphi": "φ",
    "phi": "φ",
    "lambda": "λ",
    "omega": "ω",
    "Omega": "Ω",
    "rho": "ρ",
    "chi": "χ",
    "pi": "π",
    "nu": "ν",
    "Delta": "Δ",
    "varphi": "φ",
}


def _brace_arg(s: str, start: int) -> tuple[str, int]:
    """Считать аргумент {...} начиная с позиции '{'."""
    assert s[start] == "{"
    depth = 0
    i = start
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1 : i], i + 1
        i += 1
    return s[start + 1 :], len(s)


def latex_to_text(latex: str) -> str:
    s = latex
    # Многократный проход команд с аргументами в скобках
    for _ in range(12):
        changed = False
        for cmd, fmt in (
            ("dfrac", lambda a, b: f"({a})/({b})"),
            ("frac", lambda a, b: f"({a})/({b})"),
        ):
            token = "\\" + cmd
            while token + "{" in s:
                i = s.find(token + "{")
                a, j = _brace_arg(s, i + len(token))
                if j >= len(s) or s[j] != "{":
                    break
                b, k = _brace_arg(s, j)
                s = s[:i] + fmt(a, b) + s[k:]
                changed = True
        for cmd, fmt in (
            ("sqrt", lambda a: f"√({a})"),
            ("mathrm", lambda a: a),
            ("mathsf", lambda a: a),
            ("mathbf", lambda a: a),
            ("boldsymbol", lambda a: a),
            ("dot", lambda a: a + "\u0307"),
        ):
            token = "\\" + cmd
            while token + "{" in s:
                i = s.find(token + "{")
                a, j = _brace_arg(s, i + len(token))
                s = s[:i] + fmt(a) + s[j:]
                changed = True
        # ^{...} _{...}
        for op, join in (("^", ""), ("_", "")):
            token = op + "{"
            while token in s:
                i = s.find(token)
                a, j = _brace_arg(s, i + 1)
                s = s[:i] + op + a + s[j:]
                changed = True
        if not changed:
            break

    s = s.replace(r"\left(", "(").replace(r"\right)", ")")
    s = s.replace(r"\left[", "[").replace(r"\right]", "]")
    s = s.replace(r"\cdot", "·").replace(r"\times", "×")
    s = s.replace(r"\quad", "  ").replace(r"\,", " ").replace("~", " ")
    s = s.replace(r"\pm", "±")
    for name, sym in sorted(GREEK.items(), key=lambda x: -len(x[0])):
        s = s.replace("\\" + name, sym)
    for name in ("sin", "cos", "arctan", "arcsin", "max"):
        s = s.replace("\\" + name, name)
    s = s.replace("{,}", ",")
    s = s.replace("\\", "")
    s = s.replace("{", "").replace("}", "")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def set_run_font(run, size: int = 14, bold: bool = False, italic: bool = False):
    run.font.name = "Times New Roman"
    run._element.rPr.rFonts.set(qn("w:eastAsia"), "Times New Roman")
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    run.font.color.rgb = RGBColor(0, 0, 0)


def set_pf(p, first_line=True, align="justify", space_after=6):
    pf = p.paragraph_format
    pf.space_after = Pt(space_after)
    pf.space_before = Pt(0)
    pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    pf.first_line_indent = Cm(1.25 if first_line else 0)
    p.alignment = {
        "justify": WD_ALIGN_PARAGRAPH.JUSTIFY,
        "center": WD_ALIGN_PARAGRAPH.CENTER,
        "left": WD_ALIGN_PARAGRAPH.LEFT,
    }[align]


def add_heading(doc, text, level=1):
    p = doc.add_paragraph()
    set_pf(p, first_line=False, align="left", space_after=12)
    run = p.add_run(text)
    set_run_font(run, size={1: 16, 2: 15, 3: 14}[level], bold=True)


def add_body(doc, text: str):
    if text.startswith("[[eq:") and text.endswith("]]") and text.count("[[eq:") == 1:
        latex = text[len("[[eq:") : -2]
        p = doc.add_paragraph()
        set_pf(p, first_line=False, align="center", space_after=10)
        run = p.add_run(latex_to_text(latex))
        set_run_font(run, size=13, italic=True)
        return

    p = doc.add_paragraph()
    set_pf(p, first_line=True, align="justify")
    pattern = re.compile(r"<<eq:(.+?)>>")
    pos = 0
    for m in pattern.finditer(text):
        if m.start() > pos:
            run = p.add_run(text[pos : m.start()])
            set_run_font(run, size=14)
        run = p.add_run(latex_to_text(m.group(1)))
        set_run_font(run, size=14, italic=True)
        pos = m.end()
    if pos < len(text):
        run = p.add_run(text[pos:])
        set_run_font(run, size=14)


def add_table(doc, headers, rows):
    table = doc.add_table(rows=1 + len(rows), cols=len(headers))
    table.style = "Table Grid"
    for j, h in enumerate(headers):
        cell = table.rows[0].cells[j]
        cell.text = ""
        run = cell.paragraphs[0].add_run(h)
        set_run_font(run, size=12, bold=True)
        cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
    for i, row in enumerate(rows):
        for j, val in enumerate(row):
            cell = table.rows[i + 1].cells[j]
            cell.text = ""
            run = cell.paragraphs[0].add_run(val)
            set_run_font(run, size=12)
    doc.add_paragraph()


def E(latex: str) -> str:
    return f"<<eq:{latex}>>"


def D(latex: str) -> str:
    return f"[[eq:{latex}]]"


def build() -> Path:
    # Импорт контента из основного билдера через повтор тех же вызовов
    from build_chapter1_docx import build as build_word

    # Переопределяем функции модуля build_chapter1_docx на google-совместимые
    import build_chapter1_docx as m

    m.OUT = OUT
    m.add_heading = add_heading
    m.add_body = add_body
    m.add_table = add_table
    m.E = E
    m.D = D
    m.set_run_font = set_run_font
    m.set_paragraph_format = set_pf
    # отключаем OMML
    m.add_omath_to_paragraph = lambda *a, **k: None
    return m.build()


if __name__ == "__main__":
    # Прямая сборка без хака импорта — копируем логику вызовов из исходника
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "ch1", Path(__file__).resolve().parent / "build_chapter1_docx.py"
    )
    ch1 = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ch1)

    ch1.OUT = OUT
    ch1.add_heading = add_heading
    ch1.add_body = add_body
    ch1.add_table = add_table
    ch1.E = E
    ch1.D = D
    print(ch1.build())
