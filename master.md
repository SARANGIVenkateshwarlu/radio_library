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
│   ├── asr.py                ← ASR providers (mock / faster-whisper + confidence)
│   ├── cleanup.py            ← Demucs vocal isolation (+ ffmpeg fallback)
│   ├── audio_util.py         ← pitch-preserving playback speed (atempo)
│   ├── llm.py                ← LangChain LLM factory (+ mock fallback, prompts)
│   ├── jyutping_tool.py      ← pycantonese wrapper + fallback dictionary
│   ├── jyutping_validate.py  ← LSHK syllable/tone/alignment validator (no LLM)
│   ├── grouping.py           ← topic/pause segmentation (3–6 blocks)
│   ├── pdf_gen.py            ← bilingual PDF generator (reportlab)
│   ├── library.py            ← SQLite metadata store
│   ├── vocab.py              ← VocabBank word bank + quiz builder
│   ├── schedule.py           ← RTHK 1–5 daily timetable
│   ├── phrases.py            ← phrase bank + shadowing helpers
│   ├── cantonese_teacher.py  ← photo → Cantonese worksheet (agent wrapper)
│   ├── cantonese_pdf.py      ← worksheet PDF renderer (CantoneseTeacher style)
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
| `translate`   | corrected text   | English translation (meaning) | LangChain LLM chain           |
| `validate_output` | all text     | confidence + review flags     | deterministic QC (no LLM)     |
| `segment_blocks` | segments      | 3–6 sentence blocks           | LLM topic / pause grouping    |
| `review_quality` | all text      | English QA + refine to best   | LangChain LLM chain           |
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
  "audio_quality": "good | noisy | music | overlapping_speech | unknown",
  "cleanup_method": "demucs | ffmpeg | off",
  "translation_source": "llm | mock",
  "segments": [
    {
      "start": 0.0, "end": 4.2,
      "verbatim_transcript": "...",      // what was heard (raw ASR, unchanged)
      "normalized_cantonese": "...",     // readable HK Cantonese (== corrected)
      "cantonese": "...",                // alias of verbatim_transcript
      "corrected": "...",                // alias of normalized_cantonese
      "jyutping": "nei5 hou2",
      "english": "...",
      "vocabulary": [{"word": "...", "jyutping": "...", "meaning": "..."}],
      "confidence": {"audio": 0.0, "transcription": 0.0, "jyutping": 0.0, "translation": 0.0},
      "uncertain_tokens": [],
      "alternative_readings": [],
      "needs_human_review": false,
      "review_reason": null,
      "audio_quality": "good",
      "block": 0
    }
  ],
  "quality_review": {"status": "ok", "accuracy_score": 90, "summary": "...", "issues": [], "flagged_segments": []},
  "review_status": "unreviewed"
}
```

## 5a. Output Format Rules (mandatory, apply to every recording)

**PDF / display layout — grouped blocks of 3–6 sentences.**

Segments are grouped into blocks split on a **topic change or a pause**
(LLM-proposed boundaries when an LLM is configured, otherwise audio gaps;
sizes clamped to `BLOCK_MIN`..`BLOCK_MAX`, default 3–6). Each block prints the
Cantonese sentences, then **Jyutping and English side-by-side in one table**
(one row per sentence — column 1 Jyutping, column 2 English) to save space and
make the two lines easy to compare:

```
Block 1   [hh:mm:ss – hh:mm:ss]

Cantonese:
1. <corrected Cantonese>
2. ...

Jyutping             | English
1. <jyutping>        | 1. <real English translation — never a placeholder>
2. ...               | 2. ...

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
RTHK Radio 1–5 (`https://stm1.rthk.hk/radio5`, etc.) and **Talk Only**
(`https://live.talkonly.net:8443/talkonly.mp3`, www.talkonly.net); any stream URL
works.
The **Start recording** / **Stop** buttons are enlarged and full-width for easy
tapping on a touch screen.

