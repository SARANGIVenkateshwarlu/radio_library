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


def _fallback_convert(text: str) -> str:
    out = []
    for ch in text:
        if _IS_CJK.match(ch):
            out.append(FALLBACK_DICT.get(ch, "〔?〕"))
        elif ch.strip():
            out.append(ch)
    return " ".join(t for t in out if t)


def to_jyutping(text: str) -> str:
    """Convert Cantonese text to Jyutping, one romanisation per character."""
    if _HAS_PYCT:
        pairs = pycantonese.characters_to_jyutping(text)
        toks = [jyut if jyut else (ch if not _IS_CJK.match(ch) else "〔?〕")
                for ch, jyut in pairs]
        return " ".join(t for t in toks if t.strip())
    return _fallback_convert(text)
