#!/usr/bin/env python3
"""End-to-end CLI: image -> lesson JSON -> printable PDF worksheet.

Usage:
    python3 src/main.py <image> [--lesson lesson.json] [--out worksheet.pdf]

If --lesson is given, skip the LLM calls and render from the saved JSON
(useful for offline runs, tests, and reproducible worksheets).
"""

import argparse
import json
from pathlib import Path

import agent
import pdf_generator


def main():
    p = argparse.ArgumentParser(description="Cantonese Class Teacher Agent")
    p.add_argument("image", help="Path to the uploaded image (jpg/png)")
    p.add_argument("--lesson", help="Existing lesson JSON to render (skip LLM)")
    p.add_argument("--out", default="output/worksheet.pdf", help="Output PDF path")
    p.add_argument("--lesson-out", default="data/lesson.json",
                   help="Where to save the generated lesson JSON")
    args = p.parse_args()

    if args.lesson:
        lesson = json.loads(Path(args.lesson).read_text(encoding="utf-8"))
    else:
        lesson = agent.run(args.image, args.lesson_out)

    out = pdf_generator.build_pdf(lesson, args.image, args.out)
    print(f"Worksheet ready: {out}")


if __name__ == "__main__":
    main()
