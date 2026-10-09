"""Audio playback helpers (speed control without changing pitch)."""
from __future__ import annotations

import shutil
import subprocess
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
