"""Shadowing PDF notes — a transcript split into ~1-minute parts.

Each part is a three-column table (Cantonese | Jyutping | English), one row per
segment, so a 5-minute MP3 becomes five 1-minute note pages. The document ends
with a vocabulary table (Cantonese | Jyutping | English).

Fonts use reportlab's built-in STSong-Light CID font (works on Windows with no
TrueType CJK fonts installed).
"""
from __future__ import annotations

from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
FONT = "STSong-Light"
_font_ready = False

_RULE = colors.HexColor("#bbbbbb")
_HEAD_BG = colors.HexColor("#e8eef7")
_ALT = colors.HexColor("#f4f6f8")


def _register_font():
    global _font_ready
    if not _font_ready:
        pdfmetrics.registerFont(UnicodeCIDFont(FONT))
        pdfmetrics.registerFontFamily(FONT, normal=FONT, bold=FONT,
                                      italic=FONT, boldItalic=FONT)
        _font_ready = True


def _styles():
    return {
        "title": ParagraphStyle("title", fontName=FONT, fontSize=18, leading=23,
                                textColor=colors.HexColor("#111111"), spaceAfter=2),
        "sub": ParagraphStyle("sub", fontName=FONT, fontSize=10, leading=14,
                              textColor=colors.HexColor("#555555"), spaceAfter=8),
        "section": ParagraphStyle("section", fontName=FONT, fontSize=13, leading=17,
                                  textColor=colors.HexColor("#2244aa"),
                                  spaceBefore=10, spaceAfter=4),
        "cell": ParagraphStyle("cell", fontName=FONT, fontSize=10.5, leading=14,
                               textColor=colors.HexColor("#111111")),
        "head": ParagraphStyle("head", fontName=FONT, fontSize=11, leading=14,
                               textColor=colors.HexColor("#2244aa")),
    }


def _ts(sec: float) -> str:
    sec = max(0, int(sec))
    m, s = divmod(sec, 60)
    return f"{m:02d}:{s:02d}"


def _chunks(segments: list[dict], seconds: int = 60) -> list[list[dict]]:
    """Group segments into consecutive ``seconds``-long parts."""
    ordered = sorted(segments, key=lambda s: s.get("start", 0.0))
    chunks, cur, cur_start = [], [], None
    for s in ordered:
        start = s.get("start", 0.0)
        if cur_start is None:
            cur_start = start
        elif start - cur_start >= seconds:
            chunks.append(cur)
            cur, cur_start = [], start
        cur.append(s)
    if cur:
        chunks.append(cur)
    return chunks


def _dedup_vocab(segments: list[dict]) -> list[dict]:
    seen, out = set(), []
    for s in segments:
        for v in s.get("vocabulary") or []:
            w = (v.get("word") or "").strip()
            if w and w not in seen:
                seen.add(w)
                out.append(v)
    return out


def _footer(canvas, doc):
    canvas.saveState()
    canvas.setFont(FONT, 9)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawCentredString(PAGE_W / 2, 9 * mm, f"Page 第 {doc.page} 頁")
    canvas.restoreState()


def build_shadow_pdf(segments: list[dict], audio_name: str, out,
                     title: str = "Shadowing Notes 跟讀筆記",
                     chunk_seconds: int = 60) -> object:
    """Write the shadowing notes PDF. ``out`` is a path or writable buffer."""
    _register_font()
    st = _styles()
    parts = _chunks(segments, chunk_seconds)
    vocab = _dedup_vocab(segments)

    doc = SimpleDocTemplate(out, pagesize=A4, topMargin=MARGIN, bottomMargin=MARGIN,
                            leftMargin=MARGIN, rightMargin=MARGIN, title=title)
    story = [
        Paragraph(title, st["title"]),
        Paragraph(f"{audio_name} · {len(segments)} segments · "
                  f"split into {len(parts)} part(s) · generated "
                  f"{datetime.now().strftime('%Y-%m-%d %H:%M')}", st["sub"]),
        Spacer(1, 2 * mm),
    ]

    header = [Paragraph("Cantonese 廣東話", st["head"]),
              Paragraph("Jyutping 粵拼", st["head"]),
              Paragraph("English 英文", st["head"])]

    for i, part in enumerate(parts, 1):
        start = part[0].get("start", 0.0)
        end = max(s.get("end", 0.0) for s in part)
        story.append(Paragraph(f"Part {i} · {_ts(start)} – {_ts(end)}", st["section"]))
        rows = [header]
        for s in part:
            canto = (s.get("normalized_cantonese") or s.get("corrected")
                     or s.get("cantonese") or "")
            rows.append([
                Paragraph(canto, st["cell"]),
                Paragraph(s.get("jyutping", "") or "", st["cell"]),
                Paragraph(s.get("english", "") or "", st["cell"]),
            ])
        t = Table(rows, colWidths=[40 * mm, 46 * mm, 74 * mm], repeatRows=1)
        t.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, _RULE),
            ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, _ALT]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(t)
        story.append(Spacer(1, 4 * mm))

    # Vocabulary table at the end of the notes.
    if vocab:
        story.append(Paragraph("Vocabulary 詞彙表", st["section"]))
        vheader = [Paragraph("Cantonese 中文", st["head"]),
                   Paragraph("Jyutping 粵拼", st["head"]),
                   Paragraph("English 意思", st["head"])]
        vrows = [vheader]
        for v in vocab:
            vrows.append([
                Paragraph(v.get("word", ""), st["cell"]),
                Paragraph(v.get("jyutping", "") or "", st["cell"]),
                Paragraph(v.get("meaning", "") or "", st["cell"]),
            ])
        vt = Table(vrows, colWidths=[40 * mm, 46 * mm, 74 * mm], repeatRows=1)
        vt.setStyle(TableStyle([
            ("GRID", (0, 0), (-1, -1), 0.4, _RULE),
            ("BACKGROUND", (0, 0), (-1, 0), _HEAD_BG),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, _ALT]),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(vt)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return out
