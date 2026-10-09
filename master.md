# HK Radio Cantonese Learning Library — Master Document

## 1. Project Goal

Build a daily pipeline that turns Hong Kong FM radio recordings into a
personal Cantonese-learning library:

```
HK FM recording → MP3 archive → Cantonese transcription → Jyutping → English translation → PDF + searchable library
```

Recordings are for **personal study only**. Hong Kong copyright law protects
broadcasts — do not redistribute or reuse commercially.

## 2. Architecture

The pipeline is orchestrated with **LangGraph** (state machine) and all LLM
calls go through **LangChain** so providers are pluggable (OpenAI-compatible
API, local LLM, or a built-in mock for offline testing).

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

## 3. Repository Layout

```
radio_library/
├── master.md                 ← this file
├── requirements.txt
├── run_pipeline.py           ← CLI entry point (full pipeline incl. ASR)
├── regen_outputs.py          ← re-run text stages from saved JSON (no ASR)
├── streamlit_app.py          ← Streamlit library UI
├── app/
│   ├── __init__.py
│   ├── config.py             ← paths / env settings
│   ├── state.py              ← LangGraph state schema
│   ├── asr.py                ← ASR providers (mock / pluggable)
│   ├── cleanup.py            ← Demucs vocal isolation (+ ffmpeg fallback)
│   ├── llm.py                ← LangChain LLM factory (+ mock fallback)
│   ├── jyutping_tool.py      ← pycantonese wrapper + fallback dictionary
│   ├── grouping.py           ← topic/pause segmentation (3–6 blocks)
│   ├── pdf_gen.py            ← bilingual PDF generator (reportlab)
│   ├── library.py            ← SQLite metadata store
│   ├── vocab.py              ← VocabBank word bank + quiz builder
│   ├── schedule.py           ← RTHK 1–5 daily timetable
│   ├── nodes.py              ← LangGraph node functions
│   └── graph.py              ← graph builder
├── audio/                    ← input MP3s (YYYY-MM-DD_station_duration.mp3)
├── transcripts/              ← JSON transcript records
├── pdf/                      ← generated bilingual PDFs
├── subtitles/                ← SRT subtitles
└── metadata/library.db       ← SQLite index
```

## 4. Pipeline Nodes (LangGraph)

| Node          | Input            | Output                        | Implementation                |
|---------------|------------------|-------------------------------|-------------------------------|
| `load_audio`  | audio_path       | recording metadata            | filename convention parsing   |
| `cleanup_audio` | audio file     | voice-isolated audio          | Demucs (ffmpeg denoise fallback) |
| `transcribe`  | audio file       | Cantonese segments + ts       | ASR provider (mock/pluggable) |
| `correct`     | raw transcript   | corrected Cantonese           | LangChain LLM chain           |
| `jyutping`    | corrected text   | Jyutping per sentence         | pycantonese / dictionary      |
| `translate`   | corrected text   | English translation           | LangChain LLM chain           |
| `segment_blocks` | segments      | 3–6 sentence blocks           | LLM topic / pause grouping    |
| `review_quality` | all text      | QA report + flags             | LangChain LLM chain           |
| `generate_pdf`| all above        | PDF path                      | reportlab (CID font)          |
| `save_to_library` | all above    | DB row + JSON + SRT           | SQLite                        |

## 5. Recording Metadata (JSON)

```json
{
  "recording_id": "2026-10-07-rthk-001",
  "station": "RTHK",
  "program": "Morning News",
  "recorded_at": "2026-10-07T08:00:00+08:00",
  "duration_seconds": 1800,
  "audio_file": "audio/2026-10-07_RTHK_30min.mp3",
  "segments": [
    {"start": 0.0, "end": 4.2, "cantonese": "...", "jyutping": "...", "english": "...",
     "vocabulary": [{"word": "...", "jyutping": "...", "meaning": "..."}]}
  ],
  "review_status": "unreviewed"
}
```

## 5a. Output Format Rules (mandatory, apply to every recording)

**PDF / display layout — grouped blocks of 3–6 sentences.**

Segments are grouped into blocks split on a **topic change or a pause**
(LLM-proposed boundaries when an LLM is configured, otherwise audio gaps;
sizes clamped to `BLOCK_MIN`..`BLOCK_MAX`, default 3–6). Each block prints all
its Cantonese lines, then all its Jyutping lines, then all its English lines:

```
Block 1   [hh:mm:ss – hh:mm:ss]

Cantonese:
1. <corrected Cantonese>
2. ...

Jyutping:
1. <jyutping>
2. ...

English:
1. <real English translation — never a placeholder>
2. ...

Block 2   [hh:mm:ss – hh:mm:ss]
...
```

**Plus, at the bottom of every PDF:** a deduplicated
`Vocabulary (全篇詞彙):` **table** (Word | Jyutping | Meaning) listing every
word across the recording.

**Translation rule:** English must always be real. Priority order:
1. An LLM is configured (`OPENAI_API_KEY` in `.env` / Streamlit secrets) →
   the LangChain LLM chain translates (prompted for natural meaning, not a
   word-for-word gloss).
