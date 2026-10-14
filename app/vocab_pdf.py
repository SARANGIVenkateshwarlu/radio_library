"""Dictionary-style PDF of the whole VocabBank (a printable word list).

All vocabulary is de-duplicated and sorted by Jyutping (then word), and printed
as a three-column table (Word | Jyutping | Meaning) with a repeating header and
page numbers — like a study-mate dictionary you can print.
"""
from __future__ import annotations

from datetime import datetime

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
BLACK = HexColor("#111111")
GRAY = HexColor("#555555")
RULE = HexColor("#000000")
LIGHT = HexColor("#f4f6f8")
HEADER_BG = HexColor("#e8eef7")

_FONT = "STSong-Light"
_font_ready = False


def _register_font():
    global _font_ready
    if not _font_ready:
        pdfmetrics.registerFont(UnicodeCIDFont(_FONT))
        pdfmetrics.registerFontFamily(_FONT, normal=_FONT, bold=_FONT,
                                      italic=_FONT, boldItalic=_FONT)
        _font_ready = True


def _styles():
    return {
        "title": ParagraphStyle("title", fontName=_FONT, fontSize=19, leading=24,
                                textColor=BLACK, spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName=_FONT, fontSize=10.5, leading=14,
                              textColor=GRAY, spaceAfter=8),
        "cell": ParagraphStyle("cell", fontName=_FONT, fontSize=11, leading=15,
                               textColor=BLACK),
        "cell_b": ParagraphStyle("cell_b", fontName=_FONT, fontSize=11,
                                 leading=15, textColor=HexColor("#2244aa")),
        "head": ParagraphStyle("head", fontName=_FONT, fontSize=11.5, leading=15,
                               textColor=HexColor("#2244aa")),
    }


def _dedup_sorted(entries: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for e in entries:
        word = (e.get("word") or "").strip()
        if not word:
            continue
        seen.setdefault((word, e.get("jyutping", "")), e)
    return sorted(seen.values(),
                  key=lambda e: (e.get("jyutping", ""), e["word"]))


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(_FONT, 9)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(PAGE_W / 2, 9 * mm, f"Page 第 {doc.page} 頁")
    canvas.restoreState()


def build_vocab_pdf(entries: list[dict], out, title: str = "VocabBank 詞彙表"):
    """Write the dictionary PDF. ``out`` is a path or a writable buffer."""
    _register_font()
    st = _styles()
    rows_sorted = _dedup_sorted(entries)

    doc = SimpleDocTemplate(
        out, pagesize=A4, topMargin=MARGIN, bottomMargin=MARGIN,
        leftMargin=MARGIN, rightMargin=MARGIN, title=title,
    )
    story = [
        Paragraph(title, st["title"]),
        Paragraph(f"{len(rows_sorted)} words · generated "
                  f"{datetime.now().strftime('%Y-%m-%d %H:%M')} · "
                  "sorted by Jyutping · 按粵拼排序", st["sub"]),
        Spacer(1, 2 * mm),
    ]

    header = [Paragraph("Word 詞彙", st["head"]),
              Paragraph("Jyutping 粵拼", st["head"]),
              Paragraph("Meaning 意思", st["head"])]
    data = [header]
    for e in rows_sorted:
        data.append([
            Paragraph(e["word"], st["cell"]),
            Paragraph(e.get("jyutping", ""), st["cell_b"]),
            Paragraph(e.get("meaning", ""), st["cell"]),
        ])

    table = Table(data, colWidths=[30 * mm, 46 * mm, 94 * mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, HexColor("#cccccc")),
        ("BACKGROUND", (0, 0), (-1, 0), HEADER_BG),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, LIGHT]),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(table)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return out
