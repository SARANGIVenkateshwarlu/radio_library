import { useMemo, useState } from "react";
import { Link, useParams } from "react-router";
import { ArrowLeft, Mic, Square, CheckCircle2, RotateCw, BookmarkPlus, AlertTriangle } from "lucide-react";
import { trpc } from "@/providers/trpc";
import { getDeviceToken } from "@/lib/profile";
import { Layout } from "@/components/Layout";
import { CantoneseLine } from "@/components/CantoneseLine";
import { useSpeechRecognition, speechSupported } from "@/hooks/useSpeech";
import { cn } from "@/lib/utils";
import type { PronunciationResult, PhraseItem } from "@contracts/types";

function ScoreRing({ score }: { score: number }) {
  const r = 26;
  const c = 2 * Math.PI * r;
  const color = score >= 80 ? "#2dd4bf" : score >= 60 ? "#fbbf24" : "#fb7185";
  return (
    <div className="relative h-16 w-16">
      <svg className="h-16 w-16 -rotate-90">
        <circle cx="32" cy="32" r={r} fill="none" stroke="#27272a" strokeWidth="5" />
        <circle
          cx="32" cy="32" r={r} fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={c} strokeDashoffset={c * (1 - score / 100)} strokeLinecap="round"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold tabular-nums">
        {score}
      </span>
    </div>
  );
}