- Durations: 5 min / 10 min / 30 min / 1 h / custom.
- Live ▶️ Play / ⏹️ Stop listening in the browser alongside recording.
- Quality: up to **320 kbps MP3** (libmp3lame's maximum — standard MP3 has no
  360 kbps mode; 320k is the highest available setting).
- Output lands in `audio/YYYY-MM-DD_station_duration.mp3`, ready for the
  ⚙️ Process recording tab.
- **Stream buffer / disconnect tolerance** (slider, default **12 s**, 0–30 s):
  ffmpeg keeps the input buffered, auto-reconnects (`reconnect` +
  `reconnect_at_eof`) and gap-fills the audio timeline (`aresample=async=1`)
  so brief live-stream drops don't break a continuous recording. Applies to
  every station (RTHK 1–5, Talk Only).

### Processing (⚙️ Process recording tab)

Two sub-tabs:

- **📻 Radio recordings** — pick a recording from a dropdown of every MP3 in
  `audio/` (newest on top), leave "mock ASR" off, and run the pipeline. Results
  are saved to the library and shown inline.
- **⬆️ Custom MP3** — upload an MP3 from **YouTube, a podcast, your phone or any
  local file**. It is saved into `audio/` with the standard naming convention
  (`date_source_duration.mp3`, duration probed with ffprobe/ffmpeg), so it then
  runs the **exact same A-to-Z pipeline** as a radio file: cleanup → ASR →
  Jyutping → translation → validation → LLM review → PDF → library. Optionally
  tag it with a source name used in the file name.

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
  plus **three dictionary links** per word (words.hk, jyutdictionary.com,
  cantowords.com) for meaning, Jyutping and examples. CSV export for one
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

### Pronunciations (🗣️ tab)

Two sub-tabs. Data is local (`metadata/phrase_bank.json`,
`metadata/phrase_reviews.json`, `metadata/recordings/`; all git-ignored).

- **📇 Phrase bank** — a personal card bank with fields **Jyutping, English,
  audio (link or file), topic tag**. Add cards manually, or **auto-fill from a
  processed recording** (picks a sentence and saves its audio clip). Export an
  **Anki/CSV** (columns: Jyutping, English, Audio, Topic). Progress metrics:
  total cards, **new cards this week** (target 35–50), **review streak**
  (consecutive days with ≥10 reviews) and **days on target this week**
  (target 6–7); log reviews daily.
- **🎧 Shadowing studio** — a **play station** for every MP3 in `audio/` with
  speed control, plus **sentence shadowing**: pick a recording and a sentence,
  play the clip at your chosen speed (listen → pause → repeat, matching tone
  contour and speed), **record yourself** with the microphone, and compare the
  original clip with your recording side by side. Recordings are saved for
  later review.

### Cantonese Teacher (🎓 tab)

Integration of the standalone `CantoneseTeacher` project (kept under
`CantoneseTeacher/cantonese_teacher_agent/`, sources tracked, generated
output/assets git-ignored):

- **Pipeline A (photo worksheet):** snap 📷 or upload 🖼️ a Hong Kong scene →
  vision description → teacher LLM → validated lesson JSON → **colour-coded A4
  PDF** (10 sentences · Q&A · vocabulary table), word-colour-matched across
  Cantonese/Jyutping/English. Live generation uses the configured endpoint
  (`CANTONESE_TEACHER_MODEL`); a built-in demo lesson is the offline fallback.
- Follows the locked `RULES.md` layout (title → image → ten sentences → Q&A →
  vocabulary; fonts 21/15/16/13/11.5; footer `Page 第 N 頁`).
- Implementation: `app/cantonese_teacher.py` (vision + lesson JSON + validation)
  and `app/cantonese_pdf.py` (renderer; falls back to reportlab's built-in
  STSong-Light CID font so it runs on Windows with no TrueType CJK fonts).

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
| Streamlit app (7 tabs: Radio Time Table, record, process, library, VocabBank, Pronunciations, Cantonese Teacher) | ✅ no exceptions; timetable, play toggle, record start/stop, library list, quizzes, phrase bank/shadowing, and photo→worksheet PDF working |
| Live RTHK stream from sandbox | ⚠️ `stm1.rthk.hk` unreachable from this sandbox network; verified with local stream instead — works on a normal network |

