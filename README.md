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
calls go through **LangChain** so providers are pluggable (xAI/Grok,
OpenAI-compatible API, local LLM, or a built-in mock for offline testing).

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
│   ├── config.py             ← paths / env settings (xAI, ffmpeg)
│   ├── state.py              ← LangGraph state schema
│   ├── asr.py                ← ASR providers (mock / faster-whisper)
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

**1. Install ffmpeg** (system dependency — required for recording and real ASR):

```powershell
# Windows
winget install Gyan.FFmpeg
```

```bash
# macOS
brew install ffmpeg
# Debian/Ubuntu
sudo apt install ffmpeg
```

> Reopen your terminal afterwards so ffmpeg is on `PATH`. If you cannot add it
> to `PATH`, set `FFMPEG_BINARY` to the full path of `ffmpeg.exe`.

**2. Install the Python dependencies:**

```bash
pip install -r requirements.txt
```

**3. Configure your LLM** (see [LLM Configuration](#llm-configuration)) —
otherwise the app runs in mock mode with rough-gloss translations.

**4. Run:**

```bash
# CLI test (uses the bundled demo transcript in mock ASR mode)
python run_pipeline.py --audio "audio/2026-10-07_RTHK_5min.mp3" --mock-asr

# Streamlit library app
streamlit run streamlit_app.py
```

## LLM Configuration

Any OpenAI-compatible endpoint works. Copy `.env.example` → `.env` (used by the
CLI) and/or `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml`
(used by the Streamlit app), then fill in your key. Both real files are
git-ignored.

Example for **xAI / Grok**:

```
OPENAI_BASE_URL=https://api.x.ai/v1
OPENAI_API_KEY=xai-...
LLM_MODEL=grok-4.20-0309-non-reasoning
LLM_MAX_WORKERS=4        # parallel LLM requests per stage
```

Other providers (OpenAI, OpenRouter, Groq, DeepSeek, Ollama, LM Studio) just
change the base URL and model. A key starting with `xai-` auto-selects the xAI
endpoint. Prefer a **non-reasoning** model — reasoning models are much slower
for this workload.

Without a key the pipeline runs in **mock mode** (rough-gloss translations, not
real English); the UI shows a yellow warning and the PDF prints a mock-mode
note.

### Radio Time Table

The 🗓️ **Radio Time Table** tab shows today's RTHK schedule for Radio 1–5,
fetched live from the RTHK schedule page (cached 30 min). Each channel has an
🔴 **On air now** marker; **talk programmes** (news, discussion, interview,
speech, chit-chat) are **green + bold**, while music is greyed out.

### Recording

The 🔴 Record tab captures the station's digital stream directly with ffmpeg —
no microphone, so there is no room noise. Presets include RTHK Radio 1–5; any
stream URL works. Output lands in `audio/YYYY-MM-DD_station_duration.mp3` at up
to 320 kbps.

### Processing

The ⚙️ Process recording tab lists every MP3 in `audio/` (newest first).

- **Clean audio first** — removes background music by isolating the vocal stem
  with **Demucs** (ffmpeg denoise fallback). Great for noisy/musical sources;
  slower, and the original file is never modified.
- **LLM quality review** — at the end of the run the LLM re-checks the
  transcript for accuracy (characters, Jyutping, English) and reports a score
  with flagged segments. It annotates only, never rewrites.

### VocabBank

The 🗂️ **VocabBank** tab pools vocabulary from every processed session:

- **Browse by session** — pick a recording from a dropdown and see its words
  (word / Jyutping / meaning / context), with CSV export.
- **Quick quiz** — Jyutping-only (no Chinese characters). 6–10 questions mixing
  *Jyutping → meaning* and *meaning → Jyutping*, at ~70% reviewed + ~30% new,
  one idea per question, plausible distractors. Immediate feedback includes the
  correct answer, an **audio replay** of the phrase, and the word in context.
  A 100/100 unlocks more unseen words.
- **Quiz history** — all attempts and scores.

Progress is stored locally in `metadata/` (git-ignored).

## Standard Task Procedure

1. Record (🔴 tab) or place the MP3 in `audio/` named
   `YYYY-MM-DD_station_duration.mp3`.
2. Run `python run_pipeline.py --audio <file>` (leave the mock-ASR box OFF for
   real recordings).
3. Review ASR errors (proper names, opera titles); fix the transcript JSON.
4. Regenerate without re-running ASR: `python regen_outputs.py --all`.
5. Verify the PDF and set review status in the 📚 Library tab.

## Output Format Rules

The PDF groups sentences into blocks of **3–6**, split on a topic change or
pause. Each block prints all its **Cantonese** lines, then all its **Jyutping**
lines, then all its **English** lines (numbered so the three sections line up).
A deduplicated **vocabulary table** (Word | Jyutping | Meaning) closes the
document.

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
