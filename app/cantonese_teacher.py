"""Cantonese Teacher agent — image -> lesson JSON -> worksheet PDF.

Integration of the standalone CantoneseTeacher project: a photo of a Hong
Kong scene is described by a vision model, the teacher LLM turns it into a
lesson JSON (10 sentences, Q&A, vocabulary), validated, and rendered as a
colour-coded A4 PDF worksheet (see ``app/cantonese_pdf.py``).

Uses the app's configured OpenAI-compatible endpoint (``OPENAI_BASE_URL``).
Without a vision-capable model, pass a manual description instead; demo mode
uses the bundled minibus lesson.
"""
from __future__ import annotations

import base64
import json
import re
from datetime import datetime
from pathlib import Path

from . import config

CT_ROOT = config.BASE_DIR / "CantoneseTeacher" / "cantonese_teacher_agent"
SYSTEM_PROMPT_PATH = CT_ROOT / "prompts" / "cantonese_teacher_system.md"
DEMO_LESSON_PATH = CT_ROOT / "data" / "minibus_lesson.json"

REQUIRED_KEYS = {"title", "sentences", "qa", "vocabulary"}


def load_system_prompt() -> str:
    try:
        return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
    except OSError:
        return "You are a Cantonese teacher. Produce lesson JSON for the image."


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def demo_lesson(theme: str = "") -> dict:
    """The bundled minibus lesson (offline / reproducible)."""
    lesson = json.loads(DEMO_LESSON_PATH.read_text(encoding="utf-8"))
    if theme.strip():
        lesson["title"] = f"Cantonese Class 廣東話課堂 – {theme.strip()}"
    return lesson


def _client():
    import openai

    return openai.OpenAI(
        api_key=config.OPENAI_API_KEY or "none",
        base_url=config.OPENAI_BASE_URL,
        timeout=180,
    )


def describe_image(image_path: str, model: str | None = None) -> str:
    """Vision description of the image via the configured endpoint."""
    client = _client()
    resp = client.chat.completions.create(
        model=model or config.CANTONESE_TEACHER_MODEL,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Describe this image for a Cantonese teacher: main objects, "
                    "people, actions, setting, and any Hong Kong daily-life "
                    "context.")},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{encode_image(image_path)}"}},
            ],
        }],
    )
    return resp.choices[0].message.content


def generate_lesson(image_description: str, model: str | None = None) -> dict:
    """Ask the Cantonese teacher LLM for the lesson JSON."""
    client = _client()
    resp = client.chat.completions.create(
        model=model or config.CANTONESE_TEACHER_MODEL,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": f"Image description:\n{image_description}"},
        ],
    )
    return validate_lesson(json.loads(resp.choices[0].message.content))


_JYUTPING_TOKEN = re.compile(r"^[a-z]+[1-6]$", re.IGNORECASE)


def validate_lesson(lesson: dict) -> dict:
    """Structure + Jyutping sanity checks before rendering."""
    missing = REQUIRED_KEYS - lesson.keys()
    if missing:
        raise ValueError(f"Lesson JSON missing keys: {missing}")
    if len(lesson["sentences"]) != 10:
        raise ValueError("Expected exactly 10 sentences.")
    if not (12 <= len(lesson["vocabulary"]) <= 20):
        raise ValueError("Vocabulary must contain 12-20 entries.")
    for s in lesson["sentences"]:
        text = re.sub(r"[,.!?;:\"'()]", " ", s.get("jyutping", "")).split()
        if not text or not all(_JYUTPING_TOKEN.match(t) for t in text):
            raise ValueError(f"Suspicious Jyutping: {s.get('jyutping')!r}")
    return lesson


def build_image_pdf(lesson: dict, image_path: str, out_path: str) -> str:
    from . import cantonese_pdf

    return cantonese_pdf.build_pdf(lesson, image_path, out_path)


def lesson_dir() -> Path:
    d = config.METADATA_DIR / "cantonese_teacher"
    d.mkdir(parents=True, exist_ok=True)
    return d


def next_lesson_index(day: str | None = None) -> int:
    """Next lesson number for a date (YYYY-MM-DD_lesson_N)."""
    day = day or datetime.now().strftime("%Y-%m-%d")
    prefix = f"{day}_lesson_"
    highest = 0
    for p in lesson_dir().glob(prefix + "*.pdf"):
        m = re.match(re.escape(prefix) + r"(\d+)\.pdf$", p.name)
        if m:
            highest = max(highest, int(m.group(1)))
    return highest + 1


def list_lessons() -> list[dict]:
    """Previously generated worksheets, newest first."""
    items = []
    for p in sorted(lesson_dir().glob("*.pdf"), reverse=True):
        items.append({
            "name": p.stem,
            "pdf": p,
            "json": p.with_suffix(".json"),
            "size": p.stat().st_size,
            "mtime": datetime.fromtimestamp(p.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
        })
    return items


def generate_worksheet(image_path: str, theme: str = "", num_qa: int = 3,
                       description: str = "", use_demo: bool = False,
                       out_dir=None) -> tuple[str, str | None, str]:
    """Full pipeline. Returns (pdf_path, warning_or_None, lesson_name).

    Files are named ``YYYY-MM-DD_lesson_N`` (reviewable in the app) and the
    lesson JSON is saved alongside the PDF.
    """
    out_dir = Path(out_dir) if out_dir else lesson_dir()
    out_dir.mkdir(parents=True, exist_ok=True)
    name = f"{datetime.now().strftime('%Y-%m-%d')}_lesson_{next_lesson_index()}"
    pdf_path = out_dir / f"{name}.pdf"

    warning = None
    try:
        if use_demo:
            lesson = demo_lesson(theme)
        else:
            desc = (description or "").strip()
            if not desc:
                desc = describe_image(image_path)
            lesson = generate_lesson(desc)
            lesson = validate_lesson(lesson)
        if theme.strip():
            lesson["title"] = f"Cantonese Class 廣東話課堂 – {theme.strip()}"
        lesson["qa"] = lesson["qa"][:num_qa]
        build_image_pdf(lesson, image_path, str(pdf_path))
    except Exception as exc:  # LLM/vision failure → reproducible demo lesson
        warning = f"AI generation failed ({exc}); used the demo lesson instead."
        lesson = demo_lesson(theme)
        lesson["qa"] = lesson["qa"][:num_qa]
        build_image_pdf(lesson, image_path, str(pdf_path))

    (out_dir / f"{name}.json").write_text(
        json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(pdf_path), warning, name