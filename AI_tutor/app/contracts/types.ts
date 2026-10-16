export * from "./errors";

export type Level = "beginner" | "intermediate" | "advanced";
export type Mode = "conversation" | "drill" | "review";
export type UserLang = "en" | "yue";

export interface PhraseItem {
  cantonese: string;
  jyutping: string;
  english: string;
  note?: string;
}

/** Tutor turn output — mirrors the PDR §7.1 JSON contract. */
export interface TutorTurnResult {
  cantonese_reply: string;
  jyutping: string;
  english_translation: string;
  english_note: string;
  correction: {
    has_error: boolean;
    type: "tone" | "grammar" | "vocabulary" | "naturalness" | "none";
    original: string;
    corrected: string;
    explanation: string;
  };
  next_user_prompt: string;
  saved_phrase: {
    should_save: boolean;
    cantonese: string;
    jyutping: string;
    english: string;
  };
  /** Praktika-style continuous learner-state estimate (0–100 each). */
  learner_state_update: {
    fluency: number;
    accuracy: number;
    confidence: number;
    new_weak_areas: string[];
  };
  /** "ai" when produced by the LLM, "scripted" when the offline curriculum engine answered. */
  engine: "ai" | "scripted";
}

/** Pronunciation feedback — mirrors PDR §7.2 JSON contract. */
export interface PronunciationIssue {
  syllable: string;
  expected_jyutping: string;
  heard_or_predicted: string;
  issue_type: "tone" | "initial" | "final" | "rhythm" | "omission" | "substitution";
  feedback: string;
}

export interface PronunciationResult {
  overall_score: number;
  /** Praktika-style subscores, 0–100 (AI engine only; heuristic fills from overall). */
  subscores: { pronunciation: number; fluency: number; completeness: number; rhythm: number };
  passed: boolean;
  recognized_as: string;
  issues: PronunciationIssue[];
  priority_correction: string;
  encouragement: string;
  engine: "ai" | "heuristic";
}

export interface SessionSummary {
  overall_performance: string;
  strengths: string[];
  priority_improvements: string[];
  recommended_next_scenario: string;
  phrases_to_review: string[];
  encouragement: string;
}

export interface ProgressStats {
  sessionsCompleted: number;
  speakingSeconds: number;
  phrasesTotal: number;
  phrasesMastered: number;
  dueToday: number;
  avgPronunciation: number | null;
  streak: number;
  retention: number | null;
  scenarioCompletion: Record<string, number>;
}

export type AiErrorKind = "quota" | "transient" | "misconfigured" | "rejected" | null;