2. Curated sentence table (`_SENTENCE_TRANSLATIONS` in `app/llm.py`) → exact,
   natural English. **Add every new recording's sentences here after review.**
3. Offline mock fallback → word-by-word gloss from `LEXICON`, marked
   `[rough gloss]`; sentences with no known words are marked
   `[no translation — configure an LLM for real English]`.

**Never** echo the Cantonese sentence as the English field — that makes the PDF
look as though the translation is missing. When no LLM is configured the PDF
prints a red **mock-mode** note and the record stores
`"translation_source": "mock"`, so unreviewed output is never mistaken for
real English.

**Vocabulary rule:** extracted from `LEXICON` (55+ curated Cantonese words with
Jyutping and meanings) or by the LLM when configured. Extend `LEXICON` whenever
a new word appears in a transcript.

**ASR rule:** real recordings use faster-whisper (`app/asr.py`,
`WHISPER_MODEL=base` default; use `small`/`medium` for better Cantonese
accuracy). Mock ASR is only for offline pipeline testing.

## 5b. Standard Task Procedure (do this every time)

**Prerequisite (once):** configure your LLM in `.env` and
`.streamlit/secrets.toml` (section 7). If you skip this, the run uses **mock
mode**: the record is stored with `"translation_source": "mock"` and the PDF
prints a mock-mode note — English will be a rough gloss, not a real translation.
Leave the "Use mock ASR" checkbox **OFF** for real recordings.

1. Record (🔴 tab) or place the MP3 in `audio/` named
   `YYYY-MM-DD_station_duration.mp3`.
2. Run `python run_pipeline.py --audio <file>` (omit `--mock-asr` for real
   recordings).
3. Review ASR errors (proper names, opera titles); fix the transcript JSON.
4. Add any new sentences to `_SENTENCE_TRANSLATIONS` and new words to
   `LEXICON` in `app/llm.py`.
5. Regenerate without re-running ASR:
   `python regen_outputs.py transcripts/<id>.json` (or `--all`).
6. Verify the PDF: blocks of 3–6 sentences, each block listing Cantonese then
   Jyutping then English, and the vocabulary table at the bottom.
7. Set review status in the 📚 Library tab: `partially_reviewed` → `verified`.

## 6. Filename Convention

```
YYYY-MM-DD_<station>_<duration>.mp3
e.g. 2026-10-07_RTHK_30min.mp3
```

## 7. LLM Configuration

Any OpenAI-compatible endpoint works (xAI/Grok, OpenAI, OpenRouter, Groq,
DeepSeek, Ollama, LM Studio…). Copy the templates and fill in your key:

- `.env.example` → `.env` — used by the CLI (`run_pipeline.py`,
  `regen_outputs.py`).
- `.streamlit/secrets.toml.example` → `.streamlit/secrets.toml` — used by the
  Streamlit app.

Both real files are git-ignored. Example for **xAI / Grok**:

```
OPENAI_BASE_URL=https://api.x.ai/v1
OPENAI_API_KEY=xai-...
LLM_MODEL=grok-4.20-0309-non-reasoning
LLM_MAX_WORKERS=4        # parallel LLM requests per stage
```

Resolution order: OS environment variables → `.env` → Streamlit secrets.
`XAI_API_KEY` / `XAI_BASE_URL` / `XAI_MODEL` are accepted as aliases, and a key
starting with `xai-` auto-selects the xAI endpoint even without the base URL.

Prefer a **non-reasoning** Grok model for speed (reasoning models are ~10x
slower on this workload). List what your key can use:

```bash
curl -s https://api.x.ai/v1/models -H "Authorization: Bearer $OPENAI_API_KEY"
```

Without a key the pipeline runs in **mock mode** (rough-gloss translations) for
offline testing; the Streamlit UI shows a yellow warning and the PDF prints a
mock-mode note. Mock output is not real translation — configure an LLM before
review.

## 8. Quick Start

```bash
pip install -r requirements.txt

# CLI test (uses the bundled demo transcript in mock mode)
python run_pipeline.py --audio "audio/2026-10-07_RTHK_5min.mp3" --mock-asr

# Streamlit library app
streamlit run streamlit_app.py
```

### Radio Time Table (🗓️ tab)

Today's RTHK schedule for the five FM channels (Radio 1–5), read live from the
RTHK schedule page (`app/schedule.py`, cached 30 min). One section per channel
with a **🔄 Refresh** button. Every row uses the same format:

```
00:00-06:00 · Night Music 長夜細聽 (music)
```

- **Red + bold** — the programme **currently on air** (plus an 🔴 On air now
  marker).
- **Green + bold** — talk (news, discussion, interview, speech, chit-chat):
  good listening practice.
- **Grey, suffixed `(music)`** — music programmes, so they are easy to skip.
  Classification is keyword-based (Chinese title + English slug), so
  music-heavy channels like Radio 4 correctly show little highlighting.

### Recording (🔴 Record radio tab)

