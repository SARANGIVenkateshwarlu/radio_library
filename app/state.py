"""LangGraph state schema for the radio processing pipeline."""
from __future__ import annotations

from typing import TypedDict, Optional


class Segment(TypedDict, total=False):
    start: float
    end: float
    cantonese: str              # raw ASR output (== verbatim_transcript)
    corrected: str              # LLM-corrected Cantonese (== normalized_cantonese)
    verbatim_transcript: str    # what was heard, unchanged
    normalized_cantonese: str   # readable Hong Kong Cantonese characters
    jyutping: str
    english: str
    vocabulary: list[dict]      # [{"word": ..., "jyutping": ..., "meaning": ...}]
    uncertain: bool
    # confidence / evidence / validation (guideline 10)
    confidence: dict            # {"audio","transcription","jyutping","translation"}
    no_speech_prob: float
    audio_quality: str          # good | noisy | music | overlapping_speech | unknown
    uncertain_tokens: list[str]
    alternative_readings: list[dict]
    needs_human_review: bool
    review_reason: str


class RadioState(TypedDict, total=False):
    # input
    audio_path: str
    mock_asr: bool
    clean_audio: bool

    # cleanup
    asr_audio_path: str
    cleanup_method: str

    # quality review / validation
    quality_review: dict
    audio_quality: str

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
