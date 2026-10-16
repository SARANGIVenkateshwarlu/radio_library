import { z } from "zod";
import { generateObject } from "ai";
import { createRouter, publicQuery } from "./middleware";
import { kimiGw, defaultModelId } from "./ai/provider";
import {
  classifyAiError,
  AiUnavailable,
  AiMisconfigured,
  ContentRejected,
} from "./ai/ai-client";
import {
  TUTOR_SYSTEM,
  personaBlock,
  tutorUserPrompt,
  PRONUNCIATION_SYSTEM,
  pronunciationUserPrompt,
  TRANSLATE_SYSTEM,
  SUMMARY_SYSTEM,
  summaryUserPrompt,
} from "./prompts";
import { getScenario, SCENARIOS } from "@contracts/scenarios";
import { getPersona, PERSONAS } from "@contracts/personas";
import type {
  TutorTurnResult,
  PronunciationResult,
  SessionSummary,
  AiErrorKind,
} from "@contracts/types";

function aiErrorKind(err: unknown): AiErrorKind {
  const e = classifyAiError(err);
  if (e instanceof AiUnavailable) return "quota";
  if (e instanceof AiMisconfigured) return "misconfigured";
  if (e instanceof ContentRejected) return "rejected";
  return "transient";
}

const correctionSchema = z.object({
  has_error: z.boolean(),
  type: z.enum(["tone", "grammar", "vocabulary", "naturalness", "none"]),
  original: z.string(),
  corrected: z.string(),
  explanation: z.string(),
});

const tutorTurnSchema = z.object({
  cantonese_reply: z.string(),
  jyutping: z.string(),
  english_translation: z.string(),
  english_note: z.string().default(""),
  correction: correctionSchema,
  next_user_prompt: z.string().default(""),
  saved_phrase: z.object({
    should_save: z.boolean(),
    cantonese: z.string().default(""),
    jyutping: z.string().default(""),
    english: z.string().default(""),
  }),
  learner_state_update: z
    .object({
      fluency: z.number().min(0).max(100),
      accuracy: z.number().min(0).max(100),
      confidence: z.number().min(0).max(100),
      new_weak_areas: z.array(z.string()).default([]),
    })
    .default({ fluency: 50, accuracy: 50, confidence: 50, new_weak_areas: [] }),
});

const pronunciationSchema = z.object({
  overall_score: z.number().min(0).max(100),
  subscores: z
    .object({
      pronunciation: z.number().min(0).max(100),
      fluency: z.number().min(0).max(100),
      completeness: z.number().min(0).max(100),
      rhythm: z.number().min(0).max(100),
    })
    .default({ pronunciation: 0, fluency: 0, completeness: 0, rhythm: 0 }),
  passed: z.boolean(),
  recognized_as: z.string().default(""),
  issues: z
    .array(
      z.object({
        syllable: z.string(),
        expected_jyutping: z.string(),
        heard_or_predicted: z.string(),
        issue_type: z.enum(["tone", "initial", "final", "rhythm", "omission", "substitution"]),
        feedback: z.string(),
      }),
    )
    .default([]),
  priority_correction: z.string().default(""),
  encouragement: z.string().default(""),
});

const translateSchema = z.object({
  english_input: z.string(),
  cantonese: z.string(),
  jyutping: z.string(),
  english_translation: z.string(),
  register: z.enum(["casual", "polite", "formal"]),
  notes: z.string().default(""),
});

const summarySchema = z.object({
  overall_performance: z.string(),
  strengths: z.array(z.string()).default([]),
  priority_improvements: z.array(z.string()).default([]),
  recommended_next_scenario: z.string().default(""),
  phrases_to_review: z.array(z.string()).default([]),
  encouragement: z.string().default(""),
});

// ---------- scripted fallback engine (offline curriculum) ----------

const norm = (s: string) =>
  s.toLowerCase().replace(/[\s\p{P}\p{S}]+/gu, "").trim();

function charF1(a: string, b: string): number {
  const A = [...norm(a)];
  const B = [...norm(b)];
  if (!A.length || !B.length) return 0;
  const bPool = [...B];
  let hit = 0;
  for (const ch of A) {
    const i = bPool.indexOf(ch);
    if (i >= 0) {
      hit++;
      bPool.splice(i, 1);
    }
  }
  const p = hit / A.length;
  const r = hit / B.length;
  return p + r === 0 ? 0 : (2 * p * r) / (p + r);
}

