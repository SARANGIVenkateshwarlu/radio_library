"""Audio cleanup before transcription.

Primary path: **Demucs** (htdemucs) isolates the vocal stem, dropping
background music. Fallback: an ffmpeg denoise/normalise filter chain (removes
hiss and noise, but not music that overlaps the voice).

Both write a cleaned file under ``metadata/cleaned/`` and return
``(path, method)`` where method is ``"demucs"``, ``"ffmpeg"`` or ``"none"``.
"""
from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from . import config

CLEAN_DIR = config.METADATA_DIR / "cleaned"

# ffmpeg fallback: rumble cut, hiss cut, FFT denoise, normalise loudness.
_FFMPEG_AF = "highpass=f=90,lowpass=f=8000,afftdn=nf=-25,dynaudnorm,loudnorm=I=-16:TP=-1.5:LRA=11"


def demucs_available() -> bool:
    return importlib.util.find_spec("demucs") is not None


def _demucs(src: Path, dst: Path, model: str = "htdemucs") -> str:
    tmp = Path(tempfile.mkdtemp(prefix="demucs_"))
    cmd = [sys.executable, "-m", "demucs", "--two-stems=vocals",
           "--mp3", "-n", model, "-o", str(tmp), str(src)]
    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=3600)
        stem_dir = tmp / model / src.stem
        for name in ("vocals.mp3", "vocals.wav"):
            candidate = stem_dir / name
            if candidate.exists():
                shutil.copyfile(candidate, dst)
                return str(dst)
        raise RuntimeError("demucs produced no vocals stem")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _ffmpeg_clean(src: Path, dst: Path) -> str:
    cmd = [config.FFMPEG_BINARY, "-y", "-v", "error", "-i", str(src),
           "-af", _FFMPEG_AF, "-ac", "1", "-ar", "16000", str(dst)]
    subprocess.run(cmd, check=True, timeout=3600)
    return str(dst)


def clean_audio(src: str | Path, model: str = "htdemucs") -> tuple[str, str]:
    """Return (cleaned_file_path, method). Falls back to the original on error."""
    src = Path(src)
    CLEAN_DIR.mkdir(parents=True, exist_ok=True)
    suffix = ".mp3" if demucs_available() else ".wav"
    dst = CLEAN_DIR / f"{src.stem}_vocals{suffix}"

    if demucs_available():
        try:
            return _demucs(src, dst, model), "demucs"
        except Exception:
            pass
    try:
        return _ffmpeg_clean(src, CLEAN_DIR / f"{src.stem}_clean.wav"), "ffmpeg"
    except Exception:
        return str(src), "none"
