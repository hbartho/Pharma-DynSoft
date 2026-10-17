# -*- coding: utf-8 -*-
"""Génère GUIDE_INSTALLATION_LOCALE.pdf à partir de GUIDE_INSTALLATION_LOCALE.md (reportlab)."""
import os
import re
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.colors import HexColor, white
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, Preformatted, KeepTogether)

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "GUIDE_INSTALLATION_LOCALE.md")
OUT = os.path.join(HERE, "GUIDE_INSTALLATION_LOCALE.pdf")

TEAL, DARK, SLATE = HexColor("#0d9488"), HexColor("#0f172a"), HexColor("#475569")
LIGHT_BG, BORDER, CODE_BG = HexColor("#f0fdfa"), HexColor("#99f6e4"), HexColor("#f1f5f9")

styles = getSampleStyleSheet()
st_title = ParagraphStyle('T', parent=styles['Title'], fontSize=26, textColor=DARK, spaceAfter=8)
st_sub = ParagraphStyle('ST', parent=styles['Normal'], fontSize=13, textColor=TEAL, alignment=TA_CENTER)
st_h2 = ParagraphStyle('H2', parent=styles['Heading1'], fontSize=16, textColor=TEAL, spaceBefore=16, spaceAfter=6)
st_body = ParagraphStyle('B', parent=styles['Normal'], fontSize=10, textColor=SLATE, leading=15, spaceAfter=5)
st_li = ParagraphStyle('LI', parent=st_body, leftIndent=14, bulletIndent=2, spaceAfter=2)
st_cell = ParagraphStyle('C', parent=st_body, fontSize=9, leading=12, spaceAfter=0)
st_code = ParagraphStyle('CODE', parent=styles['Code'], fontSize=8, leading=10.5, backColor=CODE_BG,
                         borderPadding=6, leftIndent=4, spaceBefore=4, spaceAfter=8)


def inline(text):
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    text = re.sub(r"`(.+?)`", r"<font face='Courier' color='#0f172a'>\1</font>", text)
    return text


def build_table(rows):
    data = [[Paragraph(inline(c), st_cell) for c in r] for r in rows]
    ncols = len(rows[0])
    widths = [17 * cm / ncols] * ncols if ncols != 2 else [5.5 * cm, 11.5 * cm]
    t = Table(data, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), TEAL), ('TEXTCOLOR', (0, 0), (-1, 0), white),
        ('GRID', (0, 0), (-1, -1), 0.5, BORDER), ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [white, LIGHT_BG]),
        ('TOPPADDING', (0, 0), (-1, -1), 4), ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    for cell in data[0]:
        cell.style = ParagraphStyle('CH', parent=st_cell, textColor=white, fontName='Helvetica-Bold')
    return t


def parse(lines):
    story, i = [], 0
    while i < len(lines):
        line = lines[i]
        if line.startswith("# "):
            story += [Spacer(1, 3 * cm), Paragraph(inline(line[2:]), st_title),
                      Paragraph("Pack Docker • PostgreSQL local • Fonctionnement hors ligne", st_sub),
                      Spacer(1, 1 * cm)]
            i += 1
            while i < len(lines) and not lines[i].startswith("## "):
                if lines[i].strip():
                    story.append(Paragraph(inline(lines[i].strip()), st_body))
                i += 1
            story.append(PageBreak())
            continue
        if line.startswith("## "):
            story.append(Paragraph(inline(line[3:]), st_h2)); i += 1; continue
        if line.startswith("```"):
            i += 1; buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(lines[i]); i += 1
            story.append(Preformatted("\n".join(buf), st_code)); i += 1; continue
        if line.lstrip().startswith("|"):
            rows = []
            while i < len(lines) and lines[i].lstrip().startswith("|"):
                cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                if not all(re.fullmatch(r"-+", c) for c in cells):
                    rows.append(cells)
                i += 1
            story.append(KeepTogether([build_table(rows), Spacer(1, 6)])); continue
        m = re.match(r"^\s*(\d+)\.\s+(.*)", line)
        if m:
            txt = m.group(2); i += 1
            while i < len(lines) and lines[i].startswith("   ") and not lines[i].lstrip().startswith(("|", "-", "`")) \
                    and not re.match(r"^\s*\d+\.\s", lines[i]):
                txt += " " + lines[i].strip(); i += 1
            story.append(Paragraph(f"<b>{m.group(1)}.</b> {inline(txt)}", st_li)); continue
        if line.startswith("- "):
            txt = line[2:]; i += 1
            while i < len(lines) and lines[i].startswith("  ") and lines[i].strip() and not lines[i].lstrip().startswith("-"):
                txt += " " + lines[i].strip(); i += 1
            story.append(Paragraph(inline(txt), st_li, bulletText="•")); continue
        if not line.strip():
            i += 1; continue
        txt = line.strip(); i += 1
        while i < len(lines) and lines[i].strip() and not lines[i].startswith(("#", "|", "-", "```", " ")) \
                and not re.match(r"^\d+\.\s", lines[i]):
            txt += " " + lines[i].strip(); i += 1
        story.append(Paragraph(inline(txt), st_body))
    return story


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont('Helvetica', 8); canvas.setFillColor(SLATE)
    canvas.drawString(2 * cm, 1.2 * cm, "DynSoft Pharma – Guide d'installation locale")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
    canvas.restoreState()


if __name__ == "__main__":
    with open(SRC, encoding="utf-8") as f:
        lines = f.read().splitlines()
    doc = SimpleDocTemplate(OUT, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                            topMargin=2 * cm, bottomMargin=2 * cm, title="DynSoft Pharma – Installation locale")
    doc.build(parse(lines), onFirstPage=footer, onLaterPages=footer)
    print(f"PDF généré : {OUT}")
