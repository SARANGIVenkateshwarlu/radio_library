"""Jyutping conversion.

Primary path: pycantonese (HKCanCor-based lexicon + segmentation).
Fallback: a small built-in dictionary for the demo vocabulary, with unknown
characters marked as 〔?〕 instead of silently guessing.
"""
from __future__ import annotations

import re

try:
    import pycantonese

    _HAS_PYCT = True
except Exception:
    _HAS_PYCT = False

# Fallback mini-dictionary (demo sentences + common words).
FALLBACK_DICT = {
    "各": "gok3", "位": "wai2", "聽": "ting1", "眾": "zung3", "早": "zou2",
    "晨": "san4", "歡": "fun1", "迎": "jing4", "收": "sau1", "今": "gam1",
    "日": "jat6", "嘅": "ge3", "新": "san1", "聞": "man4", "報": "bou3",
    "道": "dou6", "天": "tin1", "氣": "hei3", "比": "bei2", "較": "gaau3",
    "潮": "ciu4", "濕": "sap1", "下": "haa6", "午": "ng5", "可": "ho2",
    "能": "nang4", "會": "wui5", "有": "jau5", "驟": "zau6", "雨": "jyu5",
    "文": "man4", "台": "toi4", "提": "tai4", "醒": "sing2", "市": "si5",
    "民": "man4", "出": "ceot1", "門": "mun4", "口": "hau2", "之": "zi1",
    "前": "cin4", "記": "gei3", "得": "dak1", "帶": "daai3", "遮": "ze1",
    "交": "gaau1", "通": "tung1", "方": "fong1", "面": "min6", "港": "gong2",
    "鐵": "tit3", "荃": "cyun4", "灣": "waan1", "綫": "sin3", "而": "ji4",
    "家": "gaa1", "服": "fuk6", "務": "mou6", "正": "zing3", "常": "soeng4",
    "不": "bat1", "過": "gwo3", "紅": "hung4", "磡": "ham3", "海": "hoi2",
    "底": "dai2", "隧": "seoi6", "往": "wong5", "香": "hoeng1", "向": "hoeng3",
    "擠": "zai1", "塞": "sak1", "車": "ce1", "龍": "lung4", "排": "paai4",
    "到": "dou3", "去": "heoi3", "理": "lei5", "工": "gung1", "大": "daai6",
    "學": "hok6",
}

_IS_CJK = re.compile(r"[一-鿿]")

# Curated per-character readings that override pycantonese where it is missing
# or demonstrably wrong for Hong Kong radio usage.
OVERRIDES = {
    "排": "paai4",
    "諜": "dip6",
    "遨": "ngou4",
    "岑": "sam4",
    "欖": "laam5",
    "磡": "ham3",
    "髒": "zong1",   # HK spoken Cantonese, not Mandarin zang1
    "骯": "ong1",    # colloquial ong1 (骯髒), not the literary kong3
}


def _fallback_convert(text: str) -> str:
    out = []
    for ch in text:
        if _IS_CJK.match(ch):
            out.append(FALLBACK_DICT.get(ch, "〔?〕"))
        elif ch.strip():
            out.append(ch)
    return " ".join(t for t in out if t)


def space_syllables(text: str) -> str:
    """Insert spaces between concatenated LSHK syllables (e.g. giu3zou6 -> giu3 zou6)."""
    return re.sub(r"([1-6])(?=[a-z])", r"\1 ", text or "").strip()


# Known Mandarin-influenced readings to correct to the Hong Kong spoken reading.
READING_FIXES = {
    "zang1": "zong1",   # 髒 — HK spoken Cantonese is zong1, not Mandarin zang1
}


def correct_jyutping(text: str) -> str:
    """Space syllables and fix known Mandarin-influenced readings."""
    return " ".join(READING_FIXES.get(t, t) for t in space_syllables(text).split())


def authoritative_jyutping(text: str, llm_jyut: str = "") -> str:
    """Dictionary-derived LSHK Jyutping — the authoritative Hong Kong reading.

    HARD RULE: Jyutping is always taken from the dictionary (pycantonese +
    OVERRIDES), never from the LLM's romanisation, to avoid teaching wrong
    readings. This covers pure Cantonese text (CJK + punctuation). Only
    mixed Chinese/English input (Latin letters/digits) falls back to the LLM's
    romanisation (space-normalised + reading-fixed), since the dictionary
    cannot romanise English words.
    """
    if text and not re.search(r"[A-Za-z0-9]", text):
        return to_jyutping(text)
    return correct_jyutping(llm_jyut)


def to_jyutping(text: str) -> str:
    """Convert Cantonese text to LSHK Jyutping, one romanisation per character.

    Re-splits pycantonese's word-level segments back into per-character
    syllables and applies ``OVERRIDES`` per character, so a colloquial reading
    (e.g. 骯 ong1, 髒 zong1) wins over a literary/Mandarin one (kong3 / zang1).
    """
    toks = []
    if _HAS_PYCT:
        for seg, jyut in pycantonese.characters_to_jyutping(text):
            chars = list(seg)
            sylls = space_syllables(jyut).split() if jyut else []
            if len(chars) == len(sylls) and len(chars) > 1:
                for c, s in zip(chars, sylls):
                    toks.append(OVERRIDES.get(c, s))
            else:
                for c in chars:
                    if c in OVERRIDES:
                        toks.append(OVERRIDES[c])
                    elif _IS_CJK.match(c):
                        toks.append(jyut or "〔?〕")
                    elif c.strip():
                        toks.append(c)
    else:
        for ch in text:
            if _IS_CJK.match(ch):
                toks.append(OVERRIDES.get(ch, FALLBACK_DICT.get(ch, "〔?〕")))
            elif ch.strip():
                toks.append(ch)
    return " ".join(t for t in toks if t.strip())
