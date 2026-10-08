#!/usr/bin/env python3
"""Re-run text stages (correct -> jyutping -> translate -> pdf -> library)
from an existing transcript JSON, without re-running ASR.

Usage:
    python regen_outputs.py transcripts/2026-10-07-rthk-001.json
    python regen_outputs.py --all          # every JSON in transcripts/
"""
import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import config, nodes  # noqa: E402


def regen(json_path: Path) -> str:
    rec = json.loads(Path(json_path).read_text(encoding="utf-8"))
    state = {
        "audio_path": rec["audio_file"],
        "recording_id": rec["recording_id"],
        "station": rec.get("station"),
        "recorded_at": rec.get("recorded_at"),
        "duration_seconds": rec.get("duration_seconds"),
        "review_status": rec.get("review_status", "unreviewed"),
        "segments": rec["segments"],
    }
    state.update(nodes.correct(state))
    state.update(nodes.jyutping(state))
    state.update(nodes.translate(state))
    state.update(nodes.generate_pdf(state))
    state.update(nodes.save_to_library(state))
    return state["pdf_path"]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("json", nargs="?", help="transcript JSON path")
    ap.add_argument("--all", action="store_true", help="regenerate all transcripts")
    args = ap.parse_args()

    paths = sorted(config.TRANSCRIPT_DIR.glob("*.json")) if args.all else [Path(args.json)] if args.json else []
    if not paths:
        ap.error("provide a JSON path or --all")
    for p in paths:
        print("regenerated:", p.name, "->", regen(p))
    return 0


if __name__ == "__main__":
    sys.exit(main())
