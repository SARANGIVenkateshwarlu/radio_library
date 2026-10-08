"""Bilingual PDF generation with reportlab (CID font for Cantonese).

Layout: segments are grouped into blocks of 3-6 sentences (topic change /
pause). Each block prints all its Cantonese lines, then all its Jyutping lines,
then all its English lines. A deduplicated vocabulary table ends the document.
"""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

TITLE = ParagraphStyle("title", fontName="STSong-Light", fontSize=16, leading=22)
META = ParagraphStyle("meta", fontName="STSong-Light", fontSize=9, leading=13, textColor="#666666")
BLOCK = ParagraphStyle("block", fontName="STSong-Light", fontSize=11, leading=15,
                       textColor="#333333", spaceBefore=2, spaceAfter=3)
CANTO = ParagraphStyle("canto", fontName="STSong-Light", fontSize=12, leading=17)
JYUT = ParagraphStyle("jyut", fontName="STSong-Light", fontSize=10, leading=14, textColor="#2244aa")
ENG = ParagraphStyle("eng", fontName="STSong-Light", fontSize=10.5, leading=14, textColor="#226622")
TS = ParagraphStyle("ts", fontName="STSong-Light", fontSize=9, leading=12, textColor="#999999")
WARN = ParagraphStyle("warn", fontName="STSong-Light", fontSize=9.5, leading=13,
                      textColor="#aa2222")


def _fmt_ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def _blocks(segments: list[dict]) -> list[list[dict]]:
    grouped: dict[int, list[dict]] = {}
    for s in segments:
        grouped.setdefault(s.get("block", 0), []).append(s)
    return [grouped[k] for k in sorted(grouped)]


def generate_pdf(record: dict, out_path: str | Path) -> str:
    out_path = str(out_path)
    tmp_path = out_path + ".tmp"
    doc = SimpleDocTemplate(
        tmp_path, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=18 * mm,
        title=record["recording_id"],
    )
    story = [
        Paragraph(f"HK Radio Cantonese Transcript — {record['recording_id']}", TITLE),
        Spacer(1, 4 * mm),
        Paragraph(
            f"Station: {record.get('station','')} &nbsp;|&nbsp; "
            f"Recorded: {record.get('recorded_at','')} &nbsp;|&nbsp; "
            f"Audio: {record.get('audio_file','')} &nbsp;|&nbsp; "
            f"Status: {record.get('review_status','unreviewed')} &nbsp;|&nbsp; "
            "Personal study use only",
            META,
        ),
        Spacer(1, 6 * mm),
    ]
    if record.get("translation_source") == "mock":
        story.append(Paragraph(
            "<b>Note:</b> offline mock mode — English below is a rough gloss "
            "(or untranslated), not a real translation. Configure an LLM "
            "(see README) then re-run to get proper English.",
            WARN,
        ))
        story.append(Spacer(1, 4 * mm))

    for bi, block in enumerate(_blocks(record.get("segments", [])), 1):
        start = block[0].get("start", 0.0)
        end = block[-1].get("end", 0.0)
        story.append(Paragraph(
            f"<b>Block {bi}</b> &nbsp; [{_fmt_ts(start)} – {_fmt_ts(end)}]", BLOCK))
        for label, key, style in (
            ("Cantonese:", "corrected", CANTO),
            ("Jyutping:", "jyutping", JYUT),
            ("English:", "english", ENG),
        ):
            story.append(Paragraph(f"<b>{label}</b>", META))
            for j, s in enumerate(block, 1):
                if key == "corrected":
                    text = s.get("corrected") or s.get("cantonese", "")
                else:
                    text = s.get(key, "")
                mark = " 〔?〕" if s.get("uncertain") and "〔?〕" not in (text or "") else ""
                story.append(Paragraph(f"{j}. {text}{mark}", style))
            story.append(Spacer(1, 2 * mm))
        story.append(Spacer(1, 3 * mm))

    seen, vocab = set(), []
    for s in record.get("segments", []):
        for v in s.get("vocabulary") or []:
            if v.get("word") and v["word"] not in seen:
                seen.add(v["word"])
                vocab.append(v)
    if vocab:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>Vocabulary (全篇詞彙):</b>", TITLE.clone(
            "vocab_head", fontSize=13, leading=18)))
        story.append(Spacer(1, 2 * mm))
        data = [["Word", "Jyutping", "Meaning"]]
        data += [[v["word"], v.get("jyutping", ""), v.get("meaning", "")] for v in vocab]
        table = Table(data, colWidths=[32 * mm, 38 * mm, 100 * mm], repeatRows=1)
        table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), "STSong-Light"),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8eef7")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#2244aa")),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#bbbbbb")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ]))
        story.append(table)

    doc.build(story)
    try:
        os.replace(tmp_path, out_path)
    except PermissionError as exc:
        try:
            os.remove(tmp_path)
        except OSError:
            pass
        raise RuntimeError(
            f"Could not write {out_path} — the file is open in another program "
            "(e.g. a PDF viewer). Close it and run again."
        ) from exc
    return out_path
