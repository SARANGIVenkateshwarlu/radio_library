"""Pronunciation / voice test.

Record yourself reading a target Cantonese sentence; the local Whisper ASR
transcribes your speech and we compare it with the target:

* **Character accuracy** — how much of the sentence was recognised.
* **Tone accuracy** — LSHK Jyutping tones compared **only on matched
  characters** (character-aligned), so a single insertion/deletion no longer
  collapses the score (the old positional compare did).
* **Rhythm** — speech rate (syllables/second) within a natural Cantonese band.
* **Fluency** — proportion of silence/pauses between ASR segments.
* **Overall** — weighted sub-scores (0.4 char + 0.4 tone + 0.1 rhythm + 0.1 fluency).

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


def evaluate(target_text: str, audio_path: str) -> dict:
    """Score a recorded reading against ``target_text``."""
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

    # rhythm: syllables per second within a natural Cantonese band (2.5-7.5)
    rate = (len(spoken_chars) / duration) if duration > 0 else 0.0
    if rate <= 0:
        rhythm = 0.0
    elif 2.5 <= rate <= 7.5:
        rhythm = 1.0
    else:
        rhythm = max(0.0, 1.0 - abs(rate - 5.0) / 5.0)

    score = round(100 * (0.4 * char_acc + 0.4 * tone_acc
                         + 0.1 * rhythm + 0.1 * fluency))

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
        "rhythm": round(rhythm * 100),
        "fluency": round(fluency * 100),
        "score": score,
        "target_tones": " ".join(str(t) for t in t_tones if t is not None),
        "spoken_tones": " ".join(str(t) for t in s_tones if t is not None),
        "duration_s": round(duration, 2),
        "differences": differences,
    }