function scriptedTurn(input: {
  scenarioId: string;
  userText: string;
  userLang: "en" | "yue";
  stepIndex: number;
}): { result: TutorTurnResult; nextStep: number } {
  const sc = getScenario(input.scenarioId) ?? SCENARIOS[0];
  const steps = sc.script;

  // Free-talk has no script — the scripted engine can't improvise, so it teaches instead.
  if (steps.length === 0) {
    return {
      result: {
        cantonese_reply: "「廣東話點講」？話我知你想講咩，我教你講。",
        jyutping: "gwong2 dung1 waa2 dim2 gong2? waa6 ngo5 zi1 nei5 soeng2 gong2 me1, ngo5 gaau3 nei5 gong2.",
        english_translation: "Tell me what you want to say in English and I'll teach you the Cantonese.",
        english_note:
          "Free talk works best with the AI tutor online. Meanwhile, type anything in English and I'll help phrase it.",
        correction: { has_error: false, type: "none" as const, original: "", corrected: "", explanation: "" },
        next_user_prompt: "Say anything in English — ask how to say it in Cantonese.",
        saved_phrase: { should_save: false, cantonese: "", jyutping: "", english: "" },
        learner_state_update: { fluency: 50, accuracy: 50, confidence: 50, new_weak_areas: [] },
        engine: "scripted",
      },
      nextStep: 0,
    };
  }

  let step = Math.min(input.stepIndex, steps.length - 1);
  const current = steps[step];
  const userLower = input.userText.toLowerCase();

  const matchesIntent =
    input.userLang === "yue"
      ? charF1(input.userText, current.teach.cantonese) > 0.4 ||
        current.acceptKeywords.some((k) => /[㐀-鿿]/.test(k) && input.userText.includes(k))
      : current.acceptKeywords.some((k) => !/[㐀-鿿]/.test(k) && userLower.includes(k));

  const advance = matchesIntent;
  const tutorStep = advance && step + 1 < steps.length ? steps[step + 1] : current;
  const nextStep = advance ? Math.min(step + 1, steps.length) : step;
  const done = nextStep >= steps.length;

  let cantonese: string;
  let jyutping: string;
  let english: string;
  let note = "";
  let savedPhrase = { should_save: false, cantonese: "", jyutping: "", english: "" };

  if (!matchesIntent && input.userLang === "en") {
    // Teach the phrase for the current step, then re-prompt.
    cantonese = `你可以咁講：${current.teach.cantonese}`;
    jyutping = `nei5 ho2 ji5 gam3 gong2: ${current.teach.jyutping}`;
    english = `You can say it like this: "${current.teach.english}"`;
    note = `Try repeating it aloud — then I'll respond as your partner.`;
    savedPhrase = {
      should_save: true,
      cantonese: current.teach.cantonese,
      jyutping: current.teach.jyutping,
      english: current.teach.english,
    };
  } else if (done) {
    cantonese = "好叻呀！今日練得好好，下次再傾過！";
    jyutping = "hou2 lek1 aa3! gam1 jat6 lin6 dak1 hou2 hou2, haa6 ci3 zoi3 king1 gwo3!";
    english = "Well done! Great practice today — let's chat again next time!";
    note = "Scenario complete. Review your saved phrases or try the drill mode.";
  } else {
    cantonese = tutorStep.tutor.cantonese;
    jyutping = tutorStep.tutor.jyutping;
    english = tutorStep.tutor.english;
    if (advance && matchesIntent && input.userLang === "yue") {
      const score = charF1(input.userText, current.teach.cantonese);
      if (score < 0.9) {
        note = "Nice! Check the correction below for a more natural version.";
      }
    }
  }

  const correction = (() => {
    if (input.userLang !== "yue" || !matchesIntent)
      return { has_error: false, type: "none" as const, original: "", corrected: "", explanation: "" };
    const score = charF1(input.userText, current.teach.cantonese);
    if (score >= 0.9)
      return { has_error: false, type: "none" as const, original: "", corrected: "", explanation: "" };
    return {
      has_error: true,
      type: "naturalness" as const,
      original: input.userText,
      corrected: current.teach.cantonese,
      explanation: `The most natural way to say it here is "${current.teach.cantonese}" (${current.teach.jyutping}) — ${current.teach.english}.`,
    };
  })();

  return {
    result: {
      cantonese_reply: cantonese,
      jyutping,
      english_translation: english,
      english_note: note,
      correction,
      next_user_prompt: done ? "Scenario complete — well done!" : tutorStep.hint,
      saved_phrase: savedPhrase,
      learner_state_update: {
        fluency: 50 + (matchesIntent ? 15 : 0),
        accuracy: 50 + (matchesIntent ? 15 : 0),
        confidence: 55,
        new_weak_areas: [],
      },
      engine: "scripted",
    },
    nextStep,
  };
}

