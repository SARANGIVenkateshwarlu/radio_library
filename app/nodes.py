"""LangGraph node functions."""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

from . import asr, config, library, pdf_gen
from .jyutping_tool import to_jyutping
from .llm import correct_chain, translate_chain, vocab_chain
from .state import RadioState

_FN_RE = re.compile(r"(?P<date>\d{4}-\d{2}-\d{2})_(?P<station>[^_]+)_(?P<dur>[^.]+)")


def _duration_to_seconds(raw: str) -> int:
    m = re.match(r"(\d+)\s*(min|hr|h|s)", raw.lower())
    if not m:
        return 0
    val, unit = int(m.group(1)), m.group(2)
    return val * {"s": 1, "min": 60, "h": 3600, "hr": 3600}[unit]


def load_audio(state: RadioState) -> dict:
    p = Path(state["audio_path"])
    m = _FN_RE.search(p.name)
    date = m.group("date") if m else datetime.now().strftime("%Y-%m-%d")
    station = m.group("station") if m else "UNKNOWN"
    dur = _duration_to_seconds(m.group("dur")) if m else 0
    return {
        "recording_id": f"{date}-{station.lower()}-001",
        "station": station,
        "recorded_at": f"{date}T08:00:00+08:00",
        "duration_seconds": dur,
        "review_status": "unreviewed",
        "errors": [],
    }


def transcribe(state: RadioState) -> dict:
    provider = asr.get_asr(mock=state.get("mock_asr", True))
    return {"segments": provider.transcribe(state["audio_path"])}


def correct(state: RadioState) -> dict:
    chain = correct_chain()
    segs = []
    for s in state["segments"]:
        s = dict(s)
        out = chain.invoke({"text": s["cantonese"]}).content.strip()
        s["corrected"] = out
        s["uncertain"] = "〔?〕" in out
        segs.append(s)
    return {"segments": segs}


def jyutping(state: RadioState) -> dict:
    segs = []
    for s in state["segments"]:
        s = dict(s)
        s["jyutping"] = to_jyutping(s["corrected"])
        if "〔?〕" in s["jyutping"]:
            s["uncertain"] = True
        segs.append(s)
    return {"segments": segs}


def translate(state: RadioState) -> dict:
    t_chain = translate_chain()
    v_chain = vocab_chain()
    segs = []
    for s in state["segments"]:
        s = dict(s)
        s["english"] = t_chain.invoke({"text": s["corrected"]}).content.strip()
        raw = v_chain.invoke({"text": s["corrected"]}).content.strip()
        vocab = []
        for line in raw.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3:
                vocab.append({"word": parts[0], "jyutping": parts[1], "meaning": parts[2]})
        s["vocabulary"] = vocab
        segs.append(s)
    return {"segments": segs}


def _record(state: RadioState) -> dict:
    return {
        "recording_id": state["recording_id"],
        "station": state.get("station"),
        "recorded_at": state.get("recorded_at"),
        "duration_seconds": state.get("duration_seconds"),
        "audio_file": state["audio_path"],
        "segments": state["segments"],
        "review_status": state.get("review_status", "unreviewed"),
    }


def _fmt_srt_ts(sec: float) -> str:
    ms = int(round((sec % 1) * 1000))
    m, s = divmod(int(sec), 60)
    h, m = divmod(m, 60)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def generate_pdf(state: RadioState) -> dict:
    rid = state["recording_id"]
    json_path = config.TRANSCRIPT_DIR / f"{rid}.json"
    srt_path = config.SUBTITLE_DIR / f"{rid}.srt"
    pdf_path = config.PDF_DIR / f"{rid}.pdf"

    json_path.write_text(json.dumps(_record(state), ensure_ascii=False, indent=2), encoding="utf-8")

    lines = []
    for i, s in enumerate(state["segments"], 1):
        lines.append(
            f"{i}\n{_fmt_srt_ts(s['start'])} --> {_fmt_srt_ts(s['end'])}\n"
            f"{s['corrected']}\n{s['jyutping']}\n{s['english']}\n"
        )
    srt_path.write_text("\n".join(lines), encoding="utf-8")

    pdf_gen.generate_pdf(_record(state), pdf_path)
    return {
        "transcript_json_path": str(json_path),
        "srt_path": str(srt_path),
        "pdf_path": str(pdf_path),
    }


def save_to_library(state: RadioState) -> dict:
    rec = _record(state)
    rec.update(
        pdf_file=state["pdf_path"],
        transcript_json=state["transcript_json_path"],
        srt_file=state["srt_path"],
    )
    library.save_recording(rec)
    return {}