export default function Drill() {
  const { id = "greetings" } = useParams();
  const deviceToken = getDeviceToken();
  const scenariosQ = trpc.tutor.scenarios.useQuery();
  const scenario = scenariosQ.data?.find((s) => s.id === id);

  const queue = useMemo<PhraseItem[]>(
    () => (scenario ? [...scenario.assessmentPhrases, ...scenario.targetPhrases] : []),
    [scenario],
  );
  const [idx, setIdx] = useState(0);
  const [attempts, setAttempts] = useState<number[]>([]);
  const [result, setResult] = useState<PronunciationResult | null>(null);
  const [saved, setSaved] = useState(false);

  const score = trpc.tutor.pronunciation.useMutation();
  const savePhrase = trpc.learning.savePhrase.useMutation();
  const { listening, transcript, error: micError, start, stop } = useSpeechRecognition("yue-HK", 2500);

  const current = queue[idx];
  const improved = attempts.length >= 2 && attempts[attempts.length - 1] > attempts[0];

  function submitAttempt(recognized: string) {
    if (!current) return;
    score.mutate(
      {
        targetCantonese: current.cantonese,
        targetJyutping: current.jyutping,
        recognizedText: recognized,
        level: "beginner",
      },
      {
        onSuccess: ({ result }) => {
          setResult(result);
          setAttempts((a) => [...a, result.overall_score]);
        },
      },
    );
  }

  function next(passedForward = true) {
    setResult(null);
    setAttempts([]);
    setSaved(false);
    if (passedForward) setIdx((i) => Math.min(i + 1, queue.length - 1));
  }

  if (!scenario || !current) {
    return (
      <Layout>
        <div className="pt-16 text-center text-sm text-zinc-500">Loading drill…</div>
      </Layout>
    );
  }

  const done = idx === queue.length - 1 && result?.passed;

  return (
    <Layout>
      <div className="pt-6 max-w-2xl mx-auto">
        <Link to="/" className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300">
          <ArrowLeft className="h-3.5 w-3.5" /> Scenarios
        </Link>
        <div className="mt-4 flex items-center justify-between">
          <div>
            <h1 className="text-lg font-semibold">Pronunciation drill</h1>
            <p className="text-xs text-zinc-500">
              {scenario.icon} {scenario.title}
            </p>
          </div>
          <span className="rounded-full bg-white/5 px-3 py-1 text-xs font-mono text-zinc-400">
            {idx + 1} / {queue.length}
          </span>
        </div>

        <div className="mt-2 h-1 overflow-hidden rounded-full bg-white/5">
          <div
            className="h-full bg-jade-400/70 transition-all"
            style={{ width: `${((idx + (result?.passed ? 1 : 0)) / queue.length) * 100}%` }}
          />
        </div>

        {!speechSupported && (
          <p className="mt-4 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            Voice input needs Chrome or Edge. Open this page there to do drills.
          </p>
        )}

        <div className="mt-6 rounded-2xl border border-white/5 bg-white/[0.03] p-6">
          <CantoneseLine cantonese={current.cantonese} jyutping={current.jyutping} english={current.english} size="lg" />
          {current.note && <p className="mt-3 text-xs text-zinc-500">📌 {current.note}</p>}

          <div className="mt-6 flex items-center gap-4">
            <button
              onClick={() => (listening ? stop() : start((t) => submitAttempt(t)))}
              disabled={score.isPending}
              className={cn(
                "flex h-16 w-16 items-center justify-center rounded-full transition-all",
                listening
                  ? "bg-rose-500 text-white shadow-[0_0_24px_rgba(244,63,94,0.5)]"
                  : "bg-jade-500 text-black hover:bg-jade-400",
              )}
            >
              {listening ? <Square className="h-5 w-5" /> : <Mic className="h-7 w-7" />}
            </button>
            <div className="text-xs text-zinc-500">
              {listening ? (
                <p className="text-jade-300 animate-pulse">Listening… speak the phrase in Cantonese.</p>
              ) : score.isPending ? (
                <p>Scoring your attempt…</p>
              ) : (
                <p>Tap the mic, repeat the phrase aloud. Target: 70+ to pass.</p>
              )}
              {transcript && listening && <p className="mt-1 text-zinc-300">“{transcript}”</p>}
              {micError && <p className="mt-1 text-rose-300">{micError}</p>}
            </div>
          </div>
        </div>

        {result && (
          <div className="mt-4 rounded-2xl border border-white/5 bg-white/[0.03] p-5">
            <div className="flex items-center gap-4">
              <ScoreRing score={result.overall_score} />
              <div>
                <p className={cn("font-medium", result.passed ? "text-jade-300" : "text-amber-300")}>
                  {result.passed ? "Passed!" : "Not quite — try again"}
                </p>
                <p className="mt-0.5 text-xs text-zinc-400">
                  Heard: <span className="text-zinc-200">{result.recognized_as || "（nothing recognized）"}</span>
                </p>
                <p className="mt-1 text-xs text-zinc-500">{result.encouragement}</p>
              </div>
            </div>

            {result.subscores && (
              <div className="mt-4 grid grid-cols-4 gap-2">
                {(
                  [
                    ["Pronunciation", result.subscores.pronunciation],
                    ["Fluency", result.subscores.fluency],
                    ["Completeness", result.subscores.completeness],
                    ["Rhythm", result.subscores.rhythm],
                  ] as const
                ).map(([label, v]) => (
                  <div key={label} className="rounded-lg bg-black/30 p-2 text-center">
                    <p className="text-sm font-semibold tabular-nums">{v}</p>
                    <div className="mt-1 h-1 overflow-hidden rounded-full bg-white/10">
                      <div
                        className={cn("h-full", v >= 80 ? "bg-jade-400" : v >= 60 ? "bg-amber-400" : "bg-rose-400")}
                        style={{ width: `${v}%` }}
                      />
                    </div>
                    <p className="mt-1 text-[9px] uppercase tracking-wide text-zinc-500">{label}</p>
                  </div>
                ))}
              </div>
            )}

            {result.issues.length > 0 && (
              <div className="mt-4 space-y-2">
                {result.issues.map((iss, i) => (
                  <div key={i} className="rounded-lg border border-white/5 bg-black/30 p-3 text-xs">
                    <p className="font-medium text-zinc-200">
                      {iss.syllable} <span className="font-mono text-jade-300">({iss.expected_jyutping})</span>
                      <span className="ml-2 rounded bg-white/5 px-1.5 py-0.5 text-[10px] font-mono uppercase text-zinc-400">
                        {iss.issue_type}
                      </span>
                    </p>
                    <p className="mt-1 text-zinc-400">{iss.feedback}</p>
                  </div>
                ))}
              </div>
            )}
            <p className="mt-3 border-l-2 border-jade-500/40 pl-2 text-xs text-zinc-300">{result.priority_correction}</p>

            <div className="mt-4 flex flex-wrap gap-2">
              <button
                onClick={() => setResult(null)}
                className="flex items-center gap-1.5 rounded-lg bg-jade-500/20 px-3 py-2 text-xs text-jade-200 hover:bg-jade-500/30"
              >
                <RotateCw className="h-3.5 w-3.5" /> Retry
                {attempts.length > 0 && (
                  <span className="font-mono text-zinc-400">
                    ({attempts.join(" → ")})
                  </span>
                )}
              </button>
              <button
                onClick={() => next(true)}
                className="rounded-lg bg-white/10 px-3 py-2 text-xs text-zinc-200 hover:bg-white/15"
              >
                Next phrase
              </button>
              {!saved && (
                <button
                  onClick={() => {
                    savePhrase.mutate(
                      {
                        deviceToken,
                        cantonese: current.cantonese,
                        jyutping: current.jyutping,
                        english: current.english,
                        scenarioId: id,
                        source: "bookmark",
                      },
                      { onSuccess: () => setSaved(true) },
                    );
                  }}
                  className="flex items-center gap-1.5 rounded-lg bg-white/5 px-3 py-2 text-xs text-zinc-300 hover:bg-white/10"
                >
                  <BookmarkPlus className="h-3.5 w-3.5" /> Save to phrasebook
                </button>
              )}
              {saved && (
                <span className="flex items-center gap-1 px-2 text-xs text-jade-300">
                  <CheckCircle2 className="h-3.5 w-3.5" /> Saved
                </span>
              )}
            </div>
            {attempts.length >= 2 && (
              <p className={cn("mt-3 flex items-center gap-1.5 text-xs", improved ? "text-jade-300" : "text-zinc-500")}>
                {improved ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5" /> Improving — {attempts[0]} → {attempts[attempts.length - 1]}
                  </>
                ) : (
                  <>
                    <AlertTriangle className="h-3.5 w-3.5" /> Not improving yet — try the 0.5× playback and shadow each syllable.
                  </>
                )}
              </p>
            )}
          </div>
        )}

        {done && (
          <div className="mt-4 rounded-2xl border border-jade-400/30 bg-jade-500/10 p-5 text-center">
            <p className="font-medium text-jade-200">Drill complete — 好叻呀！</p>
            <div className="mt-3 flex justify-center gap-2">
              <Link to={`/chat/${id}`} className="rounded-lg bg-jade-500/20 px-4 py-2 text-xs text-jade-200">
                Do the roleplay
              </Link>
              <Link to="/review" className="rounded-lg bg-white/10 px-4 py-2 text-xs text-zinc-200">
                Review phrases
              </Link>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
