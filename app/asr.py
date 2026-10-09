"""ASR providers for Cantonese speech-to-text.

MockASR returns a fixed demo transcript so the whole pipeline can be tested
offline. Plug a real provider (Cantonese.ai API, whisper-yue, etc.) by
implementing the same `transcribe(audio_path) -> list[Segment]` interface.
"""
from __future__ import annotations

from . import config
from .state import Segment

DEMO_TRANSCRIPT: list[Segment] = [
    {"start": 0.0, "end": 4.5, "cantonese": "各位聽眾早晨，歡迎收聽今日嘅新聞報道。"},
    {"start": 4.5, "end": 9.0, "cantonese": "今日天氣比較潮濕，下午可能會有驟雨。"},
    {"start": 9.0, "end": 14.0, "cantonese": "天文台提醒市民出門口之前記得帶遮。"},
    {"start": 14.0, "end": 19.5, "cantonese": "交通方面，港鐵荃灣綫而家服務正常。"},
    {"start": 19.5, "end": 25.0, "cantonese": "不過紅磡海底隧道往香港方向交通擠塞，車龍排到去理工大學。"},
]


class MockASR:
    """Offline demo ASR — returns a fixed Cantonese transcript."""

    name = "mock"

    def transcribe(self, audio_path: str) -> list[Segment]:
        return [{**s, "confidence": 1.0, "no_speech_prob": 0.0}
                for s in DEMO_TRANSCRIPT]


class WhisperASR:
    """Real ASR via faster-whisper (local model, works offline after download).

    Model size from WHISPER_MODEL (default: base). Language auto-detected;
    Cantonese speech is usually transcribed as written Chinese (zh).
    """

    name = "faster-whisper"

    def __init__(self, model_size: str | None = None):
        import os
        from faster_whisper import WhisperModel

        self.model = WhisperModel(
            model_size or os.getenv("WHISPER_MODEL", "base"),
            device="cpu", compute_type="int8",
        )

    def transcribe(self, audio_path: str) -> list[Segment]:
        import math
        import subprocess

        import numpy as np

        # decode with ffmpeg (avoids PyAV version quirks): 16 kHz mono float32
        raw = subprocess.run(
            [config.FFMPEG_BINARY, "-v", "quiet", "-i", audio_path,
             "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
            capture_output=True, check=True,
        ).stdout
        audio = np.frombuffer(raw, dtype=np.float32)
        segs, info = self.model.transcribe(audio, vad_filter=True)
        out = []
        for s in segs:
            text = s.text.strip()
            if not text:
                continue
            avg = getattr(s, "avg_logprob", None)
            out.append({
                "start": s.start,
                "end": s.end,
                "cantonese": text,
                "confidence": round(math.exp(avg), 3) if avg is not None else None,
                "no_speech_prob": round(getattr(s, "no_speech_prob", 0.0) or 0.0, 3),
            })
        return out


def get_asr(mock: bool = False):
    """Return an ASR provider. Real providers can be registered here."""
    if mock:
        return MockASR()
    return WhisperASR()
