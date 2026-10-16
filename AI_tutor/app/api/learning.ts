import { z } from "zod";
import { and, asc, desc, eq, lte, sql } from "drizzle-orm";
import { createRouter, publicQuery } from "./middleware";
import { getDb } from "./queries/connection";
import { profiles, phrases, sessions, turns } from "@db/schema";
import { SCENARIOS } from "@contracts/scenarios";

async function requireProfile(deviceToken: string) {
  const db = getDb();
  const p = await db.query.profiles.findFirst({ where: eq(profiles.deviceToken, deviceToken) });
  if (!p) throw new Error("Profile not found — call profile.getOrCreate first");
  return p;
}

/** SM-2 scheduling. quality: 0–5 (>=3 pass). */
function sm2(state: { intervalDays: number; easeFactor: number; reps: number; lapses: number }, quality: number) {
  let { intervalDays, easeFactor, reps, lapses } = state;
  if (quality >= 3) {
    intervalDays = reps === 0 ? 1 : reps === 1 ? 6 : Math.round(intervalDays * easeFactor);
    reps += 1;
  } else {
    reps = 0;
    lapses += 1;
    intervalDays = 1;
  }
  easeFactor = Math.max(1.3, easeFactor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)));
  const dueAt = new Date(Date.now() + intervalDays * 24 * 3600 * 1000);
  return { intervalDays, easeFactor, reps, lapses, dueAt };
}

const today = () => new Date().toISOString().slice(0, 10);

