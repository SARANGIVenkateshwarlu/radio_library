
## Recommended app

For a Hong Kong Cantonese learning app, do not ask one LLM call to perform **audio transcription, Cantonese normalization, Jyutping conversion, translation, and teaching explanations simultaneously**. Use a staged pipeline with structured outputs, validation, and human-review flags.

Jyutping should follow the Linguistic Society of Hong Kong scheme: each syllable contains an onset/final structure and a tone number from 1–6, with the tone number written at the end. Cantonese corpora also commonly maintain a character/syllable alignment, which is useful for displaying Chinese text, Jyutping, and English together.[^1][^2]

## Top 10 guidelines

### 1. Define Hong Kong Cantonese explicitly

Tell the model that the target variety is **modern Hong Kong Cantonese**, not Mandarin, Taiwan Cantonese, Guangzhou Cantonese, or written Chinese.

Include these requirements:

- Prefer Hong Kong colloquial pronunciation and vocabulary.
- Preserve Cantonese sentence-final particles such as `喎`, `喇`, `啫`, `㗎`, `吖`, `啦`, and `喎`.
- Distinguish spoken Cantonese from formal written Chinese.
- Do not automatically rewrite Cantonese into Mandarin-style vocabulary.
- Preserve code-switching, English words, names, and local expressions.

For example, do not convert spoken `食咗飯未呀？` into formal written Chinese before analysis. The learner should see the authentic Hong Kong speech.

### 2. Separate audio transcription from language interpretation

Use separate stages:

1. Voice activity detection and noise reduction.
2. Cantonese ASR transcription.
3. Cantonese text correction.
4. Word segmentation.
5. Character-to-Jyutping conversion.
6. English translation.
7. Explanation and confidence scoring.

The LLM should not invent words simply because a sentence sounds semantically likely. Ask it to distinguish between:

- What is clearly audible.
- What is linguistically inferred.
- What is uncertain.
- What is inaudible because of music or noise.

A good rule is:

> Never replace an uncertain audio segment with a confident guess without marking the uncertainty.

### 3. Preserve the original spoken form

Require the model to produce two separate Chinese fields:

- `verbatim_transcript`: what the speaker appears to say.
- `normalized_transcript`: a readable Cantonese representation using appropriate Chinese characters.

This is important because speech may contain:

- Fillers such as `即係`, `嗯`, `嗰個`.
- Repetitions.
- False starts.
- Slang.
- Reduced pronunciation.
- English insertions.
- Incomplete sentences.

Do not silently remove these elements. If a cleanup is useful, provide it as a separate field rather than replacing the original.

### 4. Use Jyutping only, with strict validation

Instruct the model to use **LSHK Jyutping**, not Yale, Cantonese Pinyin, Mandarin Pinyin, or ad hoc English spelling. The official scheme uses tone numbers 1–6 at the end of each syllable.[^1]

Require these rules:

- Every Chinese syllable must have a Jyutping syllable.
- Every Jyutping syllable must end in a valid tone number.
- Do not use tone marks such as `ā`, `á`, or `à` unless your app explicitly supports another format.
- Do not write `nei ho` when the required format is `nei5 hou2`.
- Keep word-level spaces consistent.
- Do not merge syllables incorrectly.

For example:

```text
Chinese: 你好
Jyutping: nei5 hou2
English: Hello
```

Also validate Jyutping programmatically using a legal syllable table. Do not rely only on the LLM to check its own output.

### 5. Treat tones as essential information

Cantonese is tonal, and tone mistakes can change meaning. Your prompt should explicitly say that tone numbers are not optional pronunciation decoration.

Ask the model to:

- Provide one tone number for every syllable.
- Flag uncertain tones.
- Avoid changing tone numbers merely to make a word match a dictionary guess.
- Preserve context-sensitive pronunciation where relevant.
- Distinguish lexical tone from natural speech intonation.

