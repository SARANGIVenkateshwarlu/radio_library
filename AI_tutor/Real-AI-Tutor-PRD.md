# Real AI Tutor — Product Requirements Document (PRD)

**Product:** Real AI Tutor — English → Hong Kong Cantonese Speaking Coach
**Status:** MVP built (full-stack web app) · Version `b8bedaa`
**Sources consolidated:** original PDR (Perplexity export), market review (AI tutor_1), component architecture (AI tutor_2), Praktika-style blueprint (AI tutor_3)

---

## 1. Vision & positioning

A voice-first AI tutor that helps English speakers hold natural **Hong Kong Cantonese** conversations. Not a generic Chinese tutor with a Cantonese voice — Jyutping, tone correction, and colloquial usage are first-class features.

**Market fit (from AI tutor_1):** Cantonese is underserved; the closest competitor (Glottie) validates demand but lacks deep tone/Jyutping pedagogy. Retention risk is repetition — mitigated by scenario variety, personas, and spaced review.

**One-line loop:** Speak English → get a natural Cantonese version with audio + Jyutping → attempt it aloud → receive tone/pronunciation feedback → phrase auto-saves into spaced-repetition review.

## 2. Personas (product)

| User | Need | Success behavior |
|---|---|---|
| Beginner | Survive basic HK interactions | Orders food, asks directions, introduces self |
| Intermediate | Sound natural, use slang | Uses particles/idioms correctly |
| Busy professional | 5–10 min daily speaking habit | Completes daily plan + review queue |
| Heritage learner | Confident production | Fluency in family/social talk |

## 3. Tutor personas (Praktika pattern — implemented)

| Persona | Style | Use case |
|---|---|---|
| 阿Wing (Ah Wing) 🧑‍🎤 | Casual, playful, slang | Social, free talk |
| 陳太 (Mrs Chan) 👩‍🦱 | Patient, slow, praise-first | Beginners, drills |
| 霞姐 (Ha Jeh) 👩‍🍳 | Fast, witty, street Cantonese | Food/workplace slang |

Persona is chosen before each conversation and injected into the LLM system prompt; each persona opens with its own spoken intro.

## 4. Feature requirements & implementation status

### F1. Voice conversation ✅
- Mic capture with permission handling, interim transcript, silence-based auto-stop (VAD-lite)
- English / Cantonese / code-switch input modes
- Streaming-feel UX: interim transcripts, immediate TTS playback of tutor replies
- Try-Again button on every correction card (Praktika retry loop)

### F2. Cantonese output ✅
- Traditional Chinese + Jyutping (syllable-aligned ruby display) + English translation
- Playback at 1.0× / 0.75× / 0.5× (zh-HK voice)
- Persona-labelled replies; AI vs curriculum-coach provenance badge

### F3. Pronunciation & tone feedback ✅
- Cantonese ASR (browser `yue-HK`) → scoring service (LLM coach, deterministic heuristic fallback)
- **Subscores: pronunciation, fluency, completeness, rhythm** (Praktika dimensions) + tone-first issues with expected/heard Jyutping
- Score ring, per-syllable issue cards, retry-until-pass, attempt trend (e.g. 62 → 81)

### F4. Phrasebook & SRS ✅
- Auto-save from tutor turns (AI `saved_phrase`) + manual bookmark in drills
- SM-2 scheduler (ease factor, intervals, lapses), due-today queue, mastery (21d+ interval), retention metric

### F5. Scenario curriculum ✅ — 7 guided + free talk
Greetings · Cha chaan teng · MTR/taxi/directions · Shopping · Workplace · Social · Emergency — each with objectives, 8 target phrases, scripted roleplay, likely-mistake table, assessment phrases. **Free Talk** mode (unscripted, AI-driven).

### F6. Learner state & progress ✅
- Per-turn `learner_state_update` (fluency/accuracy/confidence 0–100 + new weak areas) from the LLM
- Dashboard: streak, speaking minutes, phrases saved/mastered, avg pronunciation, retention, per-scenario completion bars
- **Today's Plan** card (review → roleplay → drill)

## 5. AI system

### Architecture (voice loop)
```
mic → browser ASR (en-US / yue-HK) → tRPC → Lesson Agent (LLM, strict JSON)
    → tutor reply + Jyutping + correction + learner_state_update
    → zh-HK TTS playback · turn persisted to MySQL
Parallel: Pronunciation scorer (LLM + heuristic fallback) · SM-2 SRS engine
```

