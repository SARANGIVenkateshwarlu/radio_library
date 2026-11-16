"""Pronunciation / voice test.

Record yourself reading a target Cantonese sentence; the local Whisper ASR
transcribes your speech and we compare it with the target:

* **Character accuracy** — how much of the sentence was recognised.
* **Tone accuracy** — LSHK Jyutping tones compared **only on matched
  characters** (character-aligned), so a single insertion/deletion no longer
  collapses the score (the old positional compare did).
* **Pitch (F0) accuracy** — the tone **modulation**: the learner's pitch
  contour is extracted (autocorrelation) and compared syllable by syllable
  with the reference voice (`reference_audio`) in semitones relative to each
  speaker's median F0, or — if no reference was played — with the ideal LSHK
  tone templates on the learner's own 1–5 pitch range (level tones judged on
  register, rising/falling tones on direction). Raw Hz is reported for
  information only: a correct reading does **not** need to match the
  reference's absolute frequency, only its relative rises/falls/levels.
* **Rhythm** — speech rate (syllables/second) within a natural Cantonese band.
* **Fluency** — proportion of silence/pauses between ASR segments.
* **Overall** — weighted sub-scores (0.35 char + 0.25 tone + 0.2 pitch
  + 0.1 rhythm + 0.1 fluency; weights renormalise when pitch is unavailable).

Tones come from the dictionary (authoritative HK reading) per the project's
hardbound rule — never from the LLM.
"""
from __future__ import annotations

import difflib
import re

from .jyutping_tool import to_jyutping

_KEEP = re.compile(r"[\u3400-\u9fff0-9A-Za-z]")
_CJK = re.compile(r"[\u3400-\u9fff]")
_TONE = re.compile(r"([1-6])$")

# Tone minimal pairs for focused practice. Readings are **derived from the
# dictionary at runtime** (`minimal_pairs()`), never hard-coded, per the
# hardbound HK-Cantonese Jyutping rule.
MINIMAL_PAIRS = [
    {
        "words": [("識", "to know"), ("食", "to eat")],
        "sentence": "我識食",
        "english": "I know good food (I know how to eat)",
    },
    {
        "words": [("買", "to buy"), ("賣", "to sell")],
        "sentence": "我買你賣",
        "english": "I buy, you sell",
    },
    {
        "words": [("史", "history"), ("時", "time")],
        "sentence": "我時時讀歷史",
        "english": "I study history all the time",
    },
]

_asr = None


def _norm(text: str) -> str:
    return "".join(_KEEP.findall(text or ""))


def _cjk_chars(text: str) -> list[str]:
    return _CJK.findall(text or "")


def _char_tone(ch: str) -> int | None:
    """Authoritative tone (1-6) for one Cantonese character, or None."""
    m = _TONE.search(to_jyutping(ch).strip())
    return int(m.group(1)) if m else None


def _get_asr():
    global _asr
    if _asr is None:
        from . import asr

        _asr = asr.get_asr(mock=False)
    return _asr


def minimal_pairs() -> list[dict]:
    """Minimal-pair practice sets with **dictionary-derived** LSHK Jyutping.

    Each entry: ``label``, ``sentence``, ``english``, ``jyutping`` (sentence
    reading) and ``words`` (char / jyutping / tone / meaning).
    """
    out = []
    for p in MINIMAL_PAIRS:
        words = [{"char": ch, "jyutping": to_jyutping(ch),
                  "tone": _char_tone(ch), "meaning": meaning}
                 for ch, meaning in p["words"]]
        out.append({
            **p,
            "words": words,
            "jyutping": to_jyutping(p["sentence"]),
            "label": "  vs  ".join(
                f"{w['char']} {w['jyutping']} ({w['meaning']})" for w in words),
        })
    return out


def transcribe(audio_path: str) -> str:
    segs = _get_asr().transcribe(audio_path)
    return "".join(s.get("cantonese", "") for s in segs).strip()


def transcribe_words(audio_path: str) -> list[dict]:
    """Word/character-level timestamps (for syllable alignment in the graph)."""
    from . import asr

    provider = _get_asr()
    audio = asr._decode_pcm(audio_path)
    segs, _ = provider.model.transcribe(
        audio, language=asr.config.WHISPER_LANGUAGE or None, task="transcribe",
        beam_size=asr.config.WHISPER_BEAM, vad_filter=True,
        condition_on_previous_text=False, word_timestamps=True,
        initial_prompt=asr.config.WHISPER_INITIAL_PROMPT or None,
    )
    words = []
    for s in segs:
        for w in getattr(s, "words", None) or []:
            words.append({"start": float(w.start), "end": float(w.end),
                          "word": w.word})
    return words


