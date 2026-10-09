"""Deterministic LSHK Jyutping validation.

An LSHK Jyutping syllable is an optional onset + a final + a tone number 1-6
written at the end (e.g. ``nei5 hou2``). This module validates syllables and the
character/syllable alignment **without** relying on the LLM, per the project
guidelines ("validate Jyutping programmatically against a legal syllable
table").
"""
from __future__ import annotations

import re

# LSHK Jyutping onsets (initials) and finals (rhymes).
ONSETS = (
    "gw", "kw", "ng", "b", "p", "m", "f", "d", "t", "n", "l",
    "g", "k", "h", "w", "z", "c", "s", "j",
)
FINALS = (
    "aai", "aau", "aam", "aan", "aang", "aap", "aat", "aak", "aa",
    "ai", "au", "am", "an", "ang", "ap", "at", "ak",
    "ei", "eu", "em", "eng", "ep", "ek", "e",
    "iu", "im", "in", "ing", "ip", "it", "ik", "i",
    "oi", "ou", "on", "ong", "ot", "ok", "o",
    "ui", "un", "ung", "ut", "uk", "u",
    "oeng", "oek", "oe",
    "eoi", "eon", "eot", "eo",
    "yun", "yut", "yu",
    "m", "ng",
)

_TONE_RE = re.compile(r"^([a-z]+)([1-6])$")
_ROMAN_RE = re.compile(r"^[A-Za-z]")
_CJK = re.compile(r"[\u3400-\u9fff]")
_PLACEHOLDER = "〔?〕"


def is_legal_syllable(token: str) -> bool:
    """True if ``token`` is a legal LSHK Jyutping syllable with a tone 1-6."""
    m = _TONE_RE.match(token)
    if not m:
        return False
    base = m.group(1)
    if base in ("m", "ng"):
        return True
    if base in FINALS:
        return True
    for onset in ONSETS:
        if base.startswith(onset) and base[len(onset):] in FINALS:
            return True
    return False


def _romanization_tokens(jyutping: str) -> list[str]:
    return [t for t in (jyutping or "").split() if _ROMAN_RE.match(t)]


def validate_jyutping(jyutping: str) -> dict:
    """Return {'syllables', 'invalid': [...], 'missing_tone': [...]}."""
    invalid, missing_tone = [], []
    syllables = 0
    for tok in _romanization_tokens(jyutping):
        syllables += 1
        if not _TONE_RE.match(tok):
            missing_tone.append(tok)
        elif not is_legal_syllable(tok):
            invalid.append(tok)
    return {"syllables": syllables, "invalid": invalid, "missing_tone": missing_tone}


def count_chinese(text: str) -> int:
    return len(_CJK.findall(text or ""))


def validate_segment(segment: dict) -> list[str]:
    """Return a list of human-readable alignment/validity problems."""
    problems: list[str] = []
    jyutping = segment.get("jyutping", "") or ""
    text = segment.get("corrected") or segment.get("cantonese", "") or ""

    if _PLACEHOLDER in jyutping:
        problems.append("uncertain Jyutping (〔?〕)")

    result = validate_jyutping(jyutping)
    if result["missing_tone"]:
        problems.append("Jyutping missing tone number: " + ", ".join(result["missing_tone"][:5]))
    if result["invalid"]:
        problems.append("invalid Jyutping syllable: " + ", ".join(result["invalid"][:5]))

    chars = count_chinese(text)
    if chars and result["syllables"] and chars != result["syllables"]:
        problems.append(
            f"character/syllable mismatch ({chars} chars vs {result['syllables']} syllables)"
        )
    return problems