Direct stream capture with ffmpeg — the station's digital stream is recorded
straight to disk, no microphone, so there is no room noise. Presets include
RTHK Radio 1–5 (`https://stm1.rthk.hk/radio5`, etc.); any stream URL works.
The **Start recording** / **Stop** buttons are enlarged and full-width for easy
tapping on a touch screen.

- Durations: 5 min / 10 min / 30 min / 1 h / custom.
- Live ▶️ Play / ⏹️ Stop listening in the browser alongside recording.
- Quality: up to **320 kbps MP3** (libmp3lame's maximum — standard MP3 has no
  360 kbps mode; 320k is the highest available setting).
- Output lands in `audio/YYYY-MM-DD_station_duration.mp3`, ready for the
  ⚙️ Process recording tab.
- Start/stop from the browser; ffmpeg auto-reconnects on stream drops.

### Processing (⚙️ Process recording tab)

Pick the recording from a dropdown of every MP3 in `audio/` (newest on top),
leave "mock ASR" off, and run the pipeline. Results are saved to the library
and shown inline.

- **Clean audio first** — isolates the vocal stem with **Demucs** (`htdemucs`)
  so background music is dropped before ASR; falls back to an ffmpeg
  denoise/normalise chain (`highpass`/`lowpass`/`afftdn`/`loudnorm`) if Demucs
  is unavailable. Cleaned audio is written to `metadata/cleaned/`; the original
  MP3 is never modified. Slower (Demucs ≈ 0.7× realtime on CPU).
- **LLM quality review + refine** — after processing, the LLM re-checks the
  whole transcript (Cantonese typos, Jyutping, English accuracy, omissions) and
  reports an **accuracy score, English summary and per-segment issues in
  English**. If the score is below `QREVIEW_TARGET` (default 90) it corrects the
  flagged segments and reviews again, up to `QREVIEW_MAX_ATTEMPTS` (default 2),
  keeping the **best-scoring** version — that is what gets written to the JSON
  and PDF. Flagged runs set `review_status` to `partially_reviewed`.

### VocabBank (🗂️ tab)

Vocabulary is pooled across every processed session (group = one recording),
read from the SQLite library and transcript JSON files. Sections:

- **Browse by session** — dropdown of groups (labelled by MP3 file name); a
  table of word / Jyutping / meaning / in-context for the selected session,
  plus a **words.hk** link per word (`https://words.hk/zidin/<word>`) to hear
  the pronunciation and practice with Cantonese examples. CSV export for one
  session or all.
- **Quick quiz** — **character-free**, Jyutping-only (the learner cannot read
  hanzi). Two mixed types: *Jyutping → meaning* and its reverse
  *meaning → Jyutping*. 6–10 questions, **~70% reviewed words + ~30% new**, one
  idea per question, plausibility-aware distractors (same session/topic first;
  similar-sounding Jyutping for the reverse type). Immediate feedback shows the
  correct answer, the **audio replay** (ffmpeg clip of the phrase) and the word
  in context. A perfect 100/100 automatically surfaces more unseen words.
- **Quiz history** — every attempt with score, correct/wrong counts and the
  words asked; running attempts, best and average scores.

Progress is stored locally under `metadata/` (`quiz_history.json`,
`vocab_stats.json`, both git-ignored).

### Library (📚 tab)

Saved recordings, each expandable to show the grouped transcript, a
**🔊 playback control with speed settings** (0.5x / 0.75x / 1x / 1.5x / 2x —
pitch-preserving ffmpeg `atempo`, cached under `metadata/speed/`), PDF download,
and review-status editing.

## 9. Quality Controls (from the source plan)

- Never overwrite original MP3s.
- Keep timestamps for every segment.
- Mark uncertain words, don't silently guess.
- Dictionary-based Jyutping verification (not pure LLM guessing).
- Review status: `unreviewed` / `partially_reviewed` / `verified`.
- Daily processing log; separate backups for audio and PDFs.
- Copyright / personal-use metadata stored with every record.

## 10. Test Log (2026-10-07)

| Test | Result |
|------|--------|
| Stream recorder → 60 s MP3 | ✅ `2026-10-07_rthk-radio-5_1min_2.mp3` — 60.03 s @ 320 kbps, no noise (direct stream) |
| LangGraph pipeline on recording | ✅ JSON + SRT + bilingual PDF generated, saved to SQLite |
| Streamlit app (5 tabs: Radio Time Table, record, process, library, VocabBank) | ✅ no exceptions; timetable, play toggle, record start/stop, library list, quizzes working |
| Live RTHK stream from sandbox | ⚠️ `stm1.rthk.hk` unreachable from this sandbox network; verified with local stream instead — works on a normal network |

## 11. Roadmap

1. 5–10 min daily prototype on one station (current stage).
2. Real Cantonese ASR integration (e.g. Cantonese.ai API / whisper-yue).
3. Speaker diarisation for phone-in programmes.
4. Vocabulary extraction + flashcards + RAG over the library.
5. Scheduled recording (cron / Android recorder + auto-upload).