Do not expect an LLM to infer tones reliably from Chinese characters alone. Characters can help predict pronunciation, but the audio remains important, especially for colloquial speech, names, particles, and tone changes.

### 6. Handle multiple pronunciations and colloquial readings

Many Cantonese characters have multiple readings or different common spoken pronunciations. The model should select a pronunciation based on:

- The local sentence context.
- The actual audio.
- Hong Kong usage.
- The grammatical role of the word.
- Whether the item is a particle, name, slang expression, or loanword.

Require an explanation only when ambiguity matters. For example:

```json
{
  "text": "呢個",
  "jyutping": "ni1 go3",
  "alternative": "nei1 go3",
  "status": "context-dependent",
  "note": "The first syllable may be pronounced differently in colloquial Hong Kong speech."
}
```

Do not make the learner see a long list of alternatives for every sentence. Show alternatives only when confidence is low or the pronunciation is genuinely variable.

### 7. Keep spoken Cantonese and written Cantonese distinct

Your app should not confuse these different layers:


| Layer | Purpose |
| :-- | :-- |
| Verbatim speech | Represents what was heard |
| Written Cantonese | Natural Hong Kong Chinese representation |
| Formal Chinese | Optional reading or written equivalent |
| Jyutping | Pronunciation support |
| English | Meaning and usage explanation |

For example, a useful output may be:

```text
Spoken Cantonese: 我哋一陣去邊度食飯呀？
Jyutping: ngo5 dei6 jat1 zan6 heoi3 bin1 dou6 sik6 faan6 aa3?
English: Where shall we go to eat later?
Formal equivalent: 我們待會兒去哪裡吃飯？
```

The formal equivalent should be optional. It must not replace the original Cantonese learner input.

### 8. Translate meaning, not individual characters

Ask the LLM to translate at three levels:

- Natural English translation.
- Literal gloss, when useful for learning.
- Short usage explanation.

Character-by-character translation can produce unnatural or misleading English. Cantonese particles, classifiers, aspect markers, and idioms often need sentence-level interpretation.

Recommended format:

```json
{
  "natural_english": "Have you eaten yet?",
  "literal_gloss": "Eat-finished meal not-yet?",
  "usage_note": "A common greeting in Cantonese; it does not always represent a real invitation to eat."
}
```

The English translation should not invent information about gender, tense, politeness, or intention unless the Cantonese context supports it.

### 9. Use timestamps and aligned segments

For radio MP3 content, return short timestamped segments rather than one large transcript. A useful segment may contain:

```json
{
  "start": 12.40,
  "end": 15.85,
  "verbatim": "我哋聽日再傾啦",
  "characters": "我哋聽日再傾啦",
  "jyutping": "ngo5 dei6 ting1 jat6 zoi3 king1 laa1",
  "english": "Let’s talk again tomorrow.",
  "confidence": 0.91
}
```

For learner usability, align each segment at the phrase or word level where possible. Cantonese corpora commonly link Chinese characters and syllables in a one-to-one manner, which is a useful design model for synchronized learner display.[^2]

Avoid creating unnecessarily tiny segments that split every syllable. Segment boundaries should generally follow phrases, clauses, or meaningful pauses.

### 10. Add uncertainty, evidence, and validation fields

Every output should expose uncertainty instead of presenting all results as equally reliable.

Recommended fields:

```json
{
  "audio_quality": "good | noisy | music | overlapping_speech",
  "transcription_confidence": 0.0,
  "jyutping_confidence": 0.0,
  "translation_confidence": 0.0,
  "uncertain_tokens": [],
  "possible_alternatives": [],
  "needs_human_review": false,
  "review_reason": null
}
```

Set `needs_human_review` to `true` when:

- Music overlaps the voice.
- Multiple speakers overlap.
- A proper name is unclear.
- The model proposes an invalid Jyutping syllable.
- The Chinese text and Jyutping have different syllable counts.
- The English translation contains information absent from the audio.
- The confidence is below your chosen threshold.


## Strong system prompt

You can use the following as a starting system prompt:

