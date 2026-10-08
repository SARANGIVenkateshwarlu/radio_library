#!/usr/bin/env python3
"""CLI entry point to test the LangGraph pipeline.

Usage:
    python run_pipeline.py --audio "audio/2026-10-07_RTHK_5min.mp3" --mock-asr
"""
import argparse
import sys

from app.graph import run

# Windows consoles default to cp1252, which cannot print Cantonese output.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        _stream.reconfigure(encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio", required=True, help="path to the MP3 (YYYY-MM-DD_station_duration.mp3)")
    ap.add_argument("--mock-asr", action="store_true", help="use the offline demo ASR")
    ap.add_argument("--clean-audio", action="store_true",
                    help="isolate vocals / denoise before ASR (Demucs, ffmpeg fallback)")
    args = ap.parse_args()

    final = run(args.audio, mock_asr=args.mock_asr, clean_audio=args.clean_audio)

    print(f"\n=== Pipeline finished: {final['recording_id']} ===")
    for s in final["segments"]:
        print(f"\n[{s['start']:>6.1f}s -> {s['end']:>6.1f}s]")
        print("  粵語: ", s["corrected"])
        print("  粵拼: ", s["jyutping"])
        print("  ENG:  ", s["english"])
        if s.get("uncertain"):
            print("  (!) contains uncertain items")
    print(f"\nPDF:        {final['pdf_path']}")
    print(f"JSON:       {final['transcript_json_path']}")
    print(f"SRT:        {final['srt_path']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
