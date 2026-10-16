import {
  mysqlTable,
  mysqlEnum,
  serial,
  varchar,
  text,
  int,
  float,
  bigint,
  timestamp,
  index,
} from "drizzle-orm/mysql-core";

/** Learner profile keyed by a device token generated in the browser. */
export const profiles = mysqlTable(
  "profiles",
  {
    id: serial("id").primaryKey(),
    deviceToken: varchar("device_token", { length: 64 }).notNull().unique(),
    name: varchar("name", { length: 64 }).notNull().default("Learner"),
    level: mysqlEnum("level", ["beginner", "intermediate", "advanced"])
      .notNull()
      .default("beginner"),
    dailyGoalMinutes: int("daily_goal_minutes").notNull().default(10),
    streak: int("streak").notNull().default(0),
    lastActiveDate: varchar("last_active_date", { length: 10 }),
    totalSpeakingSeconds: int("total_speaking_seconds").notNull().default(0),
    createdAt: timestamp("created_at").notNull().defaultNow(),
  },
  (t) => ({ tokenIdx: index("profiles_token_idx").on(t.deviceToken) }),
);

/** Saved phrase with SM-2 spaced-repetition state. */
export const phrases = mysqlTable(
  "phrases",
  {
    id: serial("id").primaryKey(),
    userId: bigint("user_id", { mode: "number", unsigned: true }).notNull(),
    cantonese: varchar("cantonese", { length: 255 }).notNull(),
    jyutping: varchar("jyutping", { length: 512 }).notNull(),
    english: varchar("english", { length: 512 }).notNull(),
    scenarioId: varchar("scenario_id", { length: 64 }),
    source: mysqlEnum("source", ["saved", "correction", "bookmark"])
      .notNull()
      .default("saved"),
    // SM-2 state
    intervalDays: float("interval_days").notNull().default(0),
    dueAt: timestamp("due_at").notNull().defaultNow(),
    easeFactor: float("ease_factor").notNull().default(2.5),
    reps: int("reps").notNull().default(0),
    lapses: int("lapses").notNull().default(0),
    lastResult: varchar("last_result", { length: 16 }),
    lastScore: int("last_score"),
    createdAt: timestamp("created_at").notNull().defaultNow(),
  },
  (t) => ({
    userIdx: index("phrases_user_idx").on(t.userId),
    dueIdx: index("phrases_due_idx").on(t.userId, t.dueAt),
  }),
);

/** A practice session within one scenario. */
export const sessions = mysqlTable(
  "sessions",
  {
    id: serial("id").primaryKey(),
    userId: bigint("user_id", { mode: "number", unsigned: true }).notNull(),
    scenarioId: varchar("scenario_id", { length: 64 }).notNull(),
    mode: mysqlEnum("mode", ["conversation", "drill", "review"])
      .notNull()
      .default("conversation"),
    startedAt: timestamp("started_at").notNull().defaultNow(),
    endedAt: timestamp("ended_at"),
    durationSeconds: int("duration_seconds").notNull().default(0),
    turnCount: int("turn_count").notNull().default(0),
    overallScore: int("overall_score"),
    summaryJson: text("summary_json"),
  },
  (t) => ({ userIdx: index("sessions_user_idx").on(t.userId) }),
);

/** One exchange (user → tutor) inside a session. */
export const turns = mysqlTable(
  "turns",
  {
    id: serial("id").primaryKey(),
    sessionId: bigint("session_id", { mode: "number", unsigned: true }).notNull(),
    userText: text("user_text"),
    userLang: mysqlEnum("user_lang", ["en", "yue"]),
    tutorCantonese: varchar("tutor_cantonese", { length: 512 }),
    tutorJyutping: varchar("tutor_jyutping", { length: 1024 }),
    tutorEnglish: varchar("tutor_english", { length: 1024 }),
    correctionJson: text("correction_json"),
    pronunciationScore: int("pronunciation_score"),
    createdAt: timestamp("created_at").notNull().defaultNow(),
  },
  (t) => ({ sessionIdx: index("turns_session_idx").on(t.sessionId) }),
);

export type Profile = typeof profiles.$inferSelect;
export type Phrase = typeof phrases.$inferSelect;
export type Session = typeof sessions.$inferSelect;
export type Turn = typeof turns.$inferSelect;
