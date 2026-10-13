# LOCKED MASTER RULES 固定總規格

These rules are FINAL. Whenever the user uploads images or gives a topic,
pick the matching pipeline below and just do the task — no extra confirmation
questions. Do not change format, language rules, or layout without an explicit
request from the user.

Two locked pipelines:

- **Pipeline A — Photo Worksheet** (`src/`): a photo of a scene → printable
  colour-coded worksheet PDF.
- **Pipeline B — Lesson Notes** (`lessons/`, `prompts/cantonese_notes_generator.md`):
  photos of an existing lesson/worksheet, or a topic brief → full L3 lesson
  notes (dialogue → vocabulary → grammar → exercises → answer key) → A4 PDF.

Route by input:

| Input | Pipeline |
|---|---|
| Photo of a place / object / situation (street, minibus, MTR, bus, ATM, canteen, restaurant…) | A |
| Photos of printed lesson pages / handouts, OR a topic brief like "Lesson 4: Shopping" | B |
| User says which one explicitly | follow the user |

---

## Pipeline A — Photo Worksheet (locked)

**Trigger:** user uploads any scene photo → generate the worksheet PDF
immediately.

### Content rules

1. **10 sentences** in natural, colloquial Hong Kong Cantonese
   (spoken style, Traditional Chinese, directly related to the image or
   the given situation).
2. **Q&A section**: 3–5 question/answer pairs usable in class.
3. **Vocabulary table**: 12–20 practical HK words with columns:
   Chinese | Jyutping | POS 詞性 | English | Example.
4. Every Cantonese line carries:
   - Jyutping in the standard LSHK scheme with tone numbers 1–6.
   - A clear, simple English translation.
5. **Word-by-word colour matching** (locked):
   - Each sentence/Q&A is segmented into words:
     {"chinese", "jyutping", "english" gloss}.
   - The same word appears in the SAME colour on the Cantonese line,
     the Jyutping line, and the English-gloss line.
   - A grey italic full-sentence translation follows below.
   - Legend printed once: "Same colour = same word: 中文 = Jyutping = English."
   - Palette (print-safe): #c0392b #1f618d #1e8449 #b9770e #7d3c98 #117a65.

### Layout rules (locked)

- A4, black-on-white, print-friendly; as many pages as needed — readability
  beats fitting one page.
- Order: Title → uploaded image (kept in the page, ~70% width, caption)
  → Ten Key Sentences → Questions & Answers → Vocabulary table.
- Font sizes: title 21, section 15, Cantonese 16 bold, Jyutping/English 13,
  vocab table 11.5. Never shrink below these to force fewer pages.
- Page numbers on every page: "Page 第 N 頁".
- Tables: three-line style, header row repeats across pages.
- Output: ONE single PDF per uploaded image, named after the theme,
  saved to `output/`.

### Implementation

```bash
python3 src/main.py <uploaded_image> --out "output/<theme>.pdf"
# or offline from saved JSON:
python3 src/pdf_generator.py data/<lesson>.json <image> "output/<theme>.pdf"
```

- `src/agent.py` — vision description → teacher LLM → validated lesson JSON
  (10 sentences / 12–20 vocab enforced; see
  `prompts/cantonese_teacher_system.md`).
- `src/pdf_generator.py` — renders the locked layout above.
- `src/app.py` — Streamlit mobile app (camera → PDF) for the same pipeline.
- After every generation: run visual QA (`pdf.py inspect`) and fix any
  clipping/overlap before delivery.

---

## Pipeline B — Lesson Notes (locked)

**Trigger:** user uploads photos of a printed lesson/worksheet/handout, or
gives a lesson topic → produce the full lesson notes Markdown and convert to
a print-ready PDF.

### Spec

Follow `prompts/cantonese_notes_generator.md` EXACTLY. Summary:

- Structure, in this exact order: Title → Lesson Overview → Dialogue Context
  → Main Dialogue (8–12 turns, table format) → Vocabulary (12–20 entries)
  → Key Grammar (3–5 points: meaning/pattern/2 examples/common note)
  → Useful Expressions (6–10) → Pronunciation Focus (3–6)
  → Hong Kong Note → Exercises (A match / B fill blanks / C translate /
  D role-play) → Answer Key (full, with Jyutping + back-translation)
  → Lesson Review Checklist.
- Language: natural spoken HK Cantonese, Traditional Chinese only,
  LSHK Jyutping with tone numbers 1–6, no pinyin, no Simplified Chinese.
- Sentence-final particles (呀 喇 啦 囉 啩) only when natural.
- When the source is uploaded lesson photos: reuse and clean up the lesson's
  own dialogue, vocabulary and grammar; fix any Jyutping errors silently and
  note corrections in delivery.
- When the source is a topic brief: generate fresh content per the spec.

### PDF layout (locked)

- Stylesheet: `lessons/lesson_style.css` — A4 portrait, shaded section
  headers, bordered alternating-row tables, dialogue rows kept whole,
  answer key after exercises, whitespace for handwriting.
- Footer on every page: lesson title + 第 N 頁 (stamped post-conversion).
- Content is never changed during conversion — layout only.

### Implementation

```bash
cd lessons
pandoc <lesson>.md -f markdown -t html5 -s --css=lesson_style.css -o <lesson>.html
chromium --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
  --disable-crashpad --user-data-dir=/tmp/chrome-prof --no-pdf-header-footer \
  --print-to-pdf=<lesson>_raw.pdf <lesson>.html
# then stamp page footers (see previous deliverables) and save to output/
```

- After every generation: run visual QA (`pdf.py inspect`) and fix any
  clipping/overlap/split dialogue rows before delivery.

---

## Quality gates (both pipelines)

- Run `agent.validate_lesson` (Pipeline A) or the generator's QC checklist
  (Pipeline B) before rendering.
- Visual QA of the final PDF is mandatory; deliver only clean output.
- Name files in Chinese, human-readable, after the theme:
  `output/廣東話課堂_<主題>.pdf` (A) or `output/廣東話第N課_<主題>.pdf` (B).
