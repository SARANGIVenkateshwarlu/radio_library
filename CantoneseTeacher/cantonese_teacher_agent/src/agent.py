"""Cantonese teacher agent pipeline.

Flow: image -> vision model description -> teacher LLM -> validated lesson JSON.
The lesson JSON is then handed to pdf_generator.build_pdf().

Set OPENAI_API_KEY (or adapt `call_llm`) before running against live models.
"""

import base64
import json
import os
import re
from pathlib import Path

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "cantonese_teacher_system.md"

REQUIRED_KEYS = {"title", "sentences", "qa", "vocabulary"}


def load_system_prompt() -> str:
    return PROMPT_PATH.read_text(encoding="utf-8")


def encode_image(image_path: str) -> str:
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("ascii")


def describe_image(image_path: str) -> str:
    """Call a vision model to get a structured description of the image.

    Replace the body with your multimodal model of choice (GPT-4o, LLaVA, ...).
    """
    import openai  # pip install openai

    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": (
                    "Describe this image for a Cantonese teacher: main objects, people, "
                    "actions, setting, and any Hong Kong daily-life context."
                )},
                {"type": "image_url", "image_url": {
                    "url": f"data:image/jpeg;base64,{encode_image(image_path)}"
                }},
            ],
        }],
    )
    return resp.choices[0].message.content


def generate_lesson(image_description: str) -> dict:
    """Ask the Cantonese teacher LLM for the lesson JSON."""
    import openai

    client = openai.OpenAI()
    resp = client.chat.completions.create(
        model="gpt-4o",
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": load_system_prompt()},
            {"role": "user", "content": f"Image description:\n{image_description}"},
        ],
    )
    return validate_lesson(json.loads(resp.choices[0].message.content))


JYUTPING_TOKEN = re.compile(r"^[a-z]+[1-6]$", re.IGNORECASE)


def _valid_jyutping(text: str) -> bool:
    tokens = re.sub(r"[,.!?;:\"'()]", " ", text).split()
    return bool(tokens) and all(JYUTPING_TOKEN.match(t) for t in tokens)


def validate_lesson(lesson: dict) -> dict:
    """Basic structural + Jyutping sanity checks before rendering."""
    missing = REQUIRED_KEYS - lesson.keys()
    if missing:
        raise ValueError(f"Lesson JSON missing keys: {missing}")
    if len(lesson["sentences"]) != 10:
        raise ValueError("Expected exactly 10 sentences.")
    if not (12 <= len(lesson["vocabulary"]) <= 20):
        raise ValueError("Vocabulary must contain 12-20 entries.")
    for s in lesson["sentences"]:
        if not _valid_jyutping(s["jyutping"]):
            raise ValueError(f"Suspicious Jyutping: {s['jyutping']!r}")
    return lesson


def run(image_path: str, out_json: str) -> dict:
    description = describe_image(image_path)
    lesson = generate_lesson(description)
    lesson["image_path"] = image_path
    Path(out_json).write_text(
        json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return lesson
