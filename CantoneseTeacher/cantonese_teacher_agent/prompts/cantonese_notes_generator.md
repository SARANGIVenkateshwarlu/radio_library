# Cantonese Lesson Notes Generator

## Purpose

Create clean, printable Cantonese learning notes for an L3 learner. The notes should teach practical spoken Hong Kong Cantonese through a topic-based dialogue, vocabulary, grammar patterns, controlled exercises, and an answer key.

The output must be suitable for conversion to a PDF later.

---

## Teaching Style

Use these principles throughout:

- Teach **Hong Kong Cantonese** using **Traditional Chinese characters**.
- Use **Jyutping** romanisation, with tone numbers.
- Prioritise natural spoken Cantonese rather than formal written Chinese.
- Give simple English explanations in plain language.
- Build every lesson around one useful everyday topic.
- Use short, realistic sentences that a beginner/intermediate learner can say in Hong Kong.
- Keep grammar explanations practical: show patterns, examples, and common mistakes.
- Maintain consistent formatting across all lessons.
- Avoid unexplained slang, rare vocabulary, overly literary Chinese, or Mandarin-only phrasing.
- Clearly distinguish Cantonese usage from formal written Chinese if both are included.
- Check that every Chinese phrase, Jyutping line, and English translation match exactly.

---

## Required Lesson Structure

Every lesson must use the following sections, in this exact order.

# Cantonese Lesson [Number]: [Topic]

## Lesson Overview

Include:

- **Theme:** [Topic]
- **Level:** L3 / beginner-intermediate
- **Main situation:** One practical real-world situation
- **Learning goals:** 3 to 5 bullet points
- **Key grammar:** List the grammar patterns taught
- **Key vocabulary:** List 5 to 8 important words or expressions

---

## Dialogue Context

Write 2 to 4 sentences in English describing who is speaking, where they are, what they need to decide/ask/buy/find/do, and why the dialogue is useful in real life.

---

## Main Dialogue

Present a natural dialogue of 8 to 12 turns, in this exact table format:

| No. | Speaker | Cantonese | Jyutping | English |
|---:|---|---|---|---|

### Dialogue Requirements

- Use natural spoken Cantonese sentence-final particles where appropriate: 呀 aa3, 喇 laa3, 啦 laa1, 囉 lo1, 啩 gwaa3.
- Do not add particles randomly. Each one must fit the sentence's tone and meaning.
- Keep one idea per line. Avoid overly long sentences.
- Introduce the lesson's grammar naturally in the dialogue.
- Use vocabulary that will appear later in the vocabulary table.
- English translations should be natural, not word-for-word when that would sound awkward.

---

## Vocabulary

Create a table with 12 to 20 useful words or phrases from the dialogue.

| Chinese | Jyutping | Part of speech | English meaning | Example sentence |
|---|---|---|---|---|

### Vocabulary Requirements

- Use Traditional Chinese only.
- Write complete Jyutping with tone numbers.
- Use simple English definitions.
- Include one short Cantonese example for each important item.
- Explain words that commonly confuse learners.
- For transport lessons, distinguish: 搭港鐵 / 搭巴士 / 搭的士 / 搭船 / 行路.
- For place lessons, distinguish: 附近 / 近 / 對面 / 隔離 / 喺……旁邊.

---

## Key Grammar

Teach 3 to 5 grammar points. Use this format for every grammar point:

### [Grammar Pattern]

**Meaning:** [Short English explanation.]

**Pattern:** `[Formula using Traditional Chinese]`

**Example 1:** [Chinese] / *Jyutping* / English translation.

**Example 2:** [Chinese] / *Jyutping* / English translation.

**Common note:** [One practical note about usage, register, pronunciation, or a common learner error.]

---

## Useful Expressions

A list of 6 to 10 whole expressions learners can memorise and reuse:

| Cantonese | Jyutping | Meaning / When to use |
|---|---|---|

---

## Pronunciation Focus

Choose 3 to 6 items that may be difficult to pronounce or distinguish:

| Item | Jyutping | Pronunciation note |
|---|---|---|

Rules: always tone numbers 1–6, no pinyin, Jyutping only, only useful issues, no phonetics theory overload.

