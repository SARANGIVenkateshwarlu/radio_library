"""Render a lesson JSON + image into a one-page, print-ready A4 PDF."""

import os
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    Image, KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

PAGE_W, PAGE_H = A4
MARGIN = 15 * mm
BLACK = HexColor("#111111")
GRAY = HexColor("#555555")
RULE = HexColor("#000000")
LIGHT = HexColor("#f2f2f2")

# Word-by-word colour coding: the same colour marks the same word across the
# Cantonese, Jyutping and English lines. Palette stays legible when printed.
PALETTE = ["#c0392b", "#1f618d", "#1e8449", "#b9770e", "#7d3c98", "#117a65"]


def _colored(segments, key, sep=" "):
    """Join one field of each segment, wrapping each in its palette colour."""
    parts = []
    for i, seg in enumerate(segments):
        color = PALETTE[i % len(PALETTE)]
        parts.append(f'<font color="{color}">{seg[key]}</font>')
    return sep.join(parts)


def register_cjk_fonts():
    regular = os.environ.get("DAIMON_CJK_FONT_REGULAR")
    bold = os.environ.get("DAIMON_CJK_FONT_BOLD")
    if regular and bold:
        pdfmetrics.registerFont(TTFont("CJK", regular))
        pdfmetrics.registerFont(TTFont("CJK-Bold", bold))
    else:  # fallback: system WenQuanYi Zen Hei (TrueType, covers TC/SC CJK)
        wqy = "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc"
        pdfmetrics.registerFont(TTFont("CJK", wqy))
        pdfmetrics.registerFont(TTFont("CJK-Bold", wqy))
    pdfmetrics.registerFontFamily(
        "CJK", normal="CJK", bold="CJK-Bold", italic="CJK", boldItalic="CJK-Bold")


def styles():
    return {
        "title": ParagraphStyle("title", fontName="CJK-Bold", fontSize=21,
                                leading=26, textColor=BLACK, spaceAfter=2),
        "subtitle": ParagraphStyle("subtitle", fontName="CJK", fontSize=12,
                                   leading=15, textColor=GRAY, spaceAfter=6),
        "section": ParagraphStyle("section", fontName="CJK-Bold", fontSize=15,
                                  leading=19, textColor=BLACK, spaceBefore=10,
                                  spaceAfter=5),
        "cantonese": ParagraphStyle("cantonese", fontName="CJK-Bold", fontSize=16,
                                    leading=20, textColor=BLACK),
        "jyutping": ParagraphStyle("jyutping", fontName="CJK", fontSize=13,
                                   leading=16.5, textColor=HexColor("#333333")),
        "english": ParagraphStyle("english", fontName="CJK", fontSize=13,
                                  leading=16.5, textColor=GRAY, spaceAfter=7),
        "caption": ParagraphStyle("caption", fontName="CJK", fontSize=11,
                                  leading=14, textColor=GRAY, alignment=1),
        "cell": ParagraphStyle("cell", fontName="CJK", fontSize=11.5, leading=15,
                               textColor=BLACK),
        "cell_b": ParagraphStyle("cell_b", fontName="CJK-Bold", fontSize=11.5,
                                 leading=15, textColor=BLACK),
    }


def trilingual_lines(prefix, cantonese, jyutping, english, segments, st):
    """Render a sentence as colour-matched lines when segments are available.

    Line 1: Cantonese (each word in its own colour)
    Line 2: Jyutping (same word -> same colour)
    Line 3: English gloss word-by-word (same colour), then full translation.
    """
    if segments:
        return [
            Paragraph(f"{prefix}{_colored(segments, 'chinese', sep='')}",
                      st["cantonese"]),
            Paragraph(f"&nbsp;&nbsp;&nbsp;{_colored(segments, 'jyutping')}",
                      st["jyutping"]),
            Paragraph(f"&nbsp;&nbsp;&nbsp;{_colored(segments, 'english')}",
                      st["jyutping"]),
            Paragraph(f"&nbsp;&nbsp;&nbsp;<i>{english}</i>", st["english"]),
        ]
    return [
        Paragraph(f"{prefix}{cantonese}", st["cantonese"]),
        Paragraph(f"&nbsp;&nbsp;&nbsp;{jyutping}", st["jyutping"]),
        Paragraph(f"&nbsp;&nbsp;&nbsp;{english}", st["english"]),
    ]


