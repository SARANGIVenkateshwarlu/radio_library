"""Cantonese text normalisation for TTS.

Full-width normalisation, whitespace cleanup, and (starter) number/date
expansion into Cantonese readings. Extend the tables for production coverage.
"""
from __future__ import annotations

import re
import sys
import unicodedata

_DIGITS = {"0": "零", "1": "一", "2": "二", "3": "三", "4": "四",
           "5": "五", "6": "六", "7": "七", "8": "八", "9": "九"}
_UNITS = {0: "", 1: "十", 2: "百", 3: "千", 4: "萬"}

# English stays English (code-switch). Add more symbols as needed.
_SYMBOLS = {"%": "巴仙", "℃": "度", "$": "蚊", "￥": "蚊"}


def digits_to_cantonese(number: str) -> str:
    """Very small integer→Cantonese reader (extend for decimals/years)."""
    if not number.isdigit():
        return number
    if len(number) <= 1:
        return _DIGITS[number]
    out, n = [], int(number)
    for i in range(len(number)):
        d = int(number[i])
        pos = len(number) - 1 - i
        if d:
            out.append(_DIGITS[str(d)] + _UNITS.get(pos, ""))
        elif out and out[-1] != "零":
            out.append("零")
    return "".join(out).rstrip("零")


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKC", text)
    for sym, word in _SYMBOLS.items():
        text = text.replace(sym, word)
    text = re.sub(r"\d+", lambda m: digits_to_cantonese(m.group()), text)
    return re.sub(r"\s+", " ", text).strip()


if __name__ == "__main__":
    print(normalize(" ".join(sys.argv[1:]) or "今日係 2026 年，3.5% 增長。"))
