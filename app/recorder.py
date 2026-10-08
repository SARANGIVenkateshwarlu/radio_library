"""Direct internet-stream recorder (no microphone → no room noise).

Captures the station's own digital stream with ffmpeg and encodes it to
high-quality MP3. Files are saved under audio/ using the pipeline's naming
convention so they can be processed immediately.

Note: standard MP3 (libmp3lame) tops out at 320 kbps — there is no 360 kbps
MP3 mode. 320k is the highest-quality setting and is used by default.
"""
from __future__ import annotations

import shutil
import subprocess
import time
import uuid
from datetime import datetime
from pathlib import Path

from . import config


def ffmpeg_available() -> bool:
    """True if the ffmpeg executable can be found."""
    return shutil.which(config.FFMPEG_BINARY) is not None

STATIONS = {
    "RTHK Radio 1": "https://stm1.rthk.hk/radio1",
    "RTHK Radio 2": "https://stm1.rthk.hk/radio2",
    "RTHK Radio 3": "https://stm1.rthk.hk/radio3",
    "RTHK Radio 4": "https://stm1.rthk.hk/radio4",
    "RTHK Radio 5": "https://stm1.rthk.hk/radio5",
}

# Highest standard MP3 bitrate (no 360k mode exists for MP3).
BITRATES = ["128k", "192k", "256k", "320k"]

_jobs: dict[str, dict] = {}


def _slug(station: str) -> str:
    return station.lower().replace(" ", "-")


def start_recording(station: str, url: str, duration_s: int, bitrate: str = "320k") -> dict:
    """Start a background ffmpeg recording. Returns a job dict."""
    if not ffmpeg_available():
        raise RuntimeError(
            f"ffmpeg was not found (looked for '{config.FFMPEG_BINARY}' on PATH). "
            "Install it and reopen the terminal, e.g. on Windows run "
            "`winget install Gyan.FFmpeg`, then restart the app. You can also "
            "set the FFMPEG_BINARY env var to the full path of ffmpeg.exe."
        )

    dur_min = max(1, round(duration_s / 60))
    stamp = datetime.now().strftime("%Y-%m-%d")
    out_path = config.AUDIO_DIR / f"{stamp}_{_slug(station)}_{dur_min}min.mp3"
    # avoid overwriting an existing recording from earlier today
    n = 2
    while out_path.exists():
        out_path = config.AUDIO_DIR / f"{stamp}_{_slug(station)}_{dur_min}min_{n}.mp3"
        n += 1

    job_id = uuid.uuid4().hex[:8]
    log_path = config.METADATA_DIR / f"rec_{job_id}.log"

    cmd = [
        config.FFMPEG_BINARY, "-y",
        "-reconnect", "1", "-reconnect_streamed", "1", "-reconnect_delay_max", "5",
        "-i", url,
        "-t", str(duration_s),
        "-vn",
        "-codec:a", "libmp3lame",
        "-b:a", bitrate,
        "-ar", "44100",
        "-ac", "2",
        str(out_path),
    ]
    log = open(log_path, "wb")
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=log)
    except OSError as exc:
        log.close()
        raise RuntimeError(f"could not launch ffmpeg: {exc}") from exc
    job = {
        "id": job_id,
        "proc": proc,
        "station": station,
        "url": url,
        "out_path": str(out_path),
        "log_path": str(log_path),
        "_log": log,
        "duration_s": duration_s,
        "bitrate": bitrate,
        "started": time.time(),
    }
    _jobs[job_id] = job
    return job


def _close_log(job: dict) -> None:
    handle = job.get("_log")
    if handle is not None:
        try:
            handle.close()
        except OSError:
            pass
        job["_log"] = None


def job_status(job_id: str) -> dict:
    job = _jobs[job_id]
    rc = job["proc"].poll()
    elapsed = time.time() - job["started"]
    out = Path(job["out_path"])
    if rc is not None:
        _close_log(job)

    error_tail = ""
    log_path = Path(job["log_path"])
    if log_path.exists():
        lines = log_path.read_text(encoding="utf-8", errors="replace").strip().splitlines()
        error_tail = "\n".join(lines[-6:])

    return {
        "id": job_id,
        "station": job["station"],
        "out_path": job["out_path"],
        "duration_s": job["duration_s"],
        "bitrate": job["bitrate"],
        "elapsed_s": min(elapsed, job["duration_s"]),
        "progress": min(elapsed / job["duration_s"], 1.0),
        "running": rc is None,
        "finished": rc == 0,
        "error": rc not in (None, 0),
        "size_bytes": out.stat().st_size if out.exists() else 0,
        "error_tail": error_tail,
    }


def stop_recording(job_id: str) -> dict:
    job = _jobs[job_id]
    if job["proc"].poll() is None:
        job["proc"].terminate()
        try:
            job["proc"].wait(timeout=5)
        except subprocess.TimeoutExpired:
            job["proc"].kill()
    return job_status(job_id)


def active_jobs() -> list[str]:
    return list(_jobs.keys())
