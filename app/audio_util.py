"""Audio helpers: speed control and saving uploaded MP3s."""
from __future__ import annotations

import re
import shutil
import subprocess
from datetime import date
from pathlib import Path

from . import config

SPEED_DIR = config.METADATA_DIR / "speed"


def speed_adjusted(src: str | None, speed: float) -> bytes | None:
    """Return MP3 bytes played at ``speed`` (0.5x–2x), pitch preserved.

    Results are cached under ``metadata/speed/``. Returns None if the source
    is missing or ffmpeg is unavailable.
    """
    if not src:
        return None
    path = Path(src)
    if not path.exists():
        return None
    if abs(speed - 1.0) < 1e-6:
        return path.read_bytes()

    SPEED_DIR.mkdir(parents=True, exist_ok=True)
    dst = SPEED_DIR / f"{path.stem}_{speed:g}x.mp3"
    if dst.exists():
        return dst.read_bytes()

    if shutil.which(config.FFMPEG_BINARY) is None:
        return None
    cmd = [config.FFMPEG_BINARY, "-y", "-v", "error", "-i", str(path),
           "-filter:a", f"atempo={speed}", "-b:a", "192k", str(dst)]
    try:
        subprocess.run(cmd, check=True, timeout=600)
    except (OSError, subprocess.SubprocessError):
        return None
    return dst.read_bytes() if dst.exists() else None


def probe_duration(path: str | Path) -> float | None:
    """Duration in seconds for an audio/video file, or None if it can't tell."""
    path = Path(path)
    ffprobe = shutil.which("ffprobe")
    if ffprobe:
        out = subprocess.run(
            [ffprobe, "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", str(path)],
            capture_output=True, text=True, timeout=30)
        try:
            return float(out.stdout.strip())
        except ValueError:
            pass
    # fallback: parse the ffmpeg header
    out = subprocess.run([config.FFMPEG_BINARY, "-i", str(path)],
                         capture_output=True, text=True, timeout=30)
    m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", out.stderr)
    if m:
        return int(m.group(1)) * 3600 + int(m.group(2)) * 60 + float(m.group(3))
    return None


def save_upload_mp3(data: bytes, source: str = "custom",
                    when: date | None = None) -> tuple[str, float]:
    """Save an uploaded MP3 into ``audio/`` with the standard filename.

    Name: ``YYYY-MM-DD_<source>_<minutes>min.mp3`` (duration probed), which the
    pipeline already parses — so an uploaded file is processed exactly like a
    radio recording. Returns (path, duration_seconds).
    """
    stamp = (when or date.today()).strftime("%Y-%m-%d")
    tag = re.sub(r"[^A-Za-z0-9-]+", "-", source or "").strip("-") or "custom"
    tag = tag[:40]

    tmp = config.AUDIO_DIR / f"{stamp}_{tag}_tmp.mp3"
    k = 2
    while tmp.exists():
        tmp = config.AUDIO_DIR / f"{stamp}_{tag}_tmp_{k}.mp3"
        k += 1
    tmp.write_bytes(data)

    duration = probe_duration(tmp) or 0.0
    minutes = max(1, round(duration / 60))
    final = config.AUDIO_DIR / f"{stamp}_{tag}_{minutes}min.mp3"
    k = 2
    while final.exists():
        final = config.AUDIO_DIR / f"{stamp}_{tag}_{minutes}min_{k}.mp3"
        k += 1
    tmp.replace(final)
    return str(final), duration
