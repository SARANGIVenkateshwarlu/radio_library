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
│  load_audio → cleanup_audio → transcribe → correct →         │
│  jyutping → translate → segment_blocks → review_quality →    │
│  generate_pdf → save_to_library                              │
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
│   ├── cleanup.py            ← Demucs vocal isolation (+ ffmpeg fallback)
│   ├── audio_util.py         ← pitch-preserving playback speed
│   ├── llm.py                ← LangChain LLM factory (+ mock fallback)
│   ├── jyutping_tool.py      ← pycantonese wrapper + fallback dictionary
│   ├── jyutping_validate.py  ← LSHK Jyutping validator (no LLM)
│   ├── grouping.py           ← topic/pause segmentation into 3–6 blocks
│   ├── pdf_gen.py            ← bilingual PDF generator (reportlab)
│   ├── library.py            ← SQLite metadata store
│   ├── vocab.py              ← VocabBank: word banks + quiz builder
│   ├── schedule.py           ← RTHK 1–5 daily timetable
│   ├── phrases.py            ← phrase bank + shadowing helpers
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

### Local LLM with Ollama

You already run Ollama — point the app at it (no cloud key needed):

```bash
ollama pull qwen2.5:7b        # strong Chinese↔English; use a smaller/3b on low RAM
```
```
# .env / .streamlit/secrets.toml
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=ollama
LLM_MODEL=qwen2.5:7b
LLM_MAX_WORKERS=1
```

> **CPU-only caveat:** local LLMs are much slower than cloud. Big/reasoning
> models are unusable here — on a CPU-only box `glm-4.7-flash` took ~130 s per
> call and some quants (`qwen2.5:7b`) crash Ollama. Prefer a small model; if
> Ollama is unstable/slow on your hardware, use a cloud LLM instead.

## Cantonese ASR (local Whisper large-v3-turbo)

