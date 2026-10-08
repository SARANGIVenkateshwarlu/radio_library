"""Bilingual PDF generation with reportlab (CID font for Cantonese)."""
from __future__ import annotations

import os
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

pdfmetrics.registerFont(UnicodeCIDFont("STSong-Light"))

TITLE = ParagraphStyle("title", fontName="STSong-Light", fontSize=16, leading=22)
META = ParagraphStyle("meta", fontName="STSong-Light", fontSize=9, leading=13, textColor="#666666")
CANTO = ParagraphStyle("canto", fontName="STSong-Light", fontSize=12, leading=17)
JYUT = ParagraphStyle("jyut", fontName="STSong-Light", fontSize=10, leading=14, textColor="#2244aa")
ENG = ParagraphStyle("eng", fontName="STSong-Light", fontSize=10.5, leading=14, textColor="#226622")
TS = ParagraphStyle("ts", fontName="STSong-Light", fontSize=9, leading=12, textColor="#999999")
WARN = ParagraphStyle("warn", fontName="STSong-Light", fontSize=9.5, leading=13,
                      textColor="#aa2222")


def _fmt_ts(sec: float) -> str:
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"[{h:02d}:{m:02d}:{s:02d}]"


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
    for seg in record.get("segments", []):
        story.append(Paragraph(_fmt_ts(seg.get("start", 0)), TS))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph("<b>Cantonese:</b>", META))
        story.append(Paragraph(seg.get("corrected") or seg.get("cantonese", ""), CANTO))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph("<b>Jyutping:</b>", META))
        story.append(Paragraph(seg.get("jyutping", ""), JYUT))
        story.append(Spacer(1, 1 * mm))
        story.append(Paragraph("<b>English:</b>", META))
        story.append(Paragraph(seg.get("english", ""), ENG))
        vocab = seg.get("vocabulary") or []
        if vocab:
            story.append(Spacer(1, 1 * mm))
            story.append(Paragraph("<b>Vocabulary:</b>", META))
            for v in vocab:
                story.append(Paragraph(
                    f"{v['word']} {v['jyutping']} — {v['meaning']}", ENG))
        story.append(Spacer(1, 5 * mm))

    # Aggregated vocabulary list at the bottom of the document.
    seen, all_vocab = set(), []
    for seg in record.get("segments", []):
        for v in seg.get("vocabulary") or []:
            if v["word"] not in seen:
                seen.add(v["word"])
                all_vocab.append(v)
    if all_vocab:
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph("<b>Vocabulary (全篇詞彙):</b>", TITLE.clone(
            "vocab_head", fontSize=13, leading=18)))
        story.append(Spacer(1, 2 * mm))
        for v in all_vocab:
            story.append(Paragraph(f"{v['word']} {v['jyutping']} — {v['meaning']}", ENG))
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