// ---------- heuristic pronunciation fallback ----------

function heuristicScore(input: {
  targetCantonese: string;
  targetJyutping: string;
  recognizedText: string;
}): PronunciationResult {
  const target = [...norm(input.targetCantonese)];
  const heard = [...norm(input.recognizedText)];
  if (!heard.length) {
    return {
      overall_score: 0,
      subscores: { pronunciation: 0, fluency: 0, completeness: 0, rhythm: 0 },
      passed: false,
      recognized_as: "",
      issues: [],
      priority_correction: "I couldn't hear anything — try again a little louder and slower.",
      encouragement: "Take a breath and give it another go!",
      engine: "heuristic",
    };
  }
  const f1 = charF1(input.recognizedText, input.targetCantonese);
  const score = Math.round(f1 * 100);
  const expectedSyllables = input.targetJyutping.trim().split(/\s+/).filter(Boolean);

  const issues = [] as PronunciationResult["issues"];
  if (f1 < 1) {
    const heardPool = [...heard];
    target.forEach((ch, i) => {
      const idx = heardPool.indexOf(ch);
      if (idx >= 0) {
        heardPool.splice(idx, 1);
      } else if (issues.length < 3) {
        const exp = expectedSyllables[i] ?? expectedSyllables[expectedSyllables.length - 1] ?? "";
        issues.push({
          syllable: ch,
          expected_jyutping: exp,
          heard_or_predicted: "not recognized",
          issue_type: "tone",
          feedback: `The recognizer didn't catch "${ch}" (${exp}). Focus on the tone contour of ${exp} and say it clearly.`,
        });
      }
    });
  }

  return {
    overall_score: score,
    subscores: { pronunciation: score, fluency: score, completeness: score, rhythm: Math.max(0, score - 10) },
    passed: score >= 70,
    recognized_as: input.recognizedText,
    issues,
    priority_correction:
      score >= 95
        ? "Excellent — that sounded right!"
        : score >= 70
          ? "Good! Slow down on the characters marked below and mind their tones."
          : "Listen to the reference audio at 0.5× speed, then try again syllable by syllable.",
    encouragement:
      score >= 90 ? "好叻！That was great!" : score >= 70 ? "加油！Almost there!" : "唔緊要 — practice makes perfect!",
    engine: "heuristic",
  };
}

// ---------- router ----------