```text
You are a Hong Kong Cantonese transcription and language-learning assistant.

Your target variety is modern spoken Hong Kong Cantonese. Do not convert the input to Mandarin, Guangzhou Cantonese, or formal written Chinese unless explicitly requested.

Your tasks are:
1. Transcribe only what is audible.
2. Preserve Cantonese vocabulary, particles, fillers, repetitions, English insertions, slang, and false starts.
3. Produce a readable Cantonese character transcription separately from the verbatim transcription.
4. Convert each Chinese syllable to LSHK Jyutping.
5. Use tone numbers 1–6 after every Jyutping syllable.
6. Use valid Jyutping spelling only.
7. Translate the sentence into natural English.
8. Add a literal gloss or usage note only when it helps the learner.
9. Mark uncertainty instead of guessing silently.
10. Never invent names, words, tones, or meanings that are not supported by the audio or context.

Validation requirements:
- The number of Chinese syllables and Jyutping syllables must correspond.
- Every Jyutping syllable must have a tone number.
- Do not use Yale romanization or Mandarin pinyin.
- Do not replace colloquial Cantonese with formal Chinese.
- If the audio is unclear, use [unclear] and explain the reason.
- If music or noise interferes with speech, identify the affected span.
- If there are multiple plausible readings, provide the primary reading and list alternatives separately.

Return valid JSON matching the requested schema.
```


## Suggested JSON schema

```json
{
  "source": {
    "filename": "example.mp3",
    "language": "yue-Hant-HK",
    "dialect": "Hong Kong Cantonese"
  },
  "segments": [
    {
      "id": 1,
      "start": 0.0,
      "end": 4.2,
      "verbatim_transcript": "",
      "normalized_cantonese": "",
      "jyutping": "",
      "english_translation": "",
      "literal_gloss": "",
      "usage_note": "",
      "uncertain_tokens": [],
      "alternative_readings": [],
      "confidence": {
        "audio": 0.0,
        "transcription": 0.0,
        "jyutping": 0.0,
        "translation": 0.0
      },
      "needs_human_review": false,
      "review_reason": null
    }
  ]
}
```


## Practical quality-control pipeline

Use deterministic checks after every LLM response:

1. Parse and validate the JSON.
2. Check that timestamps are increasing and non-overlapping.
3. Check that Chinese characters, Jyutping syllables, and English fields are present.
4. Tokenize Jyutping and verify every syllable against a legal Jyutping dictionary.
5. Check that every Jyutping syllable ends with a tone number from 1–6.
6. Compare the number of Chinese syllables with the number of Jyutping syllables.
7. Run a second-pass reviewer model only on low-confidence segments.
8. Send uncertain names, particles, and overlapping speech to human review.
9. Store the original ASR output and every correction for auditability.
10. Evaluate with a manually labelled Hong Kong Cantonese test set.

Automatic annotation followed by correction by native Cantonese speakers is also a practical corpus-building strategy used in Cantonese ASR data work. For your app, native review is especially valuable for sentence-final particles, slang, names, reduced speech, and noisy radio recordings.[^3]

## Important architecture warning

An LLM is useful for correction, normalization, translation, and explanations, but it should not be the only component responsible for acoustic recognition or tone accuracy. Use a Cantonese-capable ASR model for the audio, then use the LLM as a constrained post-processing and teaching layer.

Your most reliable architecture is:

```text
MP3
  → audio preprocessing
  → Cantonese ASR with timestamps
  → LLM correction with uncertainty
  → Jyutping converter and validator
  → English translation
  → second-pass reviewer
  → learner interface
```

For the initial version, measure at least:

- Character or word transcription error rate.
- Jyutping syllable accuracy.
- Tone accuracy.
- English translation adequacy.
- Timestamp alignment quality.
- Uncertainty detection precision.
- Native-speaker acceptability.

A transcript that looks fluent but has incorrect Jyutping tones should be considered a failure for a pronunciation-learning app.
