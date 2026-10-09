"""LangGraph node functions."""
from __future__ import annotations

import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

from . import asr, cleanup, config, jyutping_validate, library, pdf_gen
from .grouping import assign_blocks
from .jyutping_tool import to_jyutping
from .llm import (
    correct_chain,
    polish_chain,
    review_chain,
    translate_chain,
    vocab_chain,
)
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


def cleanup_audio(state: RadioState) -> dict:
    """Isolate voice / denoise before ASR when requested."""
    src = state["audio_path"]
    if not state.get("clean_audio"):
        return {"asr_audio_path": src, "cleanup_method": "off"}
    path, method = cleanup.clean_audio(src)
    return {"asr_audio_path": path, "cleanup_method": method}


def transcribe(state: RadioState) -> dict:
    provider = asr.get_asr(mock=state.get("mock_asr", True))
    audio = state.get("asr_audio_path") or state["audio_path"]
    segs = provider.transcribe(audio)
    for s in segs:  # keep the untouched spoken form as verbatim
        s.setdefault("verbatim_transcript", s.get("cantonese", ""))
    return {"segments": segs}


def _llm_workers() -> int:
    try:
        return max(1, int(os.getenv("LLM_MAX_WORKERS", "4")))
    except ValueError:
        return 4


def correct(state: RadioState) -> dict:
    chain = correct_chain()

    def _one(s: dict) -> dict:
        s = dict(s)
        out = chain.invoke({"text": s["cantonese"]}).content.strip()
        s["corrected"] = out
        s["normalized_cantonese"] = out
        s["uncertain"] = "〔?〕" in out
        return s

    with ThreadPoolExecutor(max_workers=_llm_workers()) as ex:
        segs = list(ex.map(_one, state["segments"]))
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

    def _one(s: dict) -> dict:
        s = dict(s)
        s["english"] = t_chain.invoke({"text": s["corrected"]}).content.strip()
        raw = v_chain.invoke({"text": s["corrected"]}).content.strip()
        vocab = []
        for line in raw.splitlines():
            parts = [p.strip() for p in line.split("|")]
            if len(parts) == 3:
                vocab.append({"word": parts[0], "jyutping": parts[1], "meaning": parts[2]})
        s["vocabulary"] = vocab
        return s

    with ThreadPoolExecutor(max_workers=_llm_workers()) as ex:
        segs = list(ex.map(_one, state["segments"]))
    return {"segments": segs}


def validate_output(state: RadioState) -> dict:
    """Deterministic QC: validate Jyutping and attach confidence/review flags.

    Runs without the LLM (guideline: never rely on the LLM to check its own
    Jyutping). Sets per-segment ``confidence``, ``uncertain_tokens``,
    ``needs_human_review`` and ``review_reason``.
    """
    quality = "good" if state.get("cleanup_method") in ("demucs", "ffmpeg") else "unknown"
    segs = []
    for s in state["segments"]:
        s = dict(s)
        s.setdefault("verbatim_transcript", s.get("cantonese", ""))
        s.setdefault("normalized_cantonese", s.get("corrected") or s.get("cantonese", ""))
        problems = jyutping_validate.validate_segment(s)
        tc = s.get("confidence")
        tc = float(tc) if isinstance(tc, (int, float)) else 0.0
        jyut_valid = not any(
            ("Jyutping" in p or "syllable" in p) for p in problems)

        s["confidence"] = {
            "audio": round(1.0 - float(s.get("no_speech_prob") or 0.0), 3),
            "transcription": round(tc, 3),
            "jyutping": 0.9 if jyut_valid else 0.3,
            "translation": 0.9 if s.get("english") else 0.0,
        }
        s["uncertain_tokens"] = [
            t for t in (s.get("jyutping") or "").split() if t == "〔?〕"]
        s.setdefault("alternative_readings", [])
        s["audio_quality"] = quality
        reasons = list(problems)
        if tc and tc < config.ASR_CONF_THRESHOLD:
            reasons.append(f"low ASR confidence ({tc:.2f})")
        s["needs_human_review"] = bool(reasons)
        s["review_reason"] = "; ".join(reasons) if reasons else None
        segs.append(s)
    return {"segments": segs, "audio_quality": quality}