## 11. Roadmap

1. 5–10 min daily prototype on one station (current stage).
2. Real Cantonese ASR integration (e.g. Cantonese.ai API / whisper-yue).
3. Speaker diarisation for phone-in programmes.
4. Vocabulary extraction + flashcards + RAG over the library.
5. Scheduled recording (cron / Android recorder + auto-upload).

## 12. LLM design guideline alignment

The pipeline follows the staged, structured-output design (no single mega-prompt):

| Guideline | Implementation |
|-----------|----------------|
| 1. Define HK Cantonese explicitly | `SYSTEM_PROMPT` in `app/llm.py` pins *modern spoken Hong Kong Cantonese*, preserves sentence-final particles (喎 喇 啫 㗎 吖 啦 嘅 咩 囉), fillers, code-switching and names, and forbids rewriting into Mandarin/written Chinese. |
| 2. Separate ASR from interpretation | Distinct nodes: `cleanup_audio` → `transcribe` → `correct` → `jyutping` → `translate` → `validate_output` → `review_quality` (voice-activity/noise via Demucs/ffmpeg + VAD; ASR is faster-whisper, not the LLM). |
| 3. Preserve the original spoken form | Every segment keeps `verbatim_transcript` (untouched ASR) alongside `normalized_cantonese` (readable HK Cantonese). |
| 4. Jyutping only, strict validation | LSHK Jyutping from pycantonese, then `app/jyutping_validate.py` checks every syllable against an onset+final table, requires a tone 1–6, and verifies character/syllable alignment — programmatically, not by the LLM. |
| 5. Tones are essential | The validator flags missing/invalid tones; `confidence.jyutping` drops and the segment is flagged for review. |
| 6. Multiple/colloquial readings | `alternative_readings` field per segment (populated when a reading is genuinely variable; empty otherwise). |
| 7. Spoken vs written layers | `verbatim_transcript` + `normalized_cantonese` + Jyutping + English are stored separately; a formal-Chinese equivalent is optional and never replaces the Cantonese. |
| 8. Translate meaning, not characters | Translation prompt asks for sentence-level meaning, forbids inventing gender/tense/politeness; vocabulary offers per-word meaning. |
| 9. Timestamps + aligned segments | Timestamped segments (start/end) grouped into phrase-level blocks; Jyutping is character-aligned. |
| 10. Uncertainty / evidence / validation | Per-segment `confidence` (audio/transcription/jyutping/translation), `audio_quality`, `uncertain_tokens`, `needs_human_review`, `review_reason`; recording-level `quality_review`. |

Deterministic QC (guideline 10 + the "practical quality-control pipeline"):
validate JSON, check timestamps, validate Jyutping syllables/tones/alignment, and
set review flags — all in `validate_output` (no LLM). The LLM reviewer runs a
second pass and refines flagged segments (`review_quality`, English report). The
LLM is never the component responsible for acoustic recognition or tone
accuracy — that stays with the Cantonese ASR and the dictionary/validator.

## 13. Local Cantonese ASR (Whisper large-v3-turbo) & guidelines

Transcription uses Whisper. For Cantonese, use a **large-v3-turbo Cantonese**
model (e.g. `wingskh/whisper-large-v3-turbo-cantonese`) — far better than
`base`/`small`, faster and cheaper than large-v3. Two backends
(`WHISPER_BACKEND`):

**A. faster-whisper (recommended).** Convert the HF model to CTranslate2 once:

```bash
pip install transformers ctranslate2 torch
ct2-transformers-converter \
  --model wingskh/whisper-large-v3-turbo-cantonese \
  --output_dir models/whisper-large-v3-turbo-cantonese-ct2 \
  --copy_files tokenizer.json preprocessor_config.json generation_config.json \
  --quantization int8
```