def sentence_block(idx, s, st):
    return trilingual_lines(f"{idx}. ", s["cantonese"], s["jyutping"],
                            s["english"], s.get("segments"), st)


def qa_block(idx, q, st):
    return (
        trilingual_lines(f"Q{idx}. ", q["question_cantonese"],
                         q["question_jyutping"], q["question_english"],
                         q.get("question_segments"), st)
        + trilingual_lines(f"A{idx}. ", q["answer_cantonese"],
                           q["answer_jyutping"], q["answer_english"],
                           q.get("answer_segments"), st)
    )


def vocab_table(vocab, st):
    header = ["Chinese 中文", "Jyutping 粵拼", "POS 詞性", "English 意思", "Example 例句"]
    rows = [[Paragraph(h, st["cell_b"]) for h in header]]
    for v in vocab:
        rows.append([
            Paragraph(v["chinese"], st["cell_b"]),
            Paragraph(v["jyutping"], st["cell"]),
            Paragraph(v["pos"], st["cell"]),
            Paragraph(v["english"], st["cell"]),
            Paragraph(v["example"], st["cell"]),
        ])
    widths = [26 * mm, 32 * mm, 22 * mm, 34 * mm, 66 * mm]
    t = Table(rows, colWidths=widths, repeatRows=1)
    t.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), 1.5, RULE),
        ("LINEBELOW", (0, 0), (-1, 0), 0.75, RULE),
        ("LINEBELOW", (0, -1), (-1, -1), 1.5, RULE),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [None, LIGHT]),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ]))
    return t


def footer(canvas, doc):
    canvas.saveState()
    canvas.setFont("CJK", 10)
    canvas.setFillColor(GRAY)
    canvas.drawCentredString(PAGE_W / 2, 9 * mm, f"Page 第 {doc.page} 頁")
    canvas.restoreState()


def build_pdf(lesson: dict, image_path: str, out_path: str,
              subtitle: str = "Image-based Lesson · 圖像教學"):
    register_cjk_fonts()
    st = styles()
    doc = SimpleDocTemplate(
        out_path, pagesize=A4,
        topMargin=MARGIN, bottomMargin=MARGIN,
        leftMargin=MARGIN, rightMargin=MARGIN,
        title=lesson["title"], author="Cantonese Class Teacher Agent",
    )
    story = [
        Paragraph(lesson["title"], st["title"]),
        Paragraph(subtitle, st["subtitle"]),
    ]

    img = Image(image_path)
    max_w = PAGE_W - 2 * MARGIN
    ratio = img.imageHeight / img.imageWidth
    img.drawWidth, img.drawHeight = max_w * 0.7, max_w * 0.7 * ratio
    img.hAlign = "CENTER"
    story.append(img)
    if lesson.get("image_caption"):
        story.append(Paragraph(lesson["image_caption"], st["caption"]))

    story.append(Paragraph("Ten Key Sentences 十個重點句子", st["section"]))
    story.append(Paragraph(
        "Same colour = same word: 中文 = Jyutping = English. "
        "同一顏色＝同一個詞，方便對照意思。", st["caption"]))
    for i, s in enumerate(lesson["sentences"], 1):
        story.append(KeepTogether(sentence_block(i, s, st)))

    if lesson.get("qa"):
        story.append(Paragraph("Questions & Answers 問答練習", st["section"]))
    for i, q in enumerate(lesson["qa"], 1):
        story.append(KeepTogether(qa_block(i, q, st)))

    story.append(Paragraph("Vocabulary 詞彙表", st["section"]))
    story.append(vocab_table(lesson["vocabulary"], st))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return out_path


if __name__ == "__main__":
    import json
    import sys

    lesson_json, image, out = sys.argv[1], sys.argv[2], sys.argv[3]
    lesson = json.loads(Path(lesson_json).read_text(encoding="utf-8"))
    build_pdf(lesson, image, out)
    print(f"PDF written to {out}")