export const tutorRouter = createRouter({
  personas: publicQuery.query(() => PERSONAS),

  scenarios: publicQuery.query(() =>
    SCENARIOS.map((s) => ({
      id: s.id,
      title: s.title,
      subtitle: s.subtitle,
      icon: s.icon,
      color: s.color,
      minutes: s.minutes,
      setting: s.setting,
      objectives: s.objectives,
      targetPhrases: s.targetPhrases,
      openingLine: s.openingLine,
      likelyMistakes: s.likelyMistakes,
      assessmentPhrases: s.assessmentPhrases,
      scriptLength: s.script.length,
    })),
  ),

  turn: publicQuery
    .input(
      z.object({
        scenarioId: z.string(),
        level: z.enum(["beginner", "intermediate", "advanced"]),
        userText: z.string().min(1),
        userLang: z.enum(["en", "yue"]),
        personaId: z.string().default("wing"),
        stepIndex: z.number().int().min(0).default(0),
        history: z
          .array(z.object({ role: z.enum(["user", "assistant"]), content: z.string() }))
          .max(20)
          .default([]),
      }),
    )
    .mutation(async ({ input }) => {
      const sc = getScenario(input.scenarioId) ?? SCENARIOS[0];
      try {
        const { object } = await generateObject({
          model: kimiGw()(await defaultModelId()),
          schema: tutorTurnSchema,
          system: TUTOR_SYSTEM + personaBlock(getPersona(input.personaId).promptDescription),
          messages: [
            ...input.history,
            {
              role: "user" as const,
              content: tutorUserPrompt({
                level: input.level,
                scenario: `${sc.title} — ${sc.setting}`,
                targetPhrases: sc.targetPhrases
                  .map((p) => `${p.cantonese} (${p.jyutping}) = ${p.english}`)
                  .join("; "),
                weakAreas: "",
                userText: input.userText,
                userLang: input.userLang,
              }),
            },
          ],
          providerOptions: { "kimi-gw": { max_completion_tokens: 1200 } },
        });
        const result: TutorTurnResult = { ...object, engine: "ai" };
        // AI answered freely; advance the script if the learner's intent matched.
        const step = Math.min(input.stepIndex, sc.script.length - 1);
        const cur = sc.script[step];
        const hit = !cur ? false : cur.acceptKeywords.some((k) =>
          /[㐀-鿿]/.test(k)
            ? input.userLang === "yue" && input.userText.includes(k)
            : input.userText.toLowerCase().includes(k),
        );
        return { result, nextStep: hit ? Math.min(step + 1, sc.script.length) : step, aiError: null };
      } catch (err) {
        const { result, nextStep } = scriptedTurn(input);
        return { result, nextStep, aiError: aiErrorKind(err) };
      }
    }),

  pronunciation: publicQuery
    .input(
      z.object({
        targetCantonese: z.string(),
        targetJyutping: z.string(),
        recognizedText: z.string(),
        level: z.enum(["beginner", "intermediate", "advanced"]),
      }),
    )
    .mutation(async ({ input }) => {
      try {
        const { object } = await generateObject({
          model: kimiGw()(await defaultModelId()),
          schema: pronunciationSchema,
          system: PRONUNCIATION_SYSTEM,
          prompt: pronunciationUserPrompt({
            targetCantonese: input.targetCantonese,
            targetJyutping: input.targetJyutping,
            recognizedText: input.recognizedText,
            level: input.level,
          }),
          providerOptions: { "kimi-gw": { max_completion_tokens: 900 } },
        });
        const result: PronunciationResult = { ...object, engine: "ai" };
        return { result, aiError: null };
      } catch (err) {
        return { result: heuristicScore(input), aiError: aiErrorKind(err) };
      }
    }),

  translate: publicQuery
    .input(z.object({ english: z.string().min(1) }))
    .mutation(async ({ input }) => {
      try {
        const { object } = await generateObject({
          model: kimiGw()(await defaultModelId()),
          schema: translateSchema,
          system: TRANSLATE_SYSTEM,
          prompt: input.english,
          providerOptions: { "kimi-gw": { max_completion_tokens: 600 } },
        });
        return { result: object, aiError: null };
      } catch (err) {
        return { result: null, aiError: aiErrorKind(err) };
      }
    }),

  summary: publicQuery
    .input(
      z.object({
        scenarioId: z.string(),
        transcript: z.string(),
        scores: z.array(z.number()),
        errors: z.array(z.string()),
        savedPhrases: z.array(z.string()),
      }),
    )
    .mutation(async ({ input }) => {
      const sc = getScenario(input.scenarioId);
      try {
        const { object } = await generateObject({
          model: kimiGw()(await defaultModelId()),
          schema: summarySchema,
          system: SUMMARY_SYSTEM,
          prompt: summaryUserPrompt({
            scenario: sc?.title ?? input.scenarioId,
            transcript: input.transcript || "(empty)",
            scores: input.scores.join(", ") || "none",
            errors: input.errors.join("; ") || "none",
            savedPhrases: input.savedPhrases.join("; ") || "none",
          }),
          providerOptions: { "kimi-gw": { max_completion_tokens: 800 } },
        });
        return { result: object as SessionSummary, aiError: null };
      } catch (err) {
        // Deterministic fallback summary
        const avg = input.scores.length
          ? Math.round(input.scores.reduce((a, b) => a + b, 0) / input.scores.length)
          : null;
        const fallback: SessionSummary = {
          overall_performance: avg !== null ? `Average pronunciation score: ${avg}/100.` : "Session completed.",
          strengths: input.errors.length === 0 ? ["No major errors recorded this session"] : ["Kept the conversation going"],
          priority_improvements: input.errors.slice(0, 2),
          recommended_next_scenario: "",
          phrases_to_review: input.savedPhrases.slice(0, 5),
          encouragement: "Practice a little every day — 加油！",
        };
        return { result: fallback, aiError: aiErrorKind(err) };
      }
    }),
});
