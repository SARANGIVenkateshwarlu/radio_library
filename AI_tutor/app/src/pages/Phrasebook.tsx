import { Link } from "react-router";
import { BookMarked, Trash2, RotateCcw } from "lucide-react";
import { trpc } from "@/providers/trpc";
import { getDeviceToken } from "@/lib/profile";
import { Layout } from "@/components/Layout";
import { CantoneseLine } from "@/components/CantoneseLine";
import { cn } from "@/lib/utils";

export default function Phrasebook() {
  const deviceToken = getDeviceToken();
  const listQ = trpc.learning.listPhrases.useQuery({ deviceToken });
  const del = trpc.learning.deletePhrase.useMutation({
    onSuccess: () => listQ.refetch(),
  });

  const items = listQ.data ?? [];
  const now = Date.now();

  return (
    <Layout>
      <div className="mx-auto max-w-3xl pt-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <BookMarked className="h-5 w-5 text-jade-300" />
            <div>
              <h1 className="text-xl font-semibold">Phrasebook</h1>
              <p className="text-xs text-zinc-500">
                {items.length} saved · {items.filter((p) => new Date(p.dueAt).getTime() <= now).length} due now
              </p>
            </div>
          </div>
          <Link
            to="/review"
            className="flex items-center gap-1.5 rounded-lg bg-jade-500/15 px-3 py-2 text-xs text-jade-200 hover:bg-jade-500/25"
          >
            <RotateCcw className="h-3.5 w-3.5" /> Review now
          </Link>
        </div>

        {listQ.isLoading && <p className="mt-10 text-center text-sm text-zinc-500">Loading…</p>}

        {!listQ.isLoading && items.length === 0 && (
          <div className="mt-10 rounded-2xl border border-white/5 bg-white/[0.03] p-8 text-center text-sm text-zinc-400">
            Nothing saved yet. Phrases are auto-saved when the tutor teaches you something new, or bookmark them in drills.
          </div>
        )}

        <div className="mt-5 space-y-3">
          {items.map((p) => {
            const due = new Date(p.dueAt).getTime() <= now;
            const mastered = p.intervalDays >= 21;
            return (
              <div
                key={p.id}
                className={cn(
                  "rounded-xl border p-4",
                  due ? "border-amber-400/25 bg-amber-500/[0.06]" : "border-white/5 bg-white/[0.03]",
                )}
              >
                <div className="flex items-start justify-between gap-3">
                  <CantoneseLine cantonese={p.cantonese} jyutping={p.jyutping} english={p.english} size="sm" />
                  <button
                    onClick={() => del.mutate({ deviceToken, phraseId: p.id })}
                    className="text-zinc-600 hover:text-rose-300 transition-colors"
                    title="Delete"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>
                <div className="mt-2 flex flex-wrap items-center gap-2 text-[10px] font-mono text-zinc-500">
                  <span className="rounded bg-white/5 px-1.5 py-0.5">{p.source}</span>
                  {p.scenarioId && <span className="rounded bg-white/5 px-1.5 py-0.5">{p.scenarioId}</span>}
                  {mastered ? (
                    <span className="rounded bg-jade-500/15 px-1.5 py-0.5 text-jade-300">mastered</span>
                  ) : due ? (
                    <span className="rounded bg-amber-500/15 px-1.5 py-0.5 text-amber-300">due</span>
                  ) : (
                    <span className="rounded bg-white/5 px-1.5 py-0.5">
                      next: {new Date(p.dueAt).toLocaleDateString()} ({p.intervalDays}d)
                    </span>
                  )}
                  {p.lastScore != null && <span>last score {p.lastScore}</span>}
                  {p.lapses > 0 && <span>{p.lapses} lapse{p.lapses > 1 ? "s" : ""}</span>}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </Layout>
  );
}
