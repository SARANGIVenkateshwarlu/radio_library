"""Assign transcript segments to blocks for the compact PDF layout.

A block is a run of 3-6 sentences. Boundaries fall on a topic change or a
pause. When an LLM is configured it proposes the topic boundaries; otherwise
pause gaps are used. Block sizes are always clamped to MIN_SIZE..MAX_SIZE.
"""
from __future__ import annotations

import os
import re

from . import config


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _float_env(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


MIN_SIZE = _int_env("BLOCK_MIN", 3)
MAX_SIZE = _int_env("BLOCK_MAX", 6)
PAUSE_SECONDS = _float_env("PAUSE_SPLIT_SECONDS", 1.0)


def _pause_blocks(segments: list[dict]) -> list[list[dict]]:
    blocks: list[list[dict]] = []
    cur: list[dict] = []
    prev_end = None
    for s in segments:
        if cur:
            gap = (s.get("start", 0.0) - prev_end) if prev_end is not None else 0.0
            if gap >= PAUSE_SECONDS or len(cur) >= MAX_SIZE:
                blocks.append(cur)
                cur = []
        cur.append(s)
        prev_end = s.get("end", prev_end)
    if cur:
        blocks.append(cur)
    return blocks


def _llm_starts(segments: list[dict]) -> list[int] | None:
    """Topic boundaries proposed by the LLM as 0-based start indices."""
    if not config.LLM_ENABLED:
        return None
    try:
        from .llm import group_chain

        listing = "\n".join(
            f"{i + 1}. {s.get('corrected') or s.get('cantonese', '')}"
            for i, s in enumerate(segments)
        )
        out = group_chain().invoke({"text": listing}).content
        nums = sorted({int(x) for x in re.findall(r"\d+", out)})
        starts = [n - 1 for n in nums if 1 <= n <= len(segments)]
        if not starts or starts[0] != 0:
            return None
        # guard against the model echoing every line number (=> all size 1)
        if len(starts) > max(2, len(segments) // 2):
            return None
        return starts
    except Exception:
        return None


def _blocks_from_starts(segments: list[dict], starts: list[int]) -> list[list[dict]]:
    bounds = starts + [len(segments)]
    return [segments[bounds[i]:bounds[i + 1]] for i in range(len(bounds) - 1)]


def _split_block(block: list[dict]) -> list[list[dict]]:
    n = len(block)
    if n <= MAX_SIZE:
        return [block]
    parts = -(-n // MAX_SIZE)  # ceil
    base, rem = divmod(n, parts)
    sizes = [base + 1] * rem + [base] * (parts - rem)
    out, i = [], 0
    for size in sizes:
        out.append(block[i:i + size])
        i += size
    return out


def _enforce_sizes(blocks: list[list[dict]]) -> list[list[dict]]:
    # 1) merge undersized blocks into the previous one when it stays <= MAX
    merged: list[list[dict]] = []
    for b in blocks:
        if merged and len(b) < MIN_SIZE and len(merged[-1]) + len(b) <= MAX_SIZE:
            merged[-1].extend(b)
        else:
            merged.append(b)
    if len(merged) >= 2 and len(merged[0]) < MIN_SIZE and len(merged[0]) + len(merged[1]) <= MAX_SIZE:
        merged[1] = merged[0] + merged[1]
        merged.pop(0)
    # 2) split oversized blocks evenly into 3-6 sentence pieces
    split: list[list[dict]] = []
    for b in merged:
        split.extend(_split_block(b))
    # 3) merge a tiny trailing remainder back
    if len(split) >= 2 and len(split[-1]) < MIN_SIZE and len(split[-2]) + len(split[-1]) <= MAX_SIZE:
        split[-2].extend(split[-1])
        split.pop()
    return split


def assign_blocks(segments: list[dict]) -> list[dict]:
    """Return copies of segments with an added ``block`` index."""
    if not segments:
        return []
    starts = _llm_starts(segments)
    blocks = _blocks_from_starts(segments, starts) if starts else _pause_blocks(segments)
    blocks = _enforce_sizes(blocks)
    out: list[dict] = []
    for bi, block in enumerate(blocks):
        for s in block:
            s = dict(s)
            s["block"] = bi
            out.append(s)
    return out
