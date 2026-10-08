"""Project configuration: paths and environment settings."""
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

AUDIO_DIR = BASE_DIR / "audio"
TRANSCRIPT_DIR = BASE_DIR / "transcripts"
PDF_DIR = BASE_DIR / "pdf"
SUBTITLE_DIR = BASE_DIR / "subtitles"
METADATA_DIR = BASE_DIR / "metadata"
DB_PATH = METADATA_DIR / "library.db"

for d in (AUDIO_DIR, TRANSCRIPT_DIR, PDF_DIR, SUBTITLE_DIR, METADATA_DIR):
    d.mkdir(parents=True, exist_ok=True)

# LLM (OpenAI-compatible via LangChain). Falls back to MockLLM if unset.
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")
