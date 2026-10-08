"""RTHK radio timetable — today's schedule for the 5 FM channels.

The RTHK schedule page is server-rendered and contains every channel's block
(``id="scrollradio1"`` … ``scrollradio5``), so one fetch covers all channels.
Programmes are classified as ``talk`` (spoken — recommended for listening) or
``music`` by keyword; talk rows are highlighted green+bold in the UI.
"""
from __future__ import annotations

import html as _html
import re
import time as _time
from datetime import datetime

import requests

URL = "https://www.rthk.hk/radio/radio1/schedule"
CHANNELS = {
    1: "RTHK Radio 1 · 第一台",
    2: "RTHK Radio 2 · 第二台",
    3: "RTHK Radio 3 · 第三台",
    4: "RTHK Radio 4 · 第四台",
    5: "RTHK Radio 5 · 第五台",
}
CACHE_TTL = 1800  # seconds

_TIME_RE = re.compile(r'class="radTime">([^<]+)<')
_TITLE_RE = re.compile(r'title="([^"]*)"')
_SLUG_RE = re.compile(r'data-f="([^"]*)"')
_RANGE_RE = re.compile(r"(\d{1,2}):(\d{2})\s*-\s*(\d{1,2}):(\d{2})")

# Anything matching these is treated as music (not highlighted).
_MUSIC_KEYS = [
    "音樂", "歌曲", "歌劇", "粵曲", "粵劇", "戲曲", "金曲", "演唱", "演奏",
    "交響", "管弦", "爵士", "古典", "合唱", "民歌", "旋律", "樂團", "樂隊",
    "美樂", "純音樂", "中樂", "西樂",
    "music", "song", "opera", "classical", "jazz", "melody", "symphon",
    "concerto", "orchestra", "ensemble", "chamber",
    "aubade", "nocturne", "nightmusic", "night music",
    "firstnotes", "first notes", "nonstopclassics", "non-stop classics",
    "tco",
]

_cache: dict = {}


def _categorize(title: str, slug: str) -> str:
    text = f"{title} {slug}".lower()
    return "music" if any(k in text for k in _MUSIC_KEYS) else "talk"


def _parse_all(page: str) -> dict[int, list[dict]]:
    out: dict[int, list[dict]] = {}
    for n in range(1, 6):
        start = page.find(f'id="scrollradio{n}"')
        end = page.find(f'id="scrollradio{n + 1}"')
        if start == -1:
            out[n] = []
            continue
        if end == -1:
            end = len(page)
        section = page[start:end]
        rows = []
        for block in section.split('class="radListBlock"')[1:]:
            mt = _TIME_RE.search(block)
            if not mt:
                continue
            mti = _TITLE_RE.search(block)
            ms = _SLUG_RE.search(block)
            title = _html.unescape(mti.group(1)) if mti else ""
            slug = ms.group(1) if ms else ""
            rows.append({
                "time": mt.group(1).strip(),
                "title": title.strip(),
                "slug": slug,
                "category": _categorize(title, slug),
            })
        out[n] = rows
    return out


def get_timetable(force: bool = False) -> dict[int, list[dict]]:
    """Today's per-channel schedule (cached for CACHE_TTL seconds)."""
    now = _time.time()
    cached = _cache.get("data")
    if cached and not force and now - cached[0] < CACHE_TTL:
        return cached[1]
    resp = requests.get(URL, timeout=20)
    resp.encoding = "utf-8"
    data = _parse_all(resp.text)
    _cache["data"] = (now, data)
    return data


def on_air(rows: list[dict], now: datetime | None = None) -> dict | None:
    """Return the programme currently airing, or None."""
    now = now or datetime.now()
    cur = now.hour * 60 + now.minute
    for r in rows:
        m = _RANGE_RE.match(r.get("time", ""))
        if not m:
            continue
        start = int(m.group(1)) * 60 + int(m.group(2))
        end = int(m.group(3)) * 60 + int(m.group(4))
        if start <= cur < end:
            return r
    return None