### Prompt pack (implemented server-side, `api/prompts.ts`)
1. **Lesson Agent** — persona block + PDR rules: colloquial HK Cantonese only, 1–2 sentence replies, max 1–2 corrections, Traditional Chinese + Jyutping, never invent vocabulary; strict JSON output (`cantonese_reply`, `jyutping`, `english_translation`, `correction`, `saved_phrase`, `learner_state_update`)
2. **Pronunciation coach** — 4 subscores, ≤3 issues, tone-first, honest under uncertainty
3. **Translator** — English → colloquial Cantonese with register notes
4. **Session summary** — strengths, priorities, next-scenario recommendation
5. **Scenario generator** — defined for future dynamic packs

### Degradation contract
AI unavailable (quota/transient/misconfigured) → **scripted curriculum coach** answers from the scenario pack; UI shows an honest banner. AI calls are billed to the site owner; no silent failures.

## 6. Data model (MySQL, implemented)

- `profiles` — device token, level, daily goal, streak, speaking seconds
- `phrases` — Cantonese/Jyutping/English, source, SM-2 state (interval, dueAt, easeFactor, reps, lapses, lastScore)
- `sessions` — scenario, mode, duration, turn count, overall score, summary JSON
- `turns` — user text/lang, tutor triple (chars/Jyutping/English), correction JSON, pronunciation score

## 7. Tech stack

| Layer | MVP (shipped) | Production path (Resources page) |
|---|---|---|
| Client | React 19 + Vite + Tailwind, browser Web Speech API | React Native/Expo |
| English ASR | Browser (en-US) | Whisper / faster-whisper / whisper-large-v3-turbo |
| Cantonese ASR | Browser (yue-HK) | **SenseVoice / SenseVoiceSmall**, Cantonese Whisper fine-tunes, cantonese.ai STT |
| Tutor LLM | Kimi gateway (structured JSON) | Same pattern, any OpenAI-compatible model |
| Cantonese TTS | Browser zh-HK | **CosyVoice 2** (streaming), **canto-tts-nano** (Jyutping tokens), edge-tts zh-HK, cantonese.ai |
| VAD | Silence timer | Silero VAD |
| G2P / lexicon QA | Curated Jyutping | pycantonese, rime-cantonese |
| SRS | SM-2 | FSRS / half-life regression |
| Backend | Hono + tRPC + Drizzle + MySQL | Same |
| Scoring research basis | LLM + char-overlap heuristic | Goodness of Pronunciation (Witt & Young) |

## 8. Quality & evaluation (from AI tutor_1)

| Metric | Target |
|---|---|
| Voice loop latency | < 2 s perceived (short replies) |
| ASR quality | WER + tone-error rate on held-out HK Cantonese test set |
| Tutor quality | ≥ 80% corrections rated useful by native reviewers |
| Learning | Phrase retention at 1/7/30 days |
| Retention | D1/D7/D30; crash-free sessions ≥ 99% |
| Privacy | Explicit mic consent; audio is processed in-browser, never uploaded |

## 9. Acceptance criteria (all met in MVP)

1. ✅ Start a scenario without configuration (persona pick → open conversation)
2. ✅ Speak English → relevant spoken Cantonese reply
3. ✅ Every reply: characters + Jyutping + English + audio controls
4. ✅ Speak Cantonese → pronunciation/tone score with subscores
5. ✅ Retry and see score improvement
6. ✅ Phrases auto-saved and findable in phrasebook
7. ✅ SM-2 review session with grading
8. ✅ Session summary with strengths/weaknesses/next steps
9. ✅ Full 5-minute session without failure (scripted fallback guarantees uptime)
10. ✅ Curated Cantonese reviewed for naturalness; LLM instructed to never invent

## 10. Roadmap

- **P1 (next):** persona voice differentiation (per-persona TTS voice), weak-area tracking surfaced on dashboard, Cantonese ASR upgrade (SenseVoice), per-scenario persona defaults
- **P2:** audio-only commuting mode, dynamic scenario generation, FSRS migration, animated avatar
- **P3:** multimodal (photo a menu → practice it), subscriptions, native-speaker content QA pipeline, mobile app
