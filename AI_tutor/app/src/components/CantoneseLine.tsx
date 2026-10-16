import { useState } from "react";
import { Volume2, Loader2 } from "lucide-react";
import { useCantoneseTTS } from "@/hooks/useSpeech";
import { cn } from "@/lib/utils";

/** Split Jyutping into syllables, ignoring punctuation. */
export function splitJyutping(jyutping: string): string[] {
  return jyutping.trim().split(/\s+/).filter(Boolean);
}

/**
 * Displays Cantonese text with Jyutping under each syllable (ruby-style),
 * plus playback at 1.0× / 0.75× / 0.5×.
 */
export function CantoneseLine({
  cantonese,
  jyutping,
  english,
  size = "md",
  showPlayback = true,
  autoSpeak = false,
}: {
  cantonese: string;
  jyutping: string;
  english?: string;
  size?: "sm" | "md" | "lg";
  showPlayback?: boolean;
  autoSpeak?: boolean;
}) {
  const { speak, speaking, supported } = useCantoneseTTS();
  const [rate, setRate] = useState(1.0);
  const chars = [...cantonese];
  const syllables = splitJyutping(jyutping);

  // Align characters to syllables: Han chars consume a syllable; latin words consume one; punctuation gets none.
  const cells: { char: string; jyut?: string }[] = [];
  let si = 0;
  for (const ch of chars) {
    if (/[㐀-鿿]/.test(ch)) {
      cells.push({ char: ch, jyut: syllables[si] });
      si++;
    } else if (/[A-Za-z0-9]/.test(ch)) {
      // group contiguous latin chars
      cells.push({ char: ch, jyut: undefined });
    } else {
      cells.push({ char: ch, jyut: undefined });
      // punctuation in jyutping string (e.g. "!" ",") consumes a slot if present
      if (syllables[si] && /^[\p{P}\p{S}]/u.test(syllables[si])) si++;
    }
  }

  if (autoSpeak && supported) {
    // fire once on mount via microtask guard
    queueMicrotask(() => speak(cantonese, 1.0));
  }

  const charSize = size === "lg" ? "text-3xl" : size === "sm" ? "text-base" : "text-xl";
  const jyutSize = size === "lg" ? "text-xs" : "text-[10px]";

  return (
    <div className="space-y-1.5">
      <div className={cn("flex flex-wrap items-end gap-x-1 gap-y-2", charSize)}>
        {cells.map((c, i) =>
          c.jyut !== undefined ? (
            <span key={i} className="inline-flex flex-col items-center leading-none">
              <span className="font-medium tracking-wide">{c.char}</span>
              <span className={cn("mt-1 text-jade-300/90 font-mono", jyutSize)}>{c.jyut}</span>
            </span>
          ) : (
            <span key={i} className="inline-flex flex-col items-center leading-none">
              <span className="tracking-wide opacity-90">{c.char}</span>
              <span className={cn("mt-1 select-none", jyutSize)}>&nbsp;</span>
            </span>
          ),
        )}
      </div>
      {english && <p className="text-sm text-zinc-400">{english}</p>}
      {showPlayback && supported && (
        <div className="flex items-center gap-2 pt-1">
          <button
            onClick={() => speak(cantonese, rate)}
            className="inline-flex h-7 w-7 items-center justify-center rounded-full bg-jade-500/15 text-jade-300 hover:bg-jade-500/25 transition-colors"
            title="Play"
          >
            {speaking ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Volume2 className="h-3.5 w-3.5" />}
          </button>
          {[1.0, 0.75, 0.5].map((r) => (
            <button
              key={r}
              onClick={() => {
                setRate(r);
                speak(cantonese, r);
              }}
              className={cn(
                "rounded-full px-2 py-0.5 text-[11px] font-mono border transition-colors",
                rate === r
                  ? "border-jade-400/50 bg-jade-500/15 text-jade-200"
                  : "border-zinc-700 text-zinc-400 hover:border-zinc-500",
              )}
            >
              {r}×
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
