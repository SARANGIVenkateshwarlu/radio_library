"""Pluggable Cantonese TTS engines.

Ships working: ``EdgeTTS`` — free Microsoft Edge ``zh-HK`` neural voices via the
open-source ``edge-tts`` client (no GPU / no key). Other engines are registered
as adapters to add when adopted (CosyVoice2-Yue, F5-TTS, Llasa, Azure).

    python src/tts_engine.py "今日天氣好好" --voice zh-HK-HiuGaaiNeural --out out.mp3
"""
from __future__ import annotations

import argparse
import asyncio

CANTONESE_VOICES = {
    "zh-HK-HiuGaaiNeural": {"gender": "Female", "name": "HiuGaai 曉佳"},
    "zh-HK-HiuMaanNeural": {"gender": "Female", "name": "HiuMaan 曉曼"},
    "zh-HK-WanLungNeural": {"gender": "Male", "name": "WanLung 雲龍"},
}


class EdgeTTS:
    """Free Edge zh-HK neural Cantonese voices."""

    name = "edge"

    def synthesize(self, text: str, voice: str = "zh-HK-HiuGaaiNeural",
                   rate: str = "+0%", pitch: str = "+0Hz") -> bytes:
        import edge_tts

        async def _run() -> bytes:
            comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            out = bytearray()
            async for chunk in comm.stream():
                if chunk["type"] == "audio":
                    out += chunk["data"]
            return bytes(out)

        return asyncio.run(_run())


# Adapters to implement when adopting (see REPORT.md §3):
class CosyVoice2TTS:   # noqa: F811  (stub)
    name = "cosyvoice2"
    def synthesize(self, text: str, **kw) -> bytes:  # pragma: no cover
        raise NotImplementedError("Install FunAudioLLM/CosyVoice + a Cantonese "
                                  "fine-tune (CosyVoice2-Yue-style) — see REPORT §3.")


class F5TTS:           # noqa: F811  (stub)
    name = "f5"
    def synthesize(self, text: str, **kw) -> bytes:  # pragma: no cover
        raise NotImplementedError("Install F5-TTS and a Cantonese checkpoint — see REPORT §3.")


ENGINES = {e.name: e for e in (EdgeTTS(), CosyVoice2TTS(), F5TTS())}


def get_engine(name: str = "edge"):
    return ENGINES[name]()


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("text")
    ap.add_argument("--voice", default="zh-HK-HiuGaaiNeural")
    ap.add_argument("--out", default="out.mp3")
    a = ap.parse_args()
    audio = EdgeTTS().synthesize(a.text, a.voice)
    open(a.out, "wb").write(audio)
    print(f"wrote {a.out} ({len(audio)} bytes)")
