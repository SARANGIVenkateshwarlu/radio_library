"""FastAPI service for AI_CantoneVoice (starter).

Endpoints:
    POST /tts           text -> audio (Edge zh-HK baseline)
    GET  /voices        available voices / personas
    POST /clone-voice   register a voice (adapter; not implemented for Edge)
    GET  /jobs/{id}     job status (sync baseline returns done immediately)

Run:  uvicorn src.service:app --reload
"""
from __future__ import annotations

import uuid

from fastapi import FastAPI, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel

try:  # script or module import
    from .tts_engine import CANTONESE_VOICES, EdgeTTS
except ImportError:  # pragma: no cover
    from tts_engine import CANTONESE_VOICES, EdgeTTS

app = FastAPI(title="AI_CantoneVoice", version="0.1")
_ENGINE = EdgeTTS()
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


@app.get("/voices")
def voices() -> list[dict]:
    return [{"voice_id": vid, **meta} for vid, meta in CANTONESE_VOICES.items()]


@app.post("/tts")
def tts(req: TTSRequest):
    try:
        audio = _ENGINE.synthesize(req.text, req.voice, rate=req.rate, pitch=req.pitch)
    except Exception as exc:  # baseline engine errors
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    job_id = "j_" + uuid.uuid4().hex[:8]
    _JOBS[job_id] = {"status": "done", "bytes": len(audio)}
    return Response(content=audio, media_type="audio/mpeg",
                    headers={"X-Job-Id": job_id})


@app.post("/clone-voice")
def clone_voice(req: CloneRequest):
    raise HTTPException(status_code=501, detail=(
        "Voice cloning requires a cloning-capable engine (CosyVoice2 / F5 / "
        "XTTS). Not available on the Edge baseline — see REPORT.md §3."))


@app.get("/jobs/{job_id}")
def job(job_id: str):
    if job_id not in _JOBS:
        raise HTTPException(status_code=404, detail="unknown job")
    return {"job_id": job_id, **_JOBS[job_id]}
