"""LangGraph state schema for the radio processing pipeline."""
from __future__ import annotations

from typing import TypedDict, Optional


class Segment(TypedDict, total=False):
    start: float
    end: float
    cantonese: str          # raw ASR output
    corrected: str          # LLM-corrected Cantonese
    jyutping: str
    english: str
    vocabulary: list[dict]    # [{"word": ..., "jyutping": ..., "meaning": ...}]
    uncertain: bool


class RadioState(TypedDict, total=False):
    # input
    audio_path: str
    mock_asr: bool

    # load_audio
    recording_id: str
    station: str
    program: str
    recorded_at: str
    duration_seconds: int

    # transcribe / correct / jyutping / translate
    segments: list[Segment]

    # outputs
    transcript_json_path: str
    srt_path: str
    pdf_path: str

    # bookkeeping
    review_status: str
    errors: list[str]
