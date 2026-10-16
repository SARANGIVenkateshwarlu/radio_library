import { createRouter, publicQuery } from "./middleware";
import { tutorRouter } from "./tutor";
import { learningRouter } from "./learning";

export const appRouter = createRouter({
  ping: publicQuery.query(() => ({ ok: true, ts: Date.now() })),
  tutor: tutorRouter,
  learning: learningRouter,
});

export type AppRouter = typeof appRouter;