The app uses Whisper for transcription. For Cantonese, use a **large-v3-turbo
Cantonese** model (e.g.
[`wingskh/whisper-large-v3-turbo-cantonese`](https://huggingface.co/wingskh/whisper-large-v3-turbo-cantonese))
— much better than `base`/`small` and faster than large-v3.

### Option A — faster-whisper (recommended: fast CPU/GPU inference)

Convert the model to CTranslate2 once, then point the app at it:

```bash
pip install transformers ctranslate2 torch
ct2-transformers-converter \
  --model wingskh/whisper-large-v3-turbo-cantonese \
  --output_dir models/whisper-large-v3-turbo-cantonese-ct2 \
  --copy_files tokenizer.json preprocessor_config.json generation_config.json \
  --quantization int8
```
```
# .env
WHISPER_BACKEND=faster-whisper
WHISPER_MODEL=models/whisper-large-v3-turbo-cantonese-ct2
WHISPER_COMPUTE=int8          # use float16 with WHISPER_DEVICE=cuda on a GPU
WHISPER_LANGUAGE=yue
```

### Option B — transformers (no conversion, slower)

```bash
pip install transformers torch accelerate
```
```
WHISPER_BACKEND=transformers
WHISPER_MODEL=wingskh/whisper-large-v3-turbo-cantonese
WHISPER_LANGUAGE=yue
```

The model downloads on first run. (Ollama is for the LLM; Whisper runs through
faster-whisper/transformers, not Ollama.)

> **Windows download tips:** use `hf_transfer` for much faster downloads
> (`pip install hf_transfer`, `HF_HUB_ENABLE_HF_TRANSFER=1`). If you see
> `WinError 1314` (symlink privilege), download into a real folder instead —
> `huggingface_hub.snapshot_download("deepdml/faster-whisper-large-v3-turbo-ct2",
> local_dir="models/whisper-large-v3-turbo-ct2")` — or set
> `HF_HUB_DISABLE_SYMLINKS=1`.

### Choosing a Cantonese model

| Model | Size | Speed | Notes |
|-------|------|-------|-------|
| `wingskh/whisper-large-v3-turbo-cantonese` | 808M | fast | **Recommended** — turbo, lower cost |
| `khleeloo/whisper-large-v3-cantonese` | 1.54B | slower | Higher accuracy, but **gated** and ~6 GB |

Both are transformers-format, so use **Option A** (convert to CTranslate2) or
**Option B** (transformers backend). The `khleeloo` model is **gated**, so
authenticate first:

```bash
pip install huggingface_hub
huggingface-cli login          # paste a READ-role token after accepting the license
# or set HF_TOKEN=hf_... in your environment / .env
```

Then either convert it (`WHISPER_MODEL=khleeloo/whisper-large-v3-cantonese` for
the transformers backend, or a CTranslate2 output dir for faster-whisper). For a
GPU, use `WHISPER_COMPUTE=float16` and `WHISPER_DEVICE=cuda`.

### Best accuracy **and** speed

The CTranslate2 backend + **batched inference** is how you get both. Pick by
hardware:

| Hardware | Model | Settings | Result |
|----------|-------|----------|--------|
| **NVIDIA GPU** | `khleeloo/whisper-large-v3-cantonese` → CTranslate2 | `WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE=float16`, `WHISPER_BATCH_SIZE=16`, `WHISPER_BEAM=5` | best accuracy, very fast |
| **CPU only** | `wingskh/whisper-large-v3-turbo-cantonese` → CTranslate2 | `WHISPER_DEVICE=cpu`, `WHISPER_COMPUTE=int8`, `WHISPER_BATCH_SIZE=8`, `WHISPER_BEAM=5` | fast + good accuracy |
| **Max accuracy, any HW** | turbo CTranslate2 | as above, then rely on the LLM quality-review pass | turbo speed, refined output |

```env
WHISPER_BATCH_SIZE=8     # raise on GPU (16-32), lower on low RAM
WHISPER_BEAM=5           # 1-2 = faster, 5 = more accurate
```

Notes: batched inference (VAD-chunked) is the biggest single speed-up; `int8`
on CPU is ~2× faster than fp32 with minimal loss; `float16` on GPU is both fast
**and** accurate. The LLM refinement pass (`review_quality`) then fixes
low-confidence segments on top of the ASR. Large-v3 on CPU (no batching) is the
only genuinely slow combination — avoid it.

### ASR guidelines for Cantonese

- **Language = `yue`** (`WHISPER_LANGUAGE=yue`). The `yue` token needs the
  **large-v3 family** — with `base`/`small` the app falls back to auto-detect.
- **Initial prompt** in Traditional Chinese/Cantonese (`WHISPER_INITIAL_PROMPT`)
  biases output toward Cantonese characters.
- **`condition_on_previous_text=False`** (set in the code) avoids repetition
  loops on radio audio.
- **VAD on** + `temperature` fallback `[0,.2,.4,.6,.8,1]` + `beam_size=5` are
  the defaults for robustness on noisy music-heavy streams.
- Jyutping is **never** produced by the ASR/LLM — it comes from the
  dictionary/validator (`app/jyutping_tool.py`, `app/jyutping_validate.py`).
- Preprocess noisy/musical recordings with the **Clean audio (Demucs)** option
  before ASR.

### Radio Time Table

The 🗓️ **Radio Time Table** tab shows today's RTHK schedule for Radio 1–5,
fetched live from the RTHK schedule page (cached 30 min). Same format on every
channel — `00:00-06:00 · Night Music 長夜細聽 (music)`: the **current**
programme is **red + bold**, **talk** (news, discussion, interview, speech,
chit-chat) is **green + bold**, and **music** is greyed out and tagged
`(music)` so it's easy to skip.

### Recording

The 🔴 Record tab captures the station's digital stream directly with ffmpeg —
no microphone, so there is no room noise. Presets include RTHK Radio 1–5 and
**Talk Only** (www.talkonly.net); any
stream URL works. Output lands in `audio/YYYY-MM-DD_station_duration.mp3` at up
to 320 kbps. A **stream buffer** slider (default 12 s) keeps input buffered,
auto-reconnects and gap-fills the audio timeline so brief stream drops don't
break a continuous recording.

### Processing

The ⚙️ Process recording tab has two sub-tabs: **📻 Radio recordings** (pick any
MP3 in `audio/`, newest first) and **⬆️ Custom MP3** — upload a file from
YouTube, a podcast, or your phone. Custom MP3s are saved to `audio/` with the
standard filename (duration auto-detected) and then run the **same full
pipeline** as radio recordings.

- **Clean audio first** — removes background music by isolating the vocal stem
  with **Demucs** (ffmpeg denoise fallback). Great for noisy/musical sources;
  slower, and the original file is never modified.
- **LLM quality review + refine** — at the end of the run the LLM re-checks
  the transcript and reports an **English** accuracy score, summary and issues.
  If it scores below the target it re-translates the flagged segments and
  reviews again, keeping the **best-scoring** version for the JSON/PDF
  (`QREVIEW_TARGET`, `QREVIEW_MAX_ATTEMPTS`).

### VocabBank

The 🗂️ **VocabBank** tab pools vocabulary from every processed session:

- **Browse by session** — pick a recording from a dropdown and see its words
  (word / Jyutping / meaning / context), each with **three dictionary links** to
  check meaning, Jyutping and examples: **words.hk**, **jyutdictionary.com** and
  **cantowords.com**; CSV export.
- **Quick quiz** — Jyutping-only (no Chinese characters). 6–10 questions mixing
  *Jyutping → meaning* and *meaning → Jyutping*, at ~70% reviewed + ~30% new,
  one idea per question, plausible distractors. Immediate feedback includes the
  correct answer, an **audio replay** of the phrase, and the word in context.
  A 100/100 unlocks more unseen words.
- **Quiz history** — all attempts and scores.

Progress is stored locally in `metadata/` (git-ignored).

### Library

The 📚 **Library** tab lists saved recordings. Each one expands to the grouped
transcript plus a **🔊 playback control with speed settings** (0.5x / 0.75x /
1x / 1.5x / 2x — pitch-preserving, cached), a PDF download, and review-status
editing.

### Pronunciations

The 🗣️ **Pronunciations** tab has two parts:

- **📇 Phrase bank** — a personal card bank (Jyutping, English, audio, topic),
  addable manually or auto-filled from a processed recording; export to
  **Anki/CSV**; tracks **new cards/week** (target 35–50) and a **review streak**
  (days with ≥10 reviews, target 6–7/week).
- **🎧 Shadowing studio** — a play station for every MP3 plus sentence
  shadowing: play a sentence clip at 0.5–2x, **record yourself**, and compare
  side by side.

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
pause. Each block prints the **Cantonese** lines, then **Jyutping and English
side-by-side in one table** (column 1 Jyutping, column 2 English, one row per
sentence) so the two are easy to compare while saving paper. A deduplicated
**vocabulary table** (Word | Jyutping | Meaning) closes the document.

## Quality Controls

- Never overwrite original MP3s.
- Keep timestamps for every segment.
- Mark uncertain words, don't silently guess.
- Dictionary-based Jyutping verification (not pure LLM guessing).
- Review status: `unreviewed` / `partially_reviewed` / `verified`.

## LLM design guideline alignment

The project follows the recommended staged, structured-output design:

- **HK Cantonese pinned** — the system prompt targets modern spoken Hong Kong
  Cantonese and forbids rewriting into Mandarin/written Chinese; particles,
  fillers and code-switching are preserved.
- **Staged pipeline** — ASR (faster-whisper) and validation are separate from
  the LLM's correction/translation layer; the LLM never does acoustic
  recognition or tone decisions.
- **Verbatim vs normalized** — each segment keeps `verbatim_transcript` and
  `normalized_cantonese` separately.
- **Programmatic Jyutping validation** — `app/jyutping_validate.py` checks every
  syllable against an LSHK onset+final table, requires tone numbers 1–6, and
  checks character/syllable alignment (no LLM self-checks).
- **Uncertainty fields** — per-segment `confidence`
  (audio/transcription/jyutping/translation), `uncertain_tokens`,
  `alternative_readings`, `needs_human_review` and `review_reason`, plus an
  English `quality_review`; flagged segments show a ⚠ in the app and PDF.
- **Quality tuning** — the reviewer is strict-but-fair (ignores legitimate
  dialectal variant readings; only flags genuinely invalid Jyutping), and
  translation is **context-aware** (neighboring sentences included) so radio
  fragments read naturally. Curated `OVERRIDES` fill pycantonese gaps.

See [`master.md`](master.md) §12 for the full mapping.

## Roadmap

1. 5–10 min daily prototype on one station (current stage).
2. Real Cantonese ASR integration (faster-whisper / Cantonese.ai API).
3. Speaker diarisation for phone-in programmes.
4. Vocabulary extraction + flashcards + RAG over the library.
5. Scheduled recording (cron / Android recorder + auto-upload).

See [`master.md`](master.md) for the full specification.
