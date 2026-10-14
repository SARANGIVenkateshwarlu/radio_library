"""CantoneVoice Production — FastAPI service (starter).

Working baseline: free Microsoft Edge ``zh-HK`` neural Cantonese voices via
``edge-tts`` (no GPU, no key). Swap ``_ENGINE`` for CosyVoice2-Yue / F5 / Azure
when adopted (see ../REPORT.md §3).

Run:  uvicorn src.service:app --reload
"""
from __future__ import annotations

import asyncio
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

app = FastAPI(title="CantoneVoice Production", version="0.1")

VOICES = {
    "zh-HK-HiuGaaiNeural": {"gender": "Female", "name": "HiuGaai 曉佳"},
    "zh-HK-HiuMaanNeural": {"gender": "Female", "name": "HiuMaan 曉曼"},
    "zh-HK-WanLungNeural": {"gender": "Male", "name": "WanLung 雲龍"},
}
_JOBS: dict[str, dict] = {}


class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-HK-HiuGaaiNeural"
    lang: str = "yue"
    rate: str = "+0%"
    pitch: str = "+0Hz"
    emotion: str = "neutral"          # reserved for expressive engines
    format: str = "mp3"


class CloneRequest(BaseModel):
    name: str
    audio_url: str | None = None
    audio_base64: str | None = None


def _synthesize(text: str, voice: str, rate: str, pitch: str) -> bytes:
    import edge_tts

    async def _run() -> bytes:
        comm = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        out = bytearray()
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                out += chunk["data"]
        return bytes(out)

    return asyncio.run(_run())


@app.get("/voices")
def voices() -> list[dict]:
    return [{"voice_id": vid, **meta} for vid, meta in VOICES.items()]


@app.post("/tts")
def tts(req: TTSRequest):
    try:
        audio = _synthesize(req.text, req.voice, req.rate, req.pitch)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    job_id = "j_" + uuid.uuid4().hex[:8]
    _JOBS[job_id] = {"status": "done", "bytes": len(audio), "voice": req.voice}
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"X-Job-Id": job_id})


@app.post("/clone-voice")
def clone_voice(req: CloneRequest):
    raise HTTPException(status_code=501, detail=(
        "Voice cloning requires a cloning-capable engine (CosyVoice2 / F5 / "
        "XTTS) — see REPORT.md §3."))


@app.get("/jobs/{job_id}")
def job(job_id: str):
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="unknown job")
    return {"job_id": job_id, **_JOBS[job_id]}
