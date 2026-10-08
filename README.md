# HK Radio Cantonese Learning Library

A daily pipeline that turns Hong Kong FM radio recordings into a personal
Cantonese-learning library.

```
HK FM recording → MP3 archive → Cantonese transcription → Jyutping → English translation → PDF + searchable library
```

Recordings are for **personal study only**. Hong Kong copyright law protects
broadcasts — do not redistribute or reuse commercially.

## Architecture

The pipeline is orchestrated with **LangGraph** (state machine) and all LLM
calls go through **LangChain** so providers are pluggable (OpenAI-compatible
API, local LLM, or a built-in mock for offline testing).

```
┌──────────────────────────────────────────────────────────────┐
│                        LangGraph pipeline                     │
│                                                              │
│  load_audio → transcribe → correct → jyutping → translate    │
│                                  │                           │
│                        generate_pdf → save_to_library         │
└──────────────────────────────────────────────────────────────┘
        │                                  │
   audio/*.mp3                    SQLite library.db + pdf/*.pdf
```

## Repository Layout

```
radio_library/
├── master.md                 ← full project specification
├── requirements.txt
├── run_pipeline.py           ← CLI entry point (full pipeline incl. ASR)
├── regen_outputs.py          ← re-run text stages from saved JSON (no ASR)
├── streamlit_app.py          ← Streamlit library UI
├── app/
│   ├── config.py             ← paths / env settings
│   ├── state.py              ← LangGraph state schema
│   ├── asr.py                ← ASR providers (mock / pluggable)
│   ├── llm.py                ← LangChain LLM factory (+ mock fallback)
│   ├── jyutping_tool.py      ← pycantonese wrapper + fallback dictionary
│   ├── pdf_gen.py            ← bilingual PDF generator (reportlab)
│   ├── library.py            ← SQLite metadata store
│   ├── recorder.py           ← ffmpeg stream recorder
│   ├── nodes.py              ← LangGraph node functions
│   └── graph.py              ← graph builder
├── audio/                    ← input MP3s (git-ignored)
├── transcripts/              ← JSON transcript records (git-ignored)
├── pdf/                      ← generated bilingual PDFs (git-ignored)
├── subtitles/                ← SRT subtitles (git-ignored)
└── metadata/library.db       ← SQLite index (git-ignored)
```

## Quick Start

```bash
pip install -r requirements.txt

# CLI test (uses the bundled demo transcript in mock mode)
python run_pipeline.py --audio "audio/2026-10-07_RTHK_5min.mp3" --mock-asr

# Streamlit library app
streamlit run streamlit_app.py
```

### LLM Configuration

Set an OpenAI-compatible endpoint; otherwise the pipeline runs in **mock mode**
so the whole system can be tested offline:

```bash
export OPENAI_API_KEY=sk-...
export OPENAI_BASE_URL=https://api.openai.com/v1   # optional
export LLM_MODEL=gpt-4o-mini                        # optional
```

### Recording

The 🔴 Record tab captures the station's digital stream directly with ffmpeg —
no microphone, so there is no room noise. Presets include RTHK Radio 1–5; any
stream URL works. Output lands in `audio/YYYY-MM-DD_station_duration.mp3` at up
to 320 kbps.

## Standard Task Procedure

1. Record (🔴 tab) or place the MP3 in `audio/` named
   `YYYY-MM-DD_station_duration.mp3`.
2. Run `python run_pipeline.py --audio <file>` (omit `--mock-asr` for real
   recordings).
3. Review ASR errors (proper names, opera titles); fix the transcript JSON.
4. Add any new sentences to `_SENTENCE_TRANSLATIONS` and new words to
   `LEXICON` in `app/llm.py`.
5. Regenerate without re-running ASR: `python regen_outputs.py --all`.
6. Verify the PDF and set review status in the 📚 Library tab.

## Output Format Rules

Each segment in the PDF always includes all five parts: timestamp, Cantonese,
Jyutping, real English translation, and up to 4 vocabulary entries. An
aggregated deduplicated vocabulary section appears at the bottom of every PDF.

## Quality Controls

- Never overwrite original MP3s.
- Keep timestamps for every segment.
- Mark uncertain words, don't silently guess.
- Dictionary-based Jyutping verification (not pure LLM guessing).
- Review status: `unreviewed` / `partially_reviewed` / `verified`.

## Roadmap

1. 5–10 min daily prototype on one station (current stage).
2. Real Cantonese ASR integration (faster-whisper / Cantonese.ai API).
3. Speaker diarisation for phone-in programmes.
4. Vocabulary extraction + flashcards + RAG over the library.
5. Scheduled recording (cron / Android recorder + auto-upload).

See [`master.md`](master.md) for the full specification.
