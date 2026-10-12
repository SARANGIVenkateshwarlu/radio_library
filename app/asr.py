"""ASR providers for Cantonese speech-to-text.

Backends (choose with ``WHISPER_BACKEND``):
  * ``faster-whisper`` (default) — CTranslate2, fastest on CPU. Point
    ``WHISPER_MODEL`` at a CTranslate2 Whisper model (a name like ``base`` or a
    converted Cantonese large-v3-turbo directory).
  * ``transformers`` — loads a Hugging Face Whisper model directly, e.g.
    ``wingskh/whisper-large-v3-turbo-cantonese``.

``MockASR`` returns a fixed demo transcript for offline testing.

Cantonese quality is driven by ``WHISPER_LANGUAGE=yue``,
``WHISPER_INITIAL_PROMPT`` (Traditional-Chinese bias) and beam/VAD defaults.
"""
from __future__ import annotations

import math
import subprocess

import numpy as np

from . import config
from .state import Segment

DEMO_TRANSCRIPT: list[Segment] = [
    {"start": 0.0, "end": 4.5, "cantonese": "各位聽眾早晨，歡迎收聽今日嘅新聞報道。"},
    {"start": 4.5, "end": 9.0, "cantonese": "今日天氣比較潮濕，下午可能會有驟雨。"},
    {"start": 9.0, "end": 14.0, "cantonese": "天文台提醒市民出門口之前記得帶遮。"},
    {"start": 14.0, "end": 19.5, "cantonese": "交通方面，港鐵荃灣綫而家服務正常。"},
    {"start": 19.5, "end": 25.0, "cantonese": "不過紅磡海底隧道往香港方向交通擠塞，車龍排到去理工大學。"},
]


def _decode_pcm(audio_path: str) -> np.ndarray:
    """Decode any audio to 16 kHz mono float32 via ffmpeg."""
    raw = subprocess.run(
        [config.FFMPEG_BINARY, "-v", "quiet", "-i", audio_path,
         "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
        capture_output=True, check=True,
    ).stdout
    return np.frombuffer(raw, dtype=np.float32)


class MockASR:
    """Offline demo ASR — returns a fixed Cantonese transcript."""

    name = "mock"

    def transcribe(self, audio_path: str) -> list[Segment]:
        return [{**s, "confidence": 1.0, "no_speech_prob": 0.0}
                for s in DEMO_TRANSCRIPT]


class WhisperASR:
    """Real ASR via faster-whisper (CTranslate2)."""

    name = "faster-whisper"

    def __init__(self, model_size: str | None = None):
        from faster_whisper import WhisperModel

        self.model = WhisperModel(
            model_size or config.WHISPER_MODEL,
            device=config.WHISPER_DEVICE,
            compute_type=config.WHISPER_COMPUTE,
        )
        self.batched = None
        if config.WHISPER_BATCH_SIZE > 1:
            try:
                from faster_whisper import BatchedInferencePipeline

                self.batched = BatchedInferencePipeline(model=self.model)
            except Exception:
                self.batched = None

    def _run(self, audio, language):
        kwargs = dict(
            language=language,
            task="transcribe",
            beam_size=config.WHISPER_BEAM,
            condition_on_previous_text=False,
            temperature=[0.0, 0.2, 0.4, 0.6, 0.8, 1.0],
            initial_prompt=config.WHISPER_INITIAL_PROMPT or None,
        )
        if self.batched is not None:
            # BatchedInferencePipeline: big speed-up with the same accuracy
            return self.batched.transcribe(
                audio, batch_size=config.WHISPER_BATCH_SIZE,
                vad_filter=True, **kwargs)
        return self.model.transcribe(audio, vad_filter=True, **kwargs)

    def transcribe(self, audio_path: str) -> list[Segment]:
        audio = _decode_pcm(audio_path)
        try:
            segs, _info = self._run(audio, config.WHISPER_LANGUAGE or None)
        except ValueError:
            # e.g. "yue" unsupported on small models -> fall back to auto-detect
            segs, _info = self._run(audio, None)
        out: list[Segment] = []
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


class TransformersWhisperASR:
    """ASR via Hugging Face transformers (e.g. wingskh Cantonese turbo)."""

    name = "transformers"

    def __init__(self, model_id: str | None = None):
        import torch
        from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor
        from transformers import pipeline

        model_id = model_id or config.WHISPER_MODEL
        self.torch = torch
        model = AutoModelForSpeechSeq2Seq.from_pretrained(model_id)
        processor = AutoProcessor.from_pretrained(model_id)
        self.pipe = pipeline(
            "automatic-speech-recognition",
            model=model,
            tokenizer=processor.tokenizer,
            feature_extractor=processor.feature_extractor,
            device="cpu",
        )

    def transcribe(self, audio_path: str) -> list[Segment]:
        audio = _decode_pcm(audio_path)
        gen_kwargs = {"task": "transcribe"}
        if config.WHISPER_LANGUAGE:
            gen_kwargs["language"] = config.WHISPER_LANGUAGE
        prompt = config.WHISPER_INITIAL_PROMPT
        if prompt:
            gen_kwargs["prompt"] = prompt
        result = self.pipe(
            audio, chunk_length_s=30, stride_length_s=5,
            return_timestamps=True, generate_kwargs=gen_kwargs,
        )
        out: list[Segment] = []
        for chunk in result.get("chunks", []):
            text = (chunk.get("text") or "").strip()
            if not text:
                continue
            ts = chunk.get("timestamp") or (0.0, 0.0)
            out.append({
                "start": float(ts[0] or 0.0),
                "end": float(ts[1] or 0.0),
                "cantonese": text,
                "confidence": None,
                "no_speech_prob": 0.0,
            })
        return out


def get_asr(mock: bool = False):
    """Return an ASR provider based on config (mock / faster-whisper / transformers)."""
    if mock:
        return MockASR()
    if config.WHISPER_BACKEND == "transformers":
        return TransformersWhisperASR()
    return WhisperASR()
