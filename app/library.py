"""SQLite metadata store for the radio library."""
from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS recordings (
    recording_id     TEXT PRIMARY KEY,
    station          TEXT,
    program          TEXT,
    recorded_at      TEXT,
    duration_seconds INTEGER,
    audio_file       TEXT,
    pdf_file         TEXT,
    transcript_json  TEXT,
    srt_file         TEXT,
    review_status    TEXT DEFAULT 'unreviewed',
    created_at       TEXT DEFAULT (datetime('now'))
);
"""


def init_db(db_path: Path | None = None) -> None:
    with sqlite3.connect(db_path or config.DB_PATH) as con:
        con.executescript(_SCHEMA)


def save_recording(record: dict, db_path: Path | None = None) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path or config.DB_PATH) as con:
        con.execute(
            """INSERT OR REPLACE INTO recordings
               (recording_id, station, program, recorded_at, duration_seconds,
                audio_file, pdf_file, transcript_json, srt_file, review_status)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (
                record["recording_id"], record.get("station"), record.get("program"),
                record.get("recorded_at"), record.get("duration_seconds"),
                record.get("audio_file"), record.get("pdf_file"),
                json.dumps(record.get("segments", []), ensure_ascii=False),
                record.get("srt_file"), record.get("review_status", "unreviewed"),
            ),
        )


def list_recordings(db_path: Path | None = None) -> list[dict]:
    init_db(db_path)
    with sqlite3.connect(db_path or config.DB_PATH) as con:
        con.row_factory = sqlite3.Row
        rows = con.execute(
            "SELECT * FROM recordings ORDER BY recorded_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def update_review_status(recording_id: str, status: str, db_path: Path | None = None) -> None:
    init_db(db_path)
    with sqlite3.connect(db_path or config.DB_PATH) as con:
        con.execute(
            "UPDATE recordings SET review_status = ? WHERE recording_id = ?",
            (status, recording_id),
        )


def get_recording(recording_id: str, db_path: Path | None = None) -> dict | None:
    init_db(db_path)
    with sqlite3.connect(db_path or config.DB_PATH) as con:
        con.row_factory = sqlite3.Row
        row = con.execute(
            "SELECT * FROM recordings WHERE recording_id = ?", (recording_id,)
        ).fetchone()
    return dict(row) if row else None
