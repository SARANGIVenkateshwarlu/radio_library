"""Pronunciation studio: personal phrase bank + shadowing helpers.

Local storage under ``metadata/``:
  * ``phrase_bank.json``  — cards: jyutping, english, audio, topic, created_at
  * ``phrase_reviews.json`` — {"YYYY-MM-DD": reviews_done} for streak tracking
  * ``recordings/``        — your own shadowing recordings (WAV)
"""
from __future__ import annotations

import csv
import io
import json
import shutil
import subprocess
import uuid
from datetime import date, datetime, timedelta
from pathlib import Path

from . import config

BANK_PATH = config.METADATA_DIR / "phrase_bank.json"
REVIEW_PATH = config.METADATA_DIR / "phrase_reviews.json"
REC_DIR = config.METADATA_DIR / "recordings"

REVIEW_TARGET = 10          # reviews/day to count as a streak day
NEW_CARDS_WEEK_TARGET = (35, 50)


def _read(path: Path, default):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return default


def _write(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(path)


# --------------------------------------------------------------------------- #
# Phrase bank
# --------------------------------------------------------------------------- #
def load_cards() -> list[dict]:
    return _read(BANK_PATH, [])


def save_cards(cards: list[dict]) -> None:
    _write(BANK_PATH, cards)


def add_card(jyutping: str = "", english: str = "", audio: str = "",
             topic: str = "") -> dict:
    cards = load_cards()
    card = {
        "id": uuid.uuid4().hex[:8],
        "jyutping": (jyutping or "").strip(),
        "english": (english or "").strip(),
        "audio": (audio or "").strip(),
        "topic": (topic or "").strip(),
        "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    cards.append(card)
    save_cards(cards)
    return card


def delete_card(card_id: str) -> None:
    save_cards([c for c in load_cards() if c.get("id") != card_id])


def new_cards_this_week(cards: list[dict] | None = None) -> int:
    cards = load_cards() if cards is None else cards
    monday = date.today() - timedelta(days=date.today().weekday())
    n = 0
    for c in cards:
        try:
            created = date.fromisoformat((c.get("created_at") or "")[:10])
        except ValueError:
            continue
        if created >= monday:
            n += 1
    return n


def export_csv(cards: list[dict] | None = None) -> str:
    cards = load_cards() if cards is None else cards
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["Jyutping", "English", "Audio", "Topic"])
    for c in cards:
        w.writerow([c.get("jyutping", ""), c.get("english", ""),
                    c.get("audio", ""), c.get("topic", "")])
    return buf.getvalue()


# --------------------------------------------------------------------------- #
# Review tracking (for the streak)
# --------------------------------------------------------------------------- #
def load_reviews() -> dict:
    return _read(REVIEW_PATH, {})


def save_reviews(reviews: dict) -> None:
    _write(REVIEW_PATH, reviews)


def log_reviews(n: int) -> int:
    reviews = load_reviews()
    key = date.today().isoformat()
    reviews[key] = reviews.get(key, 0) + int(n)
    save_reviews(reviews)
    return reviews[key]


def review_streak(target: int = REVIEW_TARGET) -> int:
    reviews = load_reviews()
    streak = 0
    d = date.today()
    while reviews.get(d.isoformat(), 0) >= target:
        streak += 1
        d -= timedelta(days=1)
    return streak


def days_met_target_this_week(target: int = REVIEW_TARGET) -> int:
    reviews = load_reviews()
    monday = date.today() - timedelta(days=date.today().weekday())
    return sum(
        1 for i in range(7)
        if reviews.get((monday + timedelta(days=i)).isoformat(), 0) >= target
    )


# --------------------------------------------------------------------------- #
# Shadowing helpers
# --------------------------------------------------------------------------- #
def segments_for_audio(audio_path: str | Path) -> list[dict]:
    """Segments of the transcript whose audio_file matches ``audio_path``."""
    from . import library

    name = Path(audio_path).name
    for rec in library.list_recordings():
        if Path(rec.get("audio_file") or "").name == name:
            return json.loads(rec.get("transcript_json") or "[]")
    for path in sorted(config.TRANSCRIPT_DIR.glob("*.json")):
        rec = _read(path, None)
        if rec and Path(rec.get("audio_file") or "").name == name:
            return rec.get("segments", [])
    return []


def clip_segment(audio_file: str | None, start: float, end: float,
                 speed: float = 1.0, pad: float = 0.25) -> bytes | None:
    """An MP3 clip of one sentence, optionally speed-adjusted (pitch kept)."""
    if not audio_file or not Path(audio_file).exists():
        return None
    if shutil.which(config.FFMPEG_BINARY) is None:
        return None
    ss = max(0.0, start - pad)
    duration = max(0.6, (end - start) + 2 * pad)
    af = ["-filter:a", f"atempo={speed}"] if abs(speed - 1.0) > 1e-6 else []
    cmd = [config.FFMPEG_BINARY, "-v", "quiet",
           "-ss", f"{ss:.2f}", "-i", audio_file, "-t", f"{duration:.2f}",
           "-vn", *af, "-ac", "2", "-ar", "44100",
           "-codec:a", "libmp3lame", "-b:a", "128k", "-f", "mp3", "pipe:1"]
    try:
        return subprocess.run(cmd, capture_output=True, check=True, timeout=30).stdout
    except (OSError, subprocess.SubprocessError):
        return None


def save_recording(data: bytes) -> str:
    REC_DIR.mkdir(parents=True, exist_ok=True)
    out = REC_DIR / f"shadow_{datetime.now().strftime('%Y%m%d_%H%M%S')}.wav"
    out.write_bytes(data)
    return str(out)


def list_recordings() -> list[str]:
    if not REC_DIR.exists():
        return []
    return [str(p) for p in sorted(REC_DIR.glob("*.wav"), reverse=True)]