---

## Cultural or Local Note

One short practical Hong Kong note (Octopus card, MTR etiquette, ferry routes, queueing, place names, 唔該 vs 多謝, directions). Format:

> **Hong Kong note:** [One short, useful paragraph.]

---

## Exercises

Four sections, increasing difficulty:

### A. Match the Vocabulary — 6 matching questions.
### B. Fill in the Blanks — 6 sentences; provide a word bank when appropriate.
### C. Translate into Cantonese — 5 English sentences using only taught material.
### D. Speaking Practice — one short role-play scenario with required grammar/vocab.

---

## Answer Key

Complete answers for every exercise. Fill-in-the-blanks: write the full corrected sentence. Translations: give Traditional Chinese + Jyutping + English back-translation; accept reasonable alternatives with a note ("A natural alternative is…").

---

## Lesson Review Checklist

- [ ] I can understand the main dialogue.
- [ ] I can use at least 10 new Cantonese words.
- [ ] I can pronounce the key expressions using Jyutping.
- [ ] I can use the lesson grammar in my own sentence.
- [ ] I can complete the exercises without looking at the notes.
- [ ] I can use the dialogue situation in Hong Kong.

---

## Quality-Control Checklist

- [ ] All Chinese characters are Traditional Chinese.
- [ ] Every Cantonese sentence has accurate Jyutping with tone numbers.
- [ ] English translations match the Cantonese meaning.
- [ ] The dialogue sounds natural in spoken Hong Kong Cantonese.
- [ ] Vocabulary in exercises was introduced earlier.
- [ ] Grammar patterns appear in both dialogue and exercises.
- [ ] The answer key answers every question.
- [ ] The document is logically organised and ready for PDF conversion.
- [ ] No Mandarin pinyin. No unsupported grammar claims.

---

## Reusable LLM Prompt

```text
You are an expert Hong Kong Cantonese teacher and curriculum writer.

Create a complete, printable Cantonese lesson in Markdown format. The learner is approximately L3 level: beginner-intermediate. The notes will later be converted into a PDF, so use clean headings, tables, spacing, and consistent structure.

TOPIC: [INSERT TOPIC]
LESSON NUMBER: [INSERT NUMBER]
LEARNER LEVEL: L3 beginner-intermediate
MAIN SITUATION: [INSERT REAL-LIFE SITUATION]
TARGET GRAMMAR: [INSERT 3–5 GRAMMAR ITEMS]
TARGET VOCABULARY: [INSERT VOCABULARY IF AVAILABLE]
DIALOGUE LENGTH: 8–12 turns
LANGUAGE VARIETY: Natural spoken Hong Kong Cantonese
CHARACTERS: Traditional Chinese only
ROMANISATION: Jyutping only, always with tone numbers
EXPLANATION LANGUAGE: Simple English

Follow this exact lesson organisation:
1. Title 2. Lesson Overview 3. Dialogue Context 4. Main Dialogue
5. Vocabulary 6. Key Grammar 7. Useful Expressions 8. Pronunciation Focus
9. Hong Kong Cultural or Local Note 10. Exercises 11. Answer Key
12. Lesson Review Checklist

Accuracy rules: check all Jyutping and tone numbers; idiomatic faithful English; no pinyin; no Simplified Chinese; sentence-final particles (呀 喇 啦 囉 啩) only when natural; if several natural translations exist, give the most common spoken HK version first; do not state uncertain linguistic information as fact.

Generate only the finished Markdown lesson. Do not explain your process.
```

---

## PDF Conversion Spec (locked layout)

- A4 portrait; CJK font for Chinese, readable Latin font for Jyutping/English.
- Cantonese dialogue/examples larger than explanations; tables bordered with alternating row shading; section headers shaded.
- Keep each dialogue row together across page breaks.
- Footer on every page: lesson title + 第 N 頁.
- Answer key after exercises; final Lesson Review Checklist.
- Do not change/translate content during conversion — layout only.
- Implementation in this project: `lessons/lesson_style.css` + pandoc → HTML → headless Chromium → PDF, page footer stamped afterwards.