def segment_blocks(state: RadioState) -> dict:
    """Group segments into 3-6 sentence blocks (topic change / pause)."""
    return {"segments": assign_blocks(state["segments"])}


def _extract_json(text: str) -> dict | None:
    text = (text or "").strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return None
    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _transcript_lines(segments: list[dict]) -> list[str]:
    return [
        f"{i}. CANT: {s.get('corrected')} | JYUT: {s.get('jyutping')} | ENG: {s.get('english')}"
        for i, s in enumerate(segments, 1)
    ]


def _review(segments: list[dict]) -> tuple[int, dict]:
    """Return (accuracy_score, review_dict). review_dict['status'] is set."""
    try:
        out = review_chain().invoke({"text": "\n".join(_transcript_lines(segments))}).content
    except Exception as exc:  # network / provider error
        return 0, {"status": "error", "reason": str(exc)}
    data = _extract_json(out)
    if data is None:
        return 0, {"status": "unparsed", "raw": (out or "")[:500]}
    try:
        data["accuracy_score"] = int(data.get("accuracy_score") or 0)
    except (TypeError, ValueError):
        data["accuracy_score"] = 0
    data["status"] = "ok"
    return data["accuracy_score"], data


def _polish(segments: list[dict], review: dict) -> list[dict] | None:
    """Re-translate flagged segments using the reviewer notes; None if no-op."""
    flagged = [n for n in (review.get("flagged_segments") or [])
               if isinstance(n, int) and 1 <= n <= len(segments)]
    if not flagged:
        return None
    notes = "\n".join(
        f"#{it.get('segment')}: {it.get('problem')} -> {it.get('suggestion')}"
        for it in (review.get("issues") or [])
    ) or "(none)"
    payload = "\n".join(
        f"{n}. CANT: {segments[n - 1].get('corrected')} | ENG: {segments[n - 1].get('english')}"
        for n in flagged
    )
    try:
        out = polish_chain().invoke({"issues": notes, "text": payload}).content
    except Exception:
        return None
    data = _extract_json(out) or {}
    new = [dict(s) for s in segments]
    changed = False
    for fx in data.get("fixes") or []:
        n = fx.get("segment")
        if not (isinstance(n, int) and 1 <= n <= len(new)):
            continue
        cant = str(fx.get("cantonese") or "").strip()
        eng = str(fx.get("english") or "").strip()
        if cant:
            new[n - 1]["corrected"] = cant
            new[n - 1]["jyutping"] = to_jyutping(cant)
            new[n - 1]["uncertain"] = "〔?〕" in new[n - 1]["jyutping"]
            changed = True
        if eng:
            new[n - 1]["english"] = eng
            changed = True
    return new if changed else None


def review_quality(state: RadioState) -> dict:
    """LLM review; if below target, re-translate flagged lines and keep the
    best-scoring run before the PDF is generated."""
    if not config.LLM_ENABLED:
        return {"quality_review": {"status": "skipped", "reason": "no LLM configured"}}

    segments = [dict(s) for s in state["segments"]]
    score, review = _review(segments)
    attempts = 0
    while (review.get("status") == "ok"
           and score < config.QREVIEW_TARGET
           and attempts < config.QREVIEW_MAX_ATTEMPTS):
        improved = _polish(segments, review)
        attempts += 1
        if improved is None:
            break
        new_score, new_review = _review(improved)
        if new_score >= score:  # keep the best-scoring run
            segments, score, review = improved, new_score, new_review
        if score >= config.QREVIEW_TARGET:
            break
    if review.get("status") == "ok":
        review["attempts"] = attempts
        review["target"] = config.QREVIEW_TARGET

    update: dict = {"segments": segments, "quality_review": review}
    if review.get("flagged_segments"):
        update["review_status"] = "partially_reviewed"
    return update


def _record(state: RadioState) -> dict:
    return {
        "recording_id": state["recording_id"],
        "station": state.get("station"),
        "recorded_at": state.get("recorded_at"),
        "duration_seconds": state.get("duration_seconds"),
        "audio_file": state["audio_path"],
        "segments": state["segments"],
        "review_status": state.get("review_status", "unreviewed"),
        "translation_source": "llm" if config.LLM_ENABLED else "mock",
        "cleanup_method": state.get("cleanup_method"),
        "audio_quality": state.get("audio_quality"),
        "quality_review": state.get("quality_review"),
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
