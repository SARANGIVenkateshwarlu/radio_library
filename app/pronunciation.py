"""Pronunciation / voice test.

Record yourself reading a target Cantonese sentence; the local Whisper ASR
transcribes your speech and we compare it with the target:

* **Character accuracy** — how much of the sentence was recognised (SequenceMatcher).
* **Tone accuracy** — LSHK Jyutping tone numbers (1-6) aligned positionally.
* **Overall score** — 0.6·character + 0.4·tone.

The Whisper model is loaded once and reused.
"""
from __future__ import annotations

import difflib
import re

from . import config
from .jyutping_tool import to_jyutping

_KEEP = re.compile(r"[\u3400-\u9fff0-9A-Za-z]")
_TONE = re.compile(r"^[a-z]+([1-6])$")

_asr = None


def _norm(text: str) -> str:
    return "".join(_KEEP.findall(text or ""))


def _tones(jyutping: str) -> list[str]:
    tones = []
    for token in (jyutping or "").split():
        m = _TONE.match(token)
        if m:
            tones.append(m.group(1))
    return tones


def _get_asr():
    global _asr
    if _asr is None:
        from . import asr

        _asr = asr.get_asr(mock=False)
    return _asr


def transcribe(audio_path: str) -> str:
    segs = _get_asr().transcribe(audio_path)
    return "".join(s.get("cantonese", "") for s in segs).strip()


def transcribe_words(audio_path: str) -> list[dict]:
    """Word/character-level timestamps (for syllable alignment in the graph)."""
    from . import asr

    provider = _get_asr()
    audio = asr._decode_pcm(audio_path)
    segs, _ = provider.model.transcribe(
        audio, language=config.WHISPER_LANGUAGE or None, task="transcribe",
        beam_size=config.WHISPER_BEAM, vad_filter=True,
        condition_on_previous_text=False, word_timestamps=True,
        initial_prompt=config.WHISPER_INITIAL_PROMPT or None,
    )
    words = []
    for s in segs:
        for w in getattr(s, "words", None) or []:
            words.append({"start": float(w.start), "end": float(w.end),
                          "word": w.word})
    return words


def evaluate(target_text: str, audio_path: str) -> dict:
    """Score a recorded reading against ``target_text``."""
    spoken = transcribe(audio_path)

    target_norm, spoken_norm = _norm(target_text), _norm(spoken)
    char_acc = difflib.SequenceMatcher(None, target_norm, spoken_norm).ratio()

    target_tones = _tones(to_jyutping(target_text))
    spoken_tones = _tones(to_jyutping(spoken))
    denom = max(len(target_tones), len(spoken_tones), 1)
    tone_hits = sum(1 for a, b in zip(target_tones, spoken_tones) if a == b)
    tone_acc = tone_hits / denom

    differences = []
    sm = difflib.SequenceMatcher(None, target_norm, spoken_norm)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            differences.append({"change": tag,
                                "target": target_norm[i1:i2] or "—",
                                "heard": spoken_norm[j1:j2] or "—"})

    return {
        "spoken": spoken or "(nothing recognised)",
        "char_accuracy": round(char_acc * 100),
        "tone_accuracy": round(tone_acc * 100),
        "score": round(100 * (0.6 * char_acc + 0.4 * tone_acc)),
        "target_tones": " ".join(target_tones),
        "spoken_tones": " ".join(spoken_tones),
        "differences": differences,
    }
