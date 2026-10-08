"""VocabBank: aggregate vocabulary across recordings and build review quizzes.

Data is stored locally under ``metadata/``:
  * ``quiz_history.json``  — every quiz attempt and score
  * ``vocab_stats.json``   — per-word seen/correct counters (drives 70/30 review)

Vocabulary is collected from the SQLite library and from any transcript JSON
files, so every processed session (group) is represented.
"""
from __future__ import annotations

import csv
import io
import json
import random
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from . import config

HISTORY_PATH = config.METADATA_DIR / "quiz_history.json"
STATS_PATH = config.METADATA_DIR / "vocab_stats.json"

REVIEW_RATIO = 0.7
MIN_QUESTIONS = 6
MAX_QUESTIONS = 10

_CLIP_CACHE: dict[tuple, bytes | None] = {}


# --------------------------------------------------------------------------- #
# Storage helpers
# --------------------------------------------------------------------------- #
def _read_json(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


def load_stats() -> dict:
    return _read_json(STATS_PATH, {})


def save_stats(stats: dict) -> None:
    _write_json(STATS_PATH, stats)


def load_history() -> list:
    return _read_json(HISTORY_PATH, [])


def save_attempt(attempt: dict) -> None:
    history = load_history()
    history.append(attempt)
    _write_json(HISTORY_PATH, history)


# --------------------------------------------------------------------------- #
# Vocabulary collection
# --------------------------------------------------------------------------- #
def _entries_from_record(rec: dict) -> list[dict]:
    rid = rec.get("recording_id") or "unknown"
    audio = rec.get("audio_file")
    audio_name = Path(audio).name if audio else ""
    out = []
    for s in rec.get("segments", []) or []:
        sentence = s.get("corrected") or s.get("cantonese", "")
        for v in s.get("vocabulary") or []:
            word = (v.get("word") or "").strip()
            if not word:
                continue
            out.append({
                "recording_id": rid,
                "audio_file": audio,
                "audio_name": audio_name,
                "station": rec.get("station"),
                "recorded_at": rec.get("recorded_at"),
                "word": word,
                "jyutping": v.get("jyutping", ""),
                "meaning": v.get("meaning", ""),
                "sentence": sentence,
                "english": s.get("english", ""),
                "start": s.get("start", 0.0),
                "end": s.get("end", 0.0),
            })
    return out


def _iter_records():
    from . import library

    for rec in library.list_recordings():
        segs = json.loads(rec.get("transcript_json") or "[]")
        yield {**rec, "segments": segs}
    for path in sorted(config.TRANSCRIPT_DIR.glob("*.json")):
        rec = _read_json(path, None)
        if isinstance(rec, dict) and rec.get("segments"):
            yield rec


def collect_vocab() -> list[dict]:
    """All vocabulary entries, de-duplicated per (recording, word, jyutping)."""
    seen: dict[tuple, dict] = {}
    for rec in _iter_records():
        for e in _entries_from_record(rec):
            seen.setdefault((e["recording_id"], e["word"], e["jyutping"]), e)
    return list(seen.values())


def groups() -> dict[str, list[dict]]:
    """Vocabulary grouped by recording (one recorded session)."""
    out: dict[str, list[dict]] = {}
    for e in collect_vocab():
        out.setdefault(e["recording_id"], []).append(e)
    return out


def group_label(entries: list[dict]) -> str:
    e = entries[0]
    name = e.get("audio_name") or e["recording_id"]
    station = e.get("station") or ""
    date = (e.get("recorded_at") or "")[:10]
    return f"{name}  ·  {station} {date}  ·  {len(entries)} words".strip()


def vocab_csv(entries: list[dict]) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["word", "jyutping", "meaning", "recording_id", "sentence", "english"])
    for e in entries:
        w.writerow([e["word"], e["jyutping"], e["meaning"],
                    e["recording_id"], e["sentence"], e["english"]])
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Audio clips
# --------------------------------------------------------------------------- #
def clip_segment(audio_file: str | None, start: float, end: float,
                 pad: float = 0.25) -> bytes | None:
    """Return an MP3 clip for a sentence via ffmpeg, or None if unavailable."""
    if not audio_file or not Path(audio_file).exists():
        return None
    key = (audio_file, round(start, 2), round(end, 2))
    if key in _CLIP_CACHE:
        return _CLIP_CACHE[key]
    if shutil.which(config.FFMPEG_BINARY) is None:
        _CLIP_CACHE[key] = None
        return None
    ss = max(0.0, start - pad)
    duration = max(0.6, (end - start) + 2 * pad)
    cmd = [
        config.FFMPEG_BINARY, "-v", "quiet",
        "-ss", f"{ss:.2f}", "-i", audio_file, "-t", f"{duration:.2f}",
        "-vn", "-ac", "2", "-ar", "44100",
        "-codec:a", "libmp3lame", "-b:a", "128k", "-f", "mp3", "pipe:1",
    ]
    try:
        out = subprocess.run(cmd, capture_output=True, check=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        out = None
    _CLIP_CACHE[key] = out
    return out


# --------------------------------------------------------------------------- #
# Quiz building
# --------------------------------------------------------------------------- #
def _key(e: dict) -> str:
    return f"{e['word']}|{e.get('jyutping','')}"


def _similar_jyutping(a: str, b: str) -> bool:
    a, b = a or "", b or ""
    if not a or not b:
        return False
    return a.split(" ")[0] == b.split(" ")[0] or len(a) == len(b)


def _pick_distractors(entry: dict, pool: list[dict], field: str, n: int = 3) -> list[str]:
    cand = [p for p in pool
            if p["word"] != entry["word"] and p.get(field)
            and p.get(field) != entry.get(field)]
    same_topic = [p for p in cand if p["recording_id"] == entry["recording_id"]]
    if field == "jyutping":
        close = [p for p in cand if _similar_jyutping(p.get("jyutping", ""),
                                                       entry.get("jyutping", ""))]
        order = close + same_topic + cand
    else:
        order = same_topic + cand
    random.shuffle(order)
    out, seen = [], set()
    for p in order:
        val = p[field]
        if val in seen:
            continue
        seen.add(val)
        out.append(val)
        if len(out) >= n:
            break
    return out


def _make_question(entry: dict, pool: list[dict], kind: str) -> dict | None:
    """Character-free questions only (the learner reads Jyutping, not hanzi).

    * ``meaning``: prompt is the Jyutping, options are English meanings.
    * ``jyutping``: prompt is the English meaning, options are Jyutping (reverse).
    """
    if not entry.get("jyutping") or not entry.get("meaning"):
        return None
    if kind == "meaning":
        correct = entry["meaning"]
        prompt = f"What does “{entry['jyutping']}” mean?"
        opts = _pick_distractors(entry, pool, "meaning")
    elif kind == "jyutping":
        correct = entry["jyutping"]
        prompt = f"Which Jyutping means “{entry['meaning']}”?"
        opts = _pick_distractors(entry, pool, "jyutping")
    else:
        return None
    options = [correct] + opts
    if len(options) < 2:
        return None
    random.shuffle(options)
    return {"kind": kind, "word": entry["word"], "prompt": prompt,
            "options": options, "answer": correct, "entry": entry}


def build_quiz(n: int | None = None, review_ratio: float = REVIEW_RATIO) -> list[dict]:
    """Mixed quiz with ~review_ratio reviewed words and the rest new."""
    all_entries = collect_vocab()
    if len(all_entries) < 2:
        return []
    n = n or random.randint(MIN_QUESTIONS, MAX_QUESTIONS)
    stats = load_stats()
    review = [e for e in all_entries if stats.get(_key(e), {}).get("seen", 0) > 0]
    new = [e for e in all_entries if stats.get(_key(e), {}).get("seen", 0) == 0]

    target_review = min(round(n * review_ratio), len(review)) if review else 0
    target_new = n - target_review
    if target_new > len(new):
        target_new = len(new)
        target_review = min(n - target_new, len(review))
    if target_review + target_new < n:  # not enough new -> top up with review
        target_review = min(n - target_new, len(review))

    picked = random.sample(review, target_review) + random.sample(new, target_new)
    random.shuffle(picked)
    if not picked:
        picked = random.sample(all_entries, min(n, len(all_entries)))

    kinds = ["meaning", "jyutping"]
    random.shuffle(kinds)
    questions, used = [], set()
    for i, e in enumerate(picked):
        for kind in (kinds[i % len(kinds)], "meaning", "jyutping"):
            if (e["word"], kind) in used:
                continue
            q = _make_question(e, all_entries, kind)
            if q:
                used.add((e["word"], kind))
                questions.append(q)
                break
    return questions


def record_result(questions: list[dict], answers: list[str]) -> dict:
    """Persist a finished attempt and update per-word stats."""
    correct = sum(1 for q, a in zip(questions, answers) if a == q["answer"])
    total = len(questions)
    score = round(correct / total * 100) if total else 0
    attempt = {
        "ts": datetime.now().isoformat(timespec="seconds"),
        "total": total,
        "correct": correct,
        "wrong": total - correct,
        "score": score,
        "words": [q["word"] for q in questions],
    }
    save_attempt(attempt)

    stats = load_stats()
    for q, a in zip(questions, answers):
        k = _key(q["entry"])
        s = stats.setdefault(k, {"seen": 0, "correct": 0})
        s["seen"] += 1
        if a == q["answer"]:
            s["correct"] += 1
    save_stats(stats)
    return attempt
