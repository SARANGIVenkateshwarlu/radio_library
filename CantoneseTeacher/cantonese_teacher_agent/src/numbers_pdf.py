# -*- coding: utf-8 -*-
"""Render numbers_conversations.py data into a print-ready A4 PDF."""
import sys, shutil
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE / "src"))
sys.path.insert(0, str(BASE / "data"))

from pdf_generator import (register_cjk_fonts, styles, trilingual_lines, footer,
                           MARGIN, BLACK, GRAY, LIGHT, RULE)
from numbers_conversations import TOPICS

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Image,
                                KeepTogether, Table, TableStyle, PageBreak)

NUMBERS = [("零","ling4","zero"),("一","jat1","one"),("二 / 兩","ji6 / loeng5","two"),
           ("三","saam1","three"),("四","sei3","four"),("五","ng5","five"),
           ("六","luk6","six"),("七","cat1","seven"),("八","baat3","eight"),
           ("九","gau2","nine"),("十","sap6","ten"),("二十 / 廿","ji6 sap6 / jaa6","twenty"),
           ("一百","jat1 baak3","100"),("一千","jat1 cin1","1,000"),
           ("一萬","jat1 maan6","10,000"),("零點五","ling4 dim2 ng5","0.5")]


def build(out_path, image_path=None):
    register_cjk_fonts()
    st = styles()
    st["topic"] = st["section"].clone("topic", fontSize=15, leading=19,
                                      backColor=LIGHT, borderPadding=(3,5,3,5),
                                      spaceBefore=12, spaceAfter=6,
                                      keepWithNext=1)
    doc = SimpleDocTemplate(str(out_path), pagesize=A4,
                            topMargin=13*mm, bottomMargin=16*mm,
                            leftMargin=MARGIN, rightMargin=MARGIN,
                            title="Cantonese Numbers in Daily Conversations")
    story = []
    story.append(Paragraph("廣東話數字・日常對話", st["title"]))
    story.append(Paragraph("Cantonese Numbers in Daily Conversations — 30 Topics × 5 Q&A",
                           st["subtitle"]))
    if image_path and Path(image_path).exists():
        from PIL import Image as PImage
        max_w = (A4[0] - 2*MARGIN) * 0.45
        iw, ih = PImage.open(image_path).size
        h = max_w * ih / iw
        if h > 100*mm:
            h = 100*mm; max_w = h * iw / ih
        img = Image(str(image_path), width=max_w, height=h)
        img.hAlign = "CENTER"
        story.append(img)
        story.append(Paragraph("Reference chart: how to count in Cantonese",
                               st["caption"]))
    story.append(Paragraph("Basic Numbers 基本數字", st["section"]))
    st_cell = st["cell"]; st_b = st["cell_b"]
    rows = [["中文", "Jyutping", "English"]]
    rows += [[zh, jp, en] for zh, jp, en in NUMBERS]
    data = [[Paragraph(c, st_b) for c in rows[0]]] + \
           [[Paragraph(c, st_cell) for c in r] for r in rows[1:]]
    t = Table(data, colWidths=[45*mm, 55*mm, 60*mm], repeatRows=1)
    t.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (-1,0), 1.5, RULE),
        ("LINEBELOW", (0,0), (-1,0), 0.75, RULE),
        ("LINEBELOW", (0,-1), (-1,-1), 1.5, RULE),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [HexColor("#ffffff"), LIGHT]),
        ("TOPPADDING", (0,0), (-1,-1), 4), ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story.append(t)
    story.append(Paragraph(
        'Same colour = same word: <font color="#c0392b">中文</font> = '
        '<font color="#c0392b">Jyutping</font> = '
        '<font color="#c0392b">English</font>　同一隻色 = 同一個字',
        st["jyutping"]))

    for i, (en, zh, items) in enumerate(TOPICS, 1):
        story.append(Paragraph(f"{i}. {en}　{zh}", st["topic"]))
        qa_no = 0
        for k in range(0, len(items), 2):
            qa_no += 1
            for kind, c, j, e, seg in items[k:k+2]:
                prefix = f"{qa_no}. {kind} "
                segd = [{"chinese": a, "jyutping": b, "english": d}
                        for a, b, d in seg]
                story.append(KeepTogether(
                    trilingual_lines(prefix, c, j, e, segd, st)))

    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    print("PDF written:", out_path)


if __name__ == "__main__":
    img = sys.argv[2] if len(sys.argv) > 2 else None
    build(Path(sys.argv[1]), img)
