"""AI_CantoneVoice — Cantonese text-to-speech for the app.

Working baseline: free Microsoft Edge ``zh-HK`` neural voices via ``edge-tts``
(no GPU, no API key). The full project blueprint lives in
``AI_CantoneVoice/REPORT.md``; heavier engines (CosyVoice2-Yue, F5-TTS, Llasa)
are adapters to add later (see that report).
"""
from __future__ import annotations

import asyncio
from pathlib import Path

from . import config
from .jyutping_tool import to_jyutping

REPORT_PATH = config.BASE_DIR / "AI_CantoneVoice" / "REPORT.md"

VOICES = {
    "zh-HK-HiuGaaiNeural": "HiuGaai 曉佳 (Female)",
    "zh-HK-HiuMaanNeural": "HiuMaan 曉曼 (Female)",
    "zh-HK-WanLungNeural": "WanLung 雲龍 (Male)",
}
RATES = {"0.8x": "-20%", "0.9x": "-10%", "1.0x": "+0%", "1.1x": "+10%", "1.2x": "+20%"}
PITCHES = {"-20Hz": "-20Hz", "0Hz": "+0Hz", "+20Hz": "+20Hz", "+40Hz": "+40Hz"}


def available() -> bool:
    import importlib.util

    return importlib.util.find_spec("edge_tts") is not None


def synthesize(text: str, voice: str = "zh-HK-HiuGaaiNeural",
               rate: str = "+0%", pitch: str = "+0Hz") -> bytes:
    """Return MP3 bytes of the Cantonese speech (Edge zh-HK neural voice)."""
    import edge_tts

    async def _run() -> bytes:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        out = bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                out += chunk["data"]
        return bytes(out)

    return asyncio.run(_run())


def reading(text: str) -> str:
    """LSHK Jyutping reading (dictionary-based) for display."""
    return to_jyutping(text)


def report_text() -> str:
    try:
        return REPORT_PATH.read_text(encoding="utf-8")
    except OSError:
        return "_Report not found._"
