"""Cantonese G2P — Chinese characters to LSHK Jyutping (tone numbers 1-6).

Dictionary-based via pycantonese; unknown characters are marked 〔?〕 rather
than guessed. Jyutping is never produced by an LLM.
"""
from __future__ import annotations

import re
import sys

_CJK = re.compile(r"[\u3400-\u9fff]")
try:
    import pycantonese
    _HAS = True
except Exception:
    _HAS = False


def to_jyutping(text: str) -> str:
    toks = []
    if _HAS:
        for ch, jyut in pycantonese.characters_to_jyutping(text):
            toks.append(jyut or (ch if not _CJK.match(ch) else "〔?〕"))
    else:
        toks = [ch for ch in text]
    return " ".join(t for t in toks if t.strip())


if __name__ == "__main__":
    print(to_jyutping(" ".join(sys.argv[1:]) or "今日天氣好好"))
