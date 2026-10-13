# Cantonese Class Teacher Agent 廣東話老師 AI Agent

An AI agent that acts as a Cantonese teacher for international students.
The student uploads an image; the agent analyses it and produces a one-page,
print-ready PDF worksheet containing:

- the original image
- 5 natural Hong Kong Cantonese sentences with Jyutping (tone numbers) and English
- a Q&A section (question + answer, each with Cantonese / Jyutping / English)
- a vocabulary table (Chinese, Jyutping, POS, English, example)

## Project structure

```
cantonese_teacher_agent/
├── assets/          input images (minibus.jpg included)
├── data/            lesson JSON (minibus_lesson.json included)
├── output/          generated PDF worksheets
├── prompts/         system prompt for the teacher LLM
└── src/
    ├── agent.py          image -> vision description -> lesson JSON (+ validation)
    ├── pdf_generator.py  lesson JSON + image -> one-page A4 PDF (ReportLab)
    └── main.py           CLI glue: image -> PDF
```

## Setup

```bash
pip install -r requirements.txt
export OPENAI_API_KEY=...   # only needed for live LLM generation
```

## Usage

Full pipeline (vision model + teacher LLM):

```bash
python3 src/main.py assets/minibus.jpg --out output/worksheet.pdf
```

Render from a saved lesson JSON (offline / reproducible):

```bash
python3 src/main.py assets/minibus.jpg \
    --lesson data/minibus_lesson.json --out output/worksheet.pdf
```

The included `data/minibus_lesson.json` was written for the sample photo of a
Hong Kong green minibus (route 8 to Central, Exchange Square) and produces
`output/廣東話課堂_小巴.pdf`.

## Rules

The full specification is LOCKED in `RULES.md` — two pipelines:

- **Pipeline A (photo worksheet):** scene photo → colour-coded 10-sentence
  worksheet PDF (`src/`, prompt spec in `prompts/cantonese_teacher_system.md`)
- **Pipeline B (lesson notes):** lesson photos or a topic brief → full L3
  lesson notes (dialogue / vocab / grammar / exercises / answer key) → A4 PDF
  (`lessons/`, spec in `prompts/cantonese_notes_generator.md`, stylesheet
  `lessons/lesson_style.css`; example: `lessons/lesson3_place_and_transport.md`)

Follow RULES.md for every task unless the user explicitly asks for a change.

## Mobile app (Streamlit)

Take a photo with your phone and get the PDF in one tap:

```bash
pip install -r requirements.txt
streamlit run src/app.py --server.address 0.0.0.0
```

On your phone (same Wi-Fi), open `http://<computer-ip>:8501`:

- **📷 Take photo** tab opens the phone camera directly (or use Upload)
- Options: lesson theme, number of Q&A pairs, level, dated filename
- **Generate Worksheet** → **Download PDF** (follows the locked RULES.md spec)
- Without `OPENAI_API_KEY` the app runs in demo mode using the built-in
  minibus lesson; set the key for live AI generation

## Notes

- Jyutping follows the LSHK scheme with tone numbers 1–6.
- All Cantonese is Traditional Chinese, colloquial Hong Kong style.
- `agent.validate_lesson` checks structure and Jyutping shape before rendering.
- PDF is A4, black-on-white, print-friendly.