export const learningRouter = createRouter({
  // ---------- profile ----------
  getOrCreateProfile: publicQuery
    .input(z.object({ deviceToken: z.string().min(8).max(64) }))
    .mutation(async ({ input }) => {
      const db = getDb();
      const existing = await db.query.profiles.findFirst({
        where: eq(profiles.deviceToken, input.deviceToken),
      });
      if (existing) {
        // streak update
        const t = today();
        if (existing.lastActiveDate !== t) {
          const yesterday = new Date(Date.now() - 86400000).toISOString().slice(0, 10);
          const streak = existing.lastActiveDate === yesterday ? existing.streak + 1 : 1;
          await db
            .update(profiles)
            .set({ streak, lastActiveDate: t })
            .where(eq(profiles.id, existing.id));
          return { ...existing, streak, lastActiveDate: t };
        }
        return existing;
      }
      const [{ id }] = await db
        .insert(profiles)
        .values({ deviceToken: input.deviceToken, streak: 1, lastActiveDate: today() })
        .$returningId();
      return (await db.query.profiles.findFirst({ where: eq(profiles.id, id) }))!;
    }),

  updateProfile: publicQuery
    .input(
      z.object({
        deviceToken: z.string(),
        name: z.string().max(64).optional(),
        level: z.enum(["beginner", "intermediate", "advanced"]).optional(),
        dailyGoalMinutes: z.number().int().min(1).max(120).optional(),
      }),
    )
    .mutation(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      await getDb()
        .update(profiles)
        .set({
          ...(input.name ? { name: input.name } : {}),
          ...(input.level ? { level: input.level } : {}),
          ...(input.dailyGoalMinutes ? { dailyGoalMinutes: input.dailyGoalMinutes } : {}),
        })
        .where(eq(profiles.id, p.id));
      return { ok: true };
    }),

  // ---------- phrasebook + SRS ----------
  savePhrase: publicQuery
    .input(
      z.object({
        deviceToken: z.string(),
        cantonese: z.string().min(1).max(255),
        jyutping: z.string().max(512),
        english: z.string().max(512),
        scenarioId: z.string().optional(),
        source: z.enum(["saved", "correction", "bookmark"]).default("saved"),
      }),
    )
    .mutation(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      const db = getDb();
      const dup = await db.query.phrases.findFirst({
        where: and(eq(phrases.userId, p.id), eq(phrases.cantonese, input.cantonese)),
      });
      if (dup) return dup;
      const [{ id }] = await db
        .insert(phrases)
        .values({
          userId: p.id,
          cantonese: input.cantonese,
          jyutping: input.jyutping,
          english: input.english,
          scenarioId: input.scenarioId ?? null,
          source: input.source,
        })
        .$returningId();
      return (await db.query.phrases.findFirst({ where: eq(phrases.id, id) }))!;
    }),

  listPhrases: publicQuery
    .input(z.object({ deviceToken: z.string() }))
    .query(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      return getDb().query.phrases.findMany({
        where: eq(phrases.userId, p.id),
        orderBy: [desc(phrases.createdAt)],
      });
    }),

  duePhrases: publicQuery
    .input(z.object({ deviceToken: z.string(), limit: z.number().int().min(1).max(50).default(20) }))
    .query(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      return getDb().query.phrases.findMany({
        where: and(eq(phrases.userId, p.id), lte(phrases.dueAt, new Date())),
        orderBy: [asc(phrases.dueAt)],
        limit: input.limit,
      });
    }),

  reviewPhrase: publicQuery
    .input(
      z.object({
        deviceToken: z.string(),
        phraseId: z.number().int(),
        quality: z.number().int().min(0).max(5),
        score: z.number().int().min(0).max(100).optional(),
      }),
    )
    .mutation(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      const db = getDb();
      const ph = await db.query.phrases.findFirst({
        where: and(eq(phrases.id, input.phraseId), eq(phrases.userId, p.id)),
      });
      if (!ph) throw new Error("Phrase not found");
      const next = sm2(ph, input.quality);
      await db
        .update(phrases)
        .set({
          ...next,
          lastResult: input.quality >= 3 ? "pass" : "fail",
          lastScore: input.score ?? ph.lastScore,
        })
        .where(eq(phrases.id, ph.id));
      return { ok: true, next };
    }),

  deletePhrase: publicQuery
    .input(z.object({ deviceToken: z.string(), phraseId: z.number().int() }))
    .mutation(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      await getDb()
        .delete(phrases)
        .where(and(eq(phrases.id, input.phraseId), eq(phrases.userId, p.id)));
      return { ok: true };
    }),

  // ---------- sessions ----------
  startSession: publicQuery
    .input(
      z.object({
        deviceToken: z.string(),
        scenarioId: z.string(),
        mode: z.enum(["conversation", "drill", "review"]),
      }),
    )
    .mutation(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      const [{ id }] = await getDb()
        .insert(sessions)
        .values({ userId: p.id, scenarioId: input.scenarioId, mode: input.mode })
        .$returningId();
      return { sessionId: id };
    }),

  addTurn: publicQuery
    .input(
      z.object({
        deviceToken: z.string(),
        sessionId: z.number().int(),
        userText: z.string().optional(),
        userLang: z.enum(["en", "yue"]).optional(),
        tutorCantonese: z.string().optional(),
        tutorJyutping: z.string().optional(),
        tutorEnglish: z.string().optional(),
        correctionJson: z.string().optional(),
        pronunciationScore: z.number().int().optional(),
      }),
    )
    .mutation(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      const db = getDb();
      const s = await db.query.sessions.findFirst({
        where: and(eq(sessions.id, input.sessionId), eq(sessions.userId, p.id)),
      });
      if (!s) throw new Error("Session not found");
      const { deviceToken: _, sessionId, ...rest } = input;
      await db.insert(turns).values({ sessionId, ...rest });
      await db
        .update(sessions)
        .set({ turnCount: s.turnCount + 1 })
        .where(eq(sessions.id, sessionId));
      return { ok: true };
    }),

  finishSession: publicQuery
    .input(
      z.object({
        deviceToken: z.string(),
        sessionId: z.number().int(),
        durationSeconds: z.number().int().min(0),
        overallScore: z.number().int().min(0).max(100).optional(),
        summaryJson: z.string().optional(),
      }),
    )
    .mutation(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      const db = getDb();
      await db
        .update(sessions)
        .set({
          endedAt: new Date(),
          durationSeconds: input.durationSeconds,
          overallScore: input.overallScore ?? null,
          summaryJson: input.summaryJson ?? null,
        })
        .where(and(eq(sessions.id, input.sessionId), eq(sessions.userId, p.id)));
      await db
        .update(profiles)
        .set({ totalSpeakingSeconds: sql`${profiles.totalSpeakingSeconds} + ${input.durationSeconds}` })
        .where(eq(profiles.id, p.id));
      return { ok: true };
    }),

  // ---------- progress ----------
  stats: publicQuery
    .input(z.object({ deviceToken: z.string() }))
    .query(async ({ input }) => {
      const p = await requireProfile(input.deviceToken);
      const db = getDb();
      const [sess, phr, turnRows] = await Promise.all([
        db.query.sessions.findMany({
          where: eq(sessions.userId, p.id),
          with: undefined,
        }),
        db.query.phrases.findMany({ where: eq(phrases.userId, p.id) }),
        db
          .select({ pronunciationScore: turns.pronunciationScore })
          .from(turns)
          .innerJoin(sessions, eq(turns.sessionId, sessions.id))
          .where(eq(sessions.userId, p.id)),
      ]);
      const done = sess.filter((s) => s.endedAt);
      const scores = turnRows
        .map((t) => t.pronunciationScore)
        .filter((x): x is number => x !== null);
      const reviewed = phr.filter((x) => x.reps > 0 || x.lapses > 0);
      const retained = reviewed.filter((x) => x.lastResult === "pass");
      const scenarioCompletion: Record<string, number> = {};
      for (const sc of SCENARIOS) {
        const steps = sc.script.length;
        const best = sess
          .filter((s) => s.scenarioId === sc.id)
          .reduce((m, s) => Math.max(m, s.turnCount), 0);
        scenarioCompletion[sc.id] = Math.min(1, steps === 0 ? 0 : best / steps);
      }
      const now = new Date();
      return {
        sessionsCompleted: done.length,
        speakingSeconds: p.totalSpeakingSeconds,
        phrasesTotal: phr.length,
        phrasesMastered: phr.filter((x) => x.intervalDays >= 21).length,
        dueToday: phr.filter((x) => x.dueAt <= now).length,
        avgPronunciation: scores.length
          ? Math.round(scores.reduce((a, b) => a + b, 0) / scores.length)
          : null,
        streak: p.streak,
        retention: reviewed.length ? Math.round((retained.length / reviewed.length) * 100) : null,
        scenarioCompletion,
        level: p.level,
        name: p.name,
        dailyGoalMinutes: p.dailyGoalMinutes,
      };
    }),
});
