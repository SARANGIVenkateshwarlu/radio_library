import { useEffect, useState } from "react";
import { Link } from "react-router";
import {
  Flame,
  MessageCircle,
  Mic,
  Clock3,
  BookMarked,
  RotateCcw,
  TrendingUp,
  ChevronRight,
  MicOff,
} from "lucide-react";
import { trpc } from "@/providers/trpc";
import { getDeviceToken } from "@/lib/profile";
import { Layout } from "@/components/Layout";
import { speechSupported } from "@/hooks/useSpeech";
import { cn } from "@/lib/utils";

export default function Home() {
  const deviceToken = getDeviceToken();
  const ensure = trpc.learning.getOrCreateProfile.useMutation();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    ensure.mutate({ deviceToken }, { onSettled: () => setReady(true) });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [deviceToken]);

  const statsQ = trpc.learning.stats.useQuery({ deviceToken }, { enabled: ready });
  const scenariosQ = trpc.tutor.scenarios.useQuery();

  const stats = statsQ.data;
  const scenarios = scenariosQ.data ?? [];

  return (
    <Layout>
      {/* Hero */}
      <section className="pt-10 pb-8">
        <p className="text-xs font-mono uppercase tracking-[0.25em] text-jade-400">Voice-first Cantonese coach</p>
        <h1 className="mt-3 text-4xl sm:text-5xl font-semibold leading-tight">
          Speak English.
          <br />
          <span className="bg-gradient-to-r from-jade-300 to-emerald-400 bg-clip-text text-transparent">
            Answer in Cantonese.
          </span>
        </h1>
        <p className="mt-4 max-w-xl text-sm text-zinc-400">
          Live roleplay in real Hong Kong situations, instant Jyutping and tone feedback, and a
          phrasebook that reviews itself with spaced repetition.
        </p>
        {!speechSupported && (
          <div className="mt-4 flex items-center gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200 max-w-xl">
            <MicOff className="h-4 w-4 shrink-0" />
            Speech recognition needs Chrome or Edge. You can still type — voice will activate in a supported browser.
          </div>
        )}
      </section>

      {/* Stats */}
      <section className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {[
          { icon: Flame, label: "Day streak", value: stats?.streak ?? "–" },
          { icon: Clock3, label: "Speaking minutes", value: stats ? Math.round(stats.speakingSeconds / 60) : "–" },
          { icon: BookMarked, label: "Phrases saved", value: stats?.phrasesTotal ?? "–" },
          { icon: RotateCcw, label: "Due for review", value: stats?.dueToday ?? "–", accent: (stats?.dueToday ?? 0) > 0 },
        ].map((s) => (
          <div key={s.label} className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
            <s.icon className={cn("h-4 w-4", s.accent ? "text-amber-300" : "text-jade-300")} />
            <p className="mt-2 text-2xl font-semibold tabular-nums">{s.value}</p>
            <p className="text-[11px] text-zinc-500">{s.label}</p>
          </div>
        ))}
      </section>

      {/* Today's plan */}
      {stats && scenarios.length > 0 && (
        <section className="mt-6 rounded-xl border border-white/5 bg-white/[0.03] p-4">
          <p className="text-xs font-mono uppercase tracking-widest text-zinc-500">Today's plan · {stats.dailyGoalMinutes} min goal</p>
          <div className="mt-3 grid gap-2 sm:grid-cols-3">
            <Link
              to="/review"
              className="rounded-lg border border-white/5 bg-black/20 p-3 hover:border-amber-400/30 transition-colors"
            >
              <p className="text-sm font-medium">1. Review {stats.dueToday > 0 ? `(${stats.dueToday} due)` : ""}</p>
              <p className="text-[11px] text-zinc-500">~3 min · spaced repetition</p>
            </Link>
            {(() => {
              const next = scenarios.find((s) => (stats.scenarioCompletion?.[s.id] ?? 0) < 1);
              return next ? (
                <Link
                  to={`/chat/${next.id}`}
                  className="rounded-lg border border-white/5 bg-black/20 p-3 hover:border-jade-400/30 transition-colors"
                >
                  <p className="text-sm font-medium">2. Roleplay: {next.title}</p>
                  <p className="text-[11px] text-zinc-500">~{next.minutes} min · live conversation</p>
                </Link>
              ) : (
                <Link to="/chat/free-talk" className="rounded-lg border border-white/5 bg-black/20 p-3 hover:border-jade-400/30 transition-colors">
                  <p className="text-sm font-medium">2. Free talk 💬</p>
                  <p className="text-[11px] text-zinc-500">All scenarios done — open practice</p>
                </Link>
              );
            })()}
            <Link
              to="/drill/cha-chaan-teng"
              className="rounded-lg border border-white/5 bg-black/20 p-3 hover:border-jade-400/30 transition-colors"
            >
              <p className="text-sm font-medium">3. Tone drill</p>
              <p className="text-[11px] text-zinc-500">~4 min · pronunciation focus</p>
            </Link>
          </div>
        </section>
      )}

      {(stats?.dueToday ?? 0) > 0 && (
        <Link
          to="/review"
          className="mt-4 flex items-center justify-between rounded-xl border border-amber-400/30 bg-gradient-to-r from-amber-500/15 to-transparent px-4 py-3 hover:border-amber-400/50 transition-colors"
        >
          <div className="flex items-center gap-3">
            <RotateCcw className="h-5 w-5 text-amber-300" />
            <div>
              <p className="text-sm font-medium">{stats!.dueToday} phrase{stats!.dueToday > 1 ? "s" : ""} due for review</p>
              <p className="text-xs text-zinc-400">Keep your streak — a 3-minute review locks them in.</p>
            </div>
          </div>
          <ChevronRight className="h-4 w-4 text-zinc-500" />
        </Link>
      )}

      {/* Scenarios */}
      <section className="mt-10">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-lg font-semibold">Scenario curriculum</h2>
            <p className="text-xs text-zinc-500">Seven real Hong Kong situations · voice roleplay + pronunciation drills</p>
          </div>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-2">
          {scenarios.map((sc) => {
            const pct = Math.round((stats?.scenarioCompletion?.[sc.id] ?? 0) * 100);
            return (
              <div
                key={sc.id}
                className={cn(
                  "group rounded-xl border border-white/5 bg-gradient-to-br p-4 transition-colors hover:border-jade-400/30",
                  sc.color,
                )}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-3">
                    <span className="text-2xl">{sc.icon}</span>
                    <div>
                      <p className="font-medium leading-tight">{sc.title}</p>
                      <p className="text-xs text-zinc-400">{sc.subtitle}</p>
                    </div>
                  </div>
                  <span className="rounded-full bg-black/30 px-2 py-0.5 text-[10px] font-mono text-zinc-400">
                    ~{sc.minutes} min
                  </span>
                </div>
                <div className="mt-3 h-1 overflow-hidden rounded-full bg-black/30">
                  <div className="h-full rounded-full bg-jade-400/70 transition-all" style={{ width: `${pct}%` }} />
                </div>
                <div className="mt-3 flex gap-2">
                  <Link
                    to={`/chat/${sc.id}`}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-jade-500/15 py-2 text-xs font-medium text-jade-200 hover:bg-jade-500/25 transition-colors"
                  >
                    <MessageCircle className="h-3.5 w-3.5" /> Roleplay
                  </Link>
                  <Link
                    to={`/drill/${sc.id}`}
                    className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-white/5 py-2 text-xs font-medium text-zinc-300 hover:bg-white/10 transition-colors"
                  >
                    <Mic className="h-3.5 w-3.5" /> Pronunciation drill
                  </Link>
                </div>
              </div>
            );
          })}
        </div>
      </section>

      {/* Learning quality */}
      <section className="mt-10 grid gap-3 sm:grid-cols-3">
        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
          <div className="flex items-center gap-2 text-zinc-400">
            <TrendingUp className="h-4 w-4 text-jade-300" />
            <p className="text-xs">Avg pronunciation</p>
          </div>
          <p className="mt-2 text-xl font-semibold">{stats?.avgPronunciation != null ? `${stats.avgPronunciation}/100` : "–"}</p>
        </div>
        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
          <div className="flex items-center gap-2 text-zinc-400">
            <BookMarked className="h-4 w-4 text-jade-300" />
            <p className="text-xs">Phrases mastered (21d+)</p>
          </div>
          <p className="mt-2 text-xl font-semibold">{stats?.phrasesMastered ?? "–"}</p>
        </div>
        <div className="rounded-xl border border-white/5 bg-white/[0.03] p-4">
          <div className="flex items-center gap-2 text-zinc-400">
            <RotateCcw className="h-4 w-4 text-jade-300" />
            <p className="text-xs">Review retention</p>
          </div>
          <p className="mt-2 text-xl font-semibold">{stats?.retention != null ? `${stats.retention}%` : "–"}</p>
        </div>
      </section>
    </Layout>
  );
}
