"""Project configuration: paths and environment settings."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# Load .env from the project root (does not override real OS env vars).
load_dotenv(BASE_DIR / ".env")

AUDIO_DIR = BASE_DIR / "audio"
TRANSCRIPT_DIR = BASE_DIR / "transcripts"
PDF_DIR = BASE_DIR / "pdf"
SUBTITLE_DIR = BASE_DIR / "subtitles"
METADATA_DIR = BASE_DIR / "metadata"
DB_PATH = METADATA_DIR / "library.db"

for d in (AUDIO_DIR, TRANSCRIPT_DIR, PDF_DIR, SUBTITLE_DIR, METADATA_DIR):
    d.mkdir(parents=True, exist_ok=True)


def _iter_raw(*names: str):
    """Yield (name, value) from OS env then Streamlit secrets, in order."""
    for name in names:
        val = os.getenv(name)
        if val:
            yield name, val
    try:  # only populated when running via `streamlit run`
        import streamlit as st

        for name in names:
            if name in st.secrets:
                yield name, str(st.secrets[name])
    except Exception:
        pass


def _setting(*names: str, default: str = "") -> str:
    """First non-empty value from OS env, then Streamlit secrets, else default."""
    for _, val in _iter_raw(*names):
        return val
    return default


# --- xAI (Grok) is the default provider for this project ---------------------
XAI_BASE_URL = "https://api.x.ai/v1"
XAI_MODEL = "grok-4.20-0309-non-reasoning"
OPENAI_BASE_URL_DEFAULT = "https://api.openai.com/v1"
OPENAI_MODEL_DEFAULT = "gpt-4o-mini"

# Values that mean "not filled in yet" — treated as no key (stays in mock mode).
_PLACEHOLDER_MARKERS = (
    "your-key", "your_key", "yourkey", "changeme", "placeholder",
    "xai-...", "sk-...", "<", "xxxx", "paste",
)


def _clean_key(value: str) -> str:
    if not value:
        return ""
    v = value.strip()
    if any(m in v.lower() for m in _PLACEHOLDER_MARKERS):
        return ""
    return v


def _find_key(*names: str) -> str:
    """First real (non-placeholder) key across OS env and Streamlit secrets."""
    for _, val in _iter_raw(*names):
        cleaned = _clean_key(val)
        if cleaned:
            return cleaned
    return ""


_key = _find_key("OPENAI_API_KEY", "XAI_API_KEY")
OPENAI_API_KEY = _key

# Default the endpoint from the key style: xai-... → xAI, otherwise OpenAI.
if _key.startswith("xai-"):
    _base_default, _model_default = XAI_BASE_URL, XAI_MODEL
else:
    _base_default, _model_default = OPENAI_BASE_URL_DEFAULT, OPENAI_MODEL_DEFAULT

OPENAI_BASE_URL = _setting("OPENAI_BASE_URL", "XAI_BASE_URL", default=_base_default)
LLM_MODEL = _setting("LLM_MODEL", "XAI_MODEL", default=_model_default)

# ffmpeg binary (on PATH by default; override if it is not).
FFMPEG_BINARY = _setting("FFMPEG_BINARY", default="ffmpeg")

# True when a real LLM endpoint is configured; otherwise MockLLM is used.
LLM_ENABLED = bool(OPENAI_API_KEY)
LLM_PROVIDER = (
    "xAI (Grok)" if _key.startswith("xai-")
    else "OpenAI-compatible" if LLM_ENABLED
    else "mock (offline)"
)