def _aligned_tone_accuracy(target_chars: list[str],
                           spoken_chars: list[str]) -> tuple[float, list[int | None], list[int | None]]:
    """Tone match over the characters that actually align (ignores insertions)."""
    t_tones = [_char_tone(c) for c in target_chars]
    s_tones = [_char_tone(c) for c in spoken_chars]
    hits, total = 0, len(target_chars)
    sm = difflib.SequenceMatcher(None, target_chars, spoken_chars)
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            tt = t_tones[blk.a + k]
            st = s_tones[blk.b + k]
            if tt is not None and st is not None and tt == st:
                hits += 1
    return (hits / total if total else 0.0), t_tones, s_tones


def evaluate(target_text: str, audio_path: str,
             reference_audio: str | None = None) -> dict:
    """Score a recorded reading against ``target_text``.

    ``reference_audio`` (optional) is a recording of the same sentence — usually
    the Edge ``zh-HK`` reference voice — used for a like-for-like pitch
    comparison. Without it the LSHK tone templates are used instead.
    """
    segs = _get_asr().transcribe(audio_path)
    spoken = "".join(s.get("cantonese", "") for s in segs).strip()

    target_norm, spoken_norm = _norm(target_text), _norm(spoken)
    char_acc = difflib.SequenceMatcher(None, target_norm, spoken_norm).ratio()

    target_chars, spoken_chars = _cjk_chars(target_text), _cjk_chars(spoken)
    tone_acc, t_tones, s_tones = _aligned_tone_accuracy(target_chars, spoken_chars)

    # duration (probe the recording; fall back to last ASR timestamp)
    duration = 0.0
    try:
        from .audio_util import probe_duration

        duration = probe_duration(audio_path) or 0.0
    except Exception:
        duration = 0.0
    if not duration and segs:
        duration = max((s.get("end", 0.0) for s in segs), default=0.0)

    # fluency: proportion of silence/pauses between recognised segments
    pause = sum(max(0.0, b.get("start", 0.0) - a.get("end", 0.0))
                for a, b in zip(segs, segs[1:]))
    pause_ratio = (pause / duration) if duration > 0 else 0.0
    fluency = max(0.0, min(1.0, 1.0 - pause_ratio / 0.5))

    # rhythm: syllables per second **while speaking** (the non-silent span, so
    # waiting before/after the recording is not counted — that is fluency's job)
    speech_dur = duration
    try:
        from . import voice_graph

        a0, b0 = voice_graph.speech_span(audio_path)
        if b0 - a0 > 0.2:
            speech_dur = b0 - a0
    except Exception:
        pass
    rate = (len(spoken_chars) / speech_dur) if speech_dur > 0 else 0.0
    if rate <= 0:
        rhythm = 0.0
    elif 2.0 <= rate <= 7.5:
        rhythm = 1.0
    else:
        rhythm = max(0.0, 1.0 - abs(rate - 4.5) / 4.5)

    # pitch (F0): does the tone modulation rise/fall/level at the right
    # relative frequency? Speaker-normalised, so a different voice type cannot
    # be penalised for a different absolute register.
    pitch = None
    try:
        from . import voice_graph

        pitch = voice_graph.pitch_accuracy(
            target_text, audio_path, reference_audio=reference_audio)
    except Exception:
        pitch = None
    pitch_score = pitch.get("score") if pitch else None

    parts = [("char", char_acc, 0.35), ("tone", tone_acc, 0.25),
             ("rhythm", rhythm, 0.10), ("fluency", fluency, 0.10)]
    if pitch_score is not None:
        parts.append(("pitch", pitch_score / 100.0, 0.20))
    total_w = sum(w for _, _, w in parts)
    score = round(100 * sum(v * w for _, v, w in parts) / total_w)

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
        "pitch_accuracy": pitch_score,
        "pitch_mode": pitch.get("mode") if pitch else None,
        "pitch_unit": pitch.get("unit") if pitch else None,
        "pitch_syllables": pitch.get("syllables") if pitch else [],
        "learner_f0_hz": pitch.get("learner_hz") if pitch else None,
        "reference_f0_hz": pitch.get("reference_hz") if pitch else None,
        "register_shift_st": pitch.get("register_shift_st") if pitch else None,
        "rhythm": round(rhythm * 100),
        "fluency": round(fluency * 100),
        "score": score,
        "target_tones": " ".join(str(t) for t in t_tones if t is not None),
        "spoken_tones": " ".join(str(t) for t in s_tones if t is not None),
        "duration_s": round(duration, 2),
        "differences": differences,
    }
