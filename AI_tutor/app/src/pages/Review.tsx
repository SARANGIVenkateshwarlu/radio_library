import { useState } from "react";
import { Eye, Mic, Square, RotateCcw, PartyPopper } from "lucide-react";
import { trpc } from "@/providers/trpc";
import { getDeviceToken } from "@/lib/profile";
import { Layout } from "@/components/Layout";
import { CantoneseLine } from "@/components/CantoneseLine";
import { useCantoneseTTS, useSpeechRecognition, speechSupported } from "@/hooks/useSpeech";
import { cn } from "@/lib/utils";

const QUALITY = [
  { q: 1, label: "Again", cls: "bg-rose-500/20 text-rose-200 hover:bg-rose-500/30" },
  { q: 3, label: "Hard", cls: "bg-amber-500/20 text-amber-200 hover:bg-amber-500/30" },
  { q: 4, label: "Good", cls: "bg-jade-500/20 text-jade-200 hover:bg-jade-500/30" },
  { q: 5, label: "Easy", cls: "bg-emerald-500/20 text-emerald-200 hover:bg-emerald-500/30" },
];

export default function Review() {
  const deviceToken = getDeviceToken();
  const dueQ = trpc.learning.duePhrases.useQuery({ deviceToken, limit: 20 });
  const review = trpc.learning.reviewPhrase.useMutation();
  const scoreM = trpc.tutor.pronunciation.useMutation();

  const [idx, setIdx] = useState(0);
  const [revealed, setRevealed] = useState(false);
  const [suggestedQ, setSuggestedQ] = useState<number | null>(null);
  const [heard, setHeard] = useState("");

  const { speak } = useCantoneseTTS();
  const { listening, transcript, start, stop } = useSpeechRecognition("yue-HK", 2500);

  const queue = dueQ.data ?? [];
  const current = queue[idx];

  function grade(q: number) {
    if (!current) return;
    review.mutate(
      { deviceToken, phraseId: current.id, quality: q, score: suggestedQ != null ? undefined : undefined },
      {
        onSuccess: () => {
          setRevealed(false);
          setSuggestedQ(null);
          setHeard("");
          setIdx((i) => i + 1);
        },
      },
    );
  }

  function checkPronunciation(text: string) {
    if (!current) return;
    setHeard(text);
    scoreM.mutate(
      {
        targetCantonese: current.cantonese,
        targetJyutping: current.jyutping,
        recognizedText: text,
        level: "beginner",
      },
      {
        onSuccess: ({ result }) => {
          setRevealed(true);
          const s = result.overall_score;
          setSuggestedQ(s >= 90 ? 5 : s >= 78 ? 4 : s >= 65 ? 3 : 1);
          review.mutate({ deviceToken, phraseId: current.id, quality: s >= 65 ? 3 : 1, score: s });
        },
      },
    );
  }

  return (
    <Layout>
      <div className="mx-auto max-w-2xl pt-8">
        <div className="flex items-center gap-3">
          <RotateCcw className="h-5 w-5 text-jade-300" />
          <div>
            <h1 className="text-xl font-semibold">Spaced-repetition review</h1>
            <p className="text-xs text-zinc-500">SM-2 scheduling — weak phrases return sooner, strong ones stretch out.</p>
          </div>
        </div>

        {dueQ.isLoading && <p className="mt-10 text-center text-sm text-zinc-500">Loading review queue…</p>}

        {!dueQ.isLoading && (queue.length === 0 || idx >= queue.length) && (
          <div className="mt-10 rounded-2xl border border-jade-400/20 bg-jade-500/5 p-8 text-center">
            <PartyPopper className="mx-auto h-8 w-8 text-jade-300" />
            <p className="mt-3 font-medium">{queue.length === 0 ? "Nothing due right now" : "Review queue cleared!"}</p>
            <p className="mt-1 text-sm text-zinc-400">
              {queue.length === 0
                ? "Practice a scenario or drill — corrected and bookmarked phrases land here automatically."
                : "Come back later — the scheduler will bring phrases back right before you forget them."}
            </p>
          </div>
        )}

        {current && idx < queue.length && (
          <div className="mt-6">
            <p className="text-center text-xs font-mono text-zinc-500">
              {idx + 1} / {queue.length} · due since {new Date(current.dueAt).toLocaleDateString()}
            </p>
            <div className="mt-3 rounded-2xl border border-white/5 bg-white/[0.03] p-6 text-center">
              <p className="text-lg text-zinc-200">{current.english}</p>
              <button
                onClick={() => speak(current.cantonese, 1.0)}
                className="mt-2 rounded-full bg-jade-500/15 px-4 py-1.5 text-xs text-jade-200 hover:bg-jade-500/25"
              >
                ▶ Hear it
              </button>

              {revealed ? (
                <div className="mt-5 text-left">
                  <CantoneseLine cantonese={current.cantonese} jyutping={current.jyutping} size="lg" showPlayback={false} />
                  {heard && (
                    <p className="mt-3 text-xs text-zinc-500">
                      You said: <span className="text-zinc-300">{heard}</span>
                      {suggestedQ != null && (
                        <span className="ml-2 text-jade-300">
                          (suggested: {QUALITY.find((x) => x.q === suggestedQ)?.label})
                        </span>
                      )}
                    </p>
                  )}
                </div>
              ) : (
                <button
                  onClick={() => setRevealed(true)}
                  className="mt-5 flex items-center gap-1.5 mx-auto rounded-lg bg-white/5 px-4 py-2 text-xs text-zinc-300 hover:bg-white/10"
                >
                  <Eye className="h-3.5 w-3.5" /> Reveal Cantonese
                </button>
              )}

              <div className="mt-6 border-t border-white/5 pt-4">
                {speechSupported && (
                  <button
                    onClick={() => (listening ? stop() : start((t) => checkPronunciation(t)))}
                    disabled={scoreM.isPending}
                    className={cn(
                      "mx-auto flex h-14 w-14 items-center justify-center rounded-full transition-all",
                      listening ? "bg-rose-500 text-white" : "bg-jade-500 text-black hover:bg-jade-400",
                    )}
                  >
                    {listening ? <Square className="h-4 w-4" /> : <Mic className="h-6 w-6" />}
                  </button>
                )}
                <p className="mt-2 text-[11px] text-zinc-500">
                  {listening ? `Listening… ${transcript}` : "Say it aloud to auto-grade, or grade yourself below."}
                </p>
                {revealed && (
                  <div className="mt-4 flex justify-center gap-2">
                    {QUALITY.map((b) => (
                      <button
                        key={b.q}
                        onClick={() => grade(b.q)}
                        className={cn("rounded-lg px-4 py-2 text-sm font-medium transition-colors", b.cls)}
                      >
                        {b.label}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