```env
WHISPER_BACKEND=faster-whisper
WHISPER_MODEL=models/whisper-large-v3-turbo-cantonese-ct2
WHISPER_COMPUTE=int8      # float16 + WHISPER_DEVICE=cuda on a GPU
WHISPER_LANGUAGE=yue
```

**B. transformers (no conversion, slower).** `pip install transformers torch
accelerate`, then `WHISPER_BACKEND=transformers` and
`WHISPER_MODEL=wingskh/whisper-large-v3-turbo-cantonese` (downloads on first run).

**Alternative model:** `khleeloo/whisper-large-v3-cantonese` — full large-v3
(1.54B, ~6 GB), higher accuracy but slower, and **gated** (accept the license on
HF and authenticate: `huggingface-cli login` or `HF_TOKEN`). Both models are
transformers-format, so use backend A (convert) or B.

**LLM with Ollama (local, no key):** `ollama pull qwen2.5:14b`, then
`OPENAI_BASE_URL=http://localhost:11434/v1`, `OPENAI_API_KEY=ollama`,
`LLM_MODEL=qwen2.5:14b`. Ollama runs the *LLM*; Whisper runs via
faster-whisper/transformers.

**Accuracy + speed.** CTranslate2 + **batched inference** gives both. Best
configs:

| Hardware | Model (CTranslate2) | Settings |
|----------|---------------------|----------|
| GPU | `khleeloo/whisper-large-v3-cantonese` | `WHISPER_DEVICE=cuda`, `WHISPER_COMPUTE=float16`, `WHISPER_BATCH_SIZE=16`, `WHISPER_BEAM=5` |
| CPU | `wingskh/whisper-large-v3-turbo-cantonese` | `WHISPER_DEVICE=cpu`, `WHISPER_COMPUTE=int8`, `WHISPER_BATCH_SIZE=8`, `WHISPER_BEAM=5` |

`WHISPER_BATCH_SIZE>1` enables `faster_whisper.BatchedInferencePipeline` (the
biggest single speed-up); `beam_size` trades speed for accuracy; `int8` (CPU) is
~2× faster than fp32; `float16` (GPU) is fast *and* accurate. The LLM
`review_quality` pass further improves accuracy on flagged segments.

**ASR guidelines**

- **`WHISPER_LANGUAGE=yue`** — the `yue` token requires the large-v3 family;
  smaller models fall back to auto-detect automatically.
- **`WHISPER_INITIAL_PROMPT`** in Traditional Chinese/Cantonese biases the
  output toward Cantonese characters (never leave it in Mandarin).
- **`condition_on_previous_text=False`**, **VAD on**, **temperature fallback**
  `[0,.2,.4,.6,.8,1]`, **`beam_size=5`** (all defaults in `app/asr.py`) for
  robustness on noisy, music-heavy radio.
- Preprocess noisy/musical audio with **Demucs** (`cleanup_audio`) first.
- Jyutping and tones are **never** produced by Whisper/LLM — they come from the
  dictionary + validator, per §12.

**Quality knobs (post-2026 tuning):** the reviewer is **strict-but-fair** — it
does not penalize legitimate dialectal variants or demand dictionary edits, and
only flags genuinely invalid Jyutping (missing tone / illegal syllable /
alignment), so the `accuracy_score` reflects real content quality. Translation
is **context-aware** (each sentence is translated with its neighbours) so radio
fragments and references resolve naturally. `OVERRIDES` in
`app/jyutping_tool.py` fills characters pycantonese misses. Typical score:
~92/100 for clean transcripts; hard call-in audio scores lower because of ASR
errors — the best lever there is a better Cantonese ASR + Demucs cleanup.

Config lives in `app/config.py` (`WHISPER_*`, `QREVIEW_*`); the provider factory
is `app/asr.py:get_asr`.
