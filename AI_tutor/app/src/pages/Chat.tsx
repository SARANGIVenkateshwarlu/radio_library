import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router";
import {
  Mic,
  Square,
  Send,
  ArrowLeft,
  Sparkles,
  AlertTriangle,
  BookmarkCheck,
  XCircle,
  Flag,
} from "lucide-react";
import { trpc } from "@/providers/trpc";
import { getDeviceToken } from "@/lib/profile";
import { Layout } from "@/components/Layout";
import { CantoneseLine } from "@/components/CantoneseLine";
import { useCantoneseTTS, useSpeechRecognition } from "@/hooks/useSpeech";
import { cn } from "@/lib/utils";
import type { TutorTurnResult, SessionSummary, AiErrorKind } from "@contracts/types";

interface ChatMsg {
  role: "user" | "tutor";
  userText?: string;
  userLang?: "en" | "yue";
  tutor?: TutorTurnResult;
  opening?: boolean;
}

const AI_ERROR_COPY: Record<Exclude<AiErrorKind, null>, string> = {
  quota: "AI quota exhausted — switched to the built-in curriculum coach. The site owner can top up to re-enable the AI tutor.",
  misconfigured: "AI is not configured for this site — using the built-in curriculum coach.",
  rejected: "The AI declined that input — continuing with the built-in curriculum coach.",
  transient: "AI is briefly unavailable — this turn was answered by the built-in curriculum coach.",
};

export default function Chat() {
  const { id = "greetings" } = useParams();
  const deviceToken = getDeviceToken();
  const scenariosQ = trpc.tutor.scenarios.useQuery();
  const personasQ = trpc.tutor.personas.useQuery();
  const scenario = scenariosQ.data?.find((s) => s.id === id);
  const personas = personasQ.data ?? [];
  const [personaId, setPersonaId] = useState<string | null>(null);
  const persona = personas.find((p) => p.id === personaId);

  const [sessionId, setSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMsg[]>([]);
  const [mode, setMode] = useState<"en" | "yue">("en");
  const [text, setText] = useState("");
  const [step, setStep] = useState(0);
  const [aiError, setAiError] = useState<AiErrorKind>(null);
  const [summary, setSummary] = useState<SessionSummary | null>(null);
  const [ended, setEnded] = useState(false);
  const startTime = useRef(Date.now());
  const bottomRef = useRef<HTMLDivElement>(null);

  const startSession = trpc.learning.startSession.useMutation();
  const turn = trpc.tutor.turn.useMutation();
  const addTurn = trpc.learning.addTurn.useMutation();
  const savePhrase = trpc.learning.savePhrase.useMutation();
  const summarize = trpc.tutor.summary.useMutation();
  const finish = trpc.learning.finishSession.useMutation();

  const { speak, speaking } = useCantoneseTTS();
  const { listening, transcript, error: micError, start, stop } = useSpeechRecognition(
    mode === "en" ? "en-US" : "yue-HK",
  );

  useEffect(() => {
    startSession.mutate(
      { deviceToken, scenarioId: id, mode: "conversation" },
      { onSuccess: (r) => setSessionId(r.sessionId) },
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  useEffect(() => {
    if (scenario && personaId && persona && messages.length === 0) {
      setMessages([
        {
          role: "tutor",
          opening: true,
          tutor: {
            cantonese_reply: persona.intro.cantonese,
            jyutping: persona.intro.jyutping,
            english_translation: persona.intro.english,
            english_note: `${persona.name} · ${persona.role} — ${persona.personality}`,
            correction: { has_error: false, type: "none", original: "", corrected: "", explanation: "" },
            next_user_prompt: "",
            saved_phrase: { should_save: false, cantonese: "", jyutping: "", english: "" },
            learner_state_update: { fluency: 50, accuracy: 50, confidence: 50, new_weak_areas: [] },
            engine: "scripted",
          },
        },
        {
          role: "tutor",
          opening: true,
          tutor: {
            cantonese_reply: scenario.openingLine.cantonese,
            jyutping: scenario.openingLine.jyutping,
            english_translation: scenario.openingLine.english,
            english_note: "Respond in English or Cantonese — the tutor will adapt.",
            correction: { has_error: false, type: "none", original: "", corrected: "", explanation: "" },
            next_user_prompt: scenario.scriptLength > 0 ? "Reply to your partner to begin." : "",
            saved_phrase: { should_save: false, cantonese: "", jyutping: "", english: "" },
            learner_state_update: { fluency: 50, accuracy: 50, confidence: 50, new_weak_areas: [] },
            engine: "scripted",
          },
        },
      ]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scenario?.id, personaId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, turn.isPending]);

  const busy = turn.isPending;

  const history = useMemo(
    () =>
      messages.slice(-12).map((m) =>
        m.role === "user"
          ? { role: "user" as const, content: m.userText ?? "" }
          : { role: "assistant" as const, content: m.tutor?.cantonese_reply ?? "" },
      ),
    [messages],
  );

  function send(userText: string, langOverride?: "en" | "yue") {
    const lang = langOverride ?? mode;
    const clean = userText.trim();
    if (!clean || busy) return;
    setText("");
    const userMsg: ChatMsg = { role: "user", userText: clean, userLang: lang };
    setMessages((m) => [...m, userMsg]);
    turn.mutate(
      {
        scenarioId: id,
        level: "beginner",
        userText: clean,
        userLang: lang,
        personaId: personaId ?? "wing",
        stepIndex: step,
        history,
      },
      {
        onSuccess: ({ result, nextStep, aiError: err }) => {
          setStep(nextStep);
          setAiError(err);
          setMessages((m) => [...m, { role: "tutor", tutor: result }]);
          speak(result.cantonese_reply.replace(/^你可以咁講：/, ""), 1.0);
          if (sessionId) {
            addTurn.mutate({
              deviceToken,
              sessionId,
              userText: clean,
              userLang: mode,
              tutorCantonese: result.cantonese_reply,
              tutorJyutping: result.jyutping,
              tutorEnglish: result.english_translation,
              correctionJson: JSON.stringify(result.correction),
            });
          }
          if (result.saved_phrase.should_save && result.saved_phrase.cantonese) {
            savePhrase.mutate({
              deviceToken,
              cantonese: result.saved_phrase.cantonese,
              jyutping: result.saved_phrase.jyutping,
              english: result.saved_phrase.english,
              scenarioId: id,
              source: "saved",
            });
          }
        },
      },
    );
  }

  function endSession() {
    const durationSeconds = Math.round((Date.now() - startTime.current) / 1000);
    const userTurns = messages.filter((m) => m.role === "user");
    const corrections = messages
      .map((m) => m.tutor?.correction)
      .filter((c) => c?.has_error)
      .map((c) => `${c!.original} → ${c!.corrected}`);
    const saved = messages
      .filter((m) => m.tutor?.saved_phrase.should_save)
      .map((m) => m.tutor!.saved_phrase.cantonese);
    summarize.mutate(
      {
        scenarioId: id,
        transcript: messages
          .map((m) => (m.role === "user" ? `Learner: ${m.userText}` : `Tutor: ${m.tutor?.english_translation}`))
          .join("\n"),
        scores: [],
        errors: corrections,
        savedPhrases: saved,
      },
      {
        onSuccess: ({ result }) => setSummary(result),
        onSettled: () => {
          setEnded(true);
          if (sessionId) {
            finish.mutate({ deviceToken, sessionId, durationSeconds, summaryJson: undefined });
          }
        },
      },
    );
    void userTurns;
  }

  if (!scenario) {
    return (
      <Layout>
        <div className="pt-16 text-center text-sm text-zinc-500">Loading scenario…</div>
      </Layout>
    );
  }

  // Persona picker — Praktika-style: choose who teaches you before the lesson starts.
  if (!personaId) {
    return (
      <Layout>
        <div className="mx-auto max-w-2xl pt-10">
          <Link to="/" className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300">
            <ArrowLeft className="h-3.5 w-3.5" /> Scenarios
          </Link>
          <h1 className="mt-6 text-2xl font-semibold">Choose your tutor</h1>
          <p className="mt-1 text-sm text-zinc-400">
            {scenario.icon} {scenario.title} — each persona has their own pace and personality.
          </p>
          <div className="mt-6 space-y-3">
            {personas.map((p) => (
              <button
                key={p.id}
                onClick={() => setPersonaId(p.id)}
                className="flex w-full items-center gap-4 rounded-2xl border border-white/5 bg-white/[0.03] p-4 text-left transition-colors hover:border-jade-400/40"
              >
                <img
                  src={p.avatarImg}
                  alt={p.name}
                  className="h-20 w-20 shrink-0 rounded-2xl border border-white/10 object-cover"
                />
                <div className="flex-1">
                  <p className="font-medium">
                    {p.name} <span className="text-jade-300">{p.cantoneseName}</span>
                    <span className="ml-2 rounded-full bg-white/5 px-2 py-0.5 text-[10px] text-zinc-400">{p.role}</span>
                  </p>
                  <p className="mt-0.5 text-xs text-zinc-400">{p.personality}</p>
                  <p className="mt-1.5 text-sm text-zinc-300">“{p.intro.cantonese}”</p>
                  <p className="text-[11px] font-mono text-jade-300/70">{p.intro.jyutping}</p>
                </div>
              </button>
            ))}
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="pt-6">
        <div className="flex items-center justify-between">
          <Link to="/" className="flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-300">
            <ArrowLeft className="h-3.5 w-3.5" /> Scenarios
          </Link>
          <div className="flex items-center gap-2 text-center">
            {persona && (
              <img
                src={persona.avatarImg}
                alt={persona.name}
                className="h-9 w-9 rounded-full border border-jade-400/30 object-cover"
              />
            )}
            <div>
              <p className="text-sm font-semibold">
                {scenario.icon} {scenario.title} · {persona?.cantoneseName}
              </p>
              <p className="text-[11px] text-zinc-500">{scenario.setting}</p>
            </div>
          </div>
          <button
            onClick={endSession}
            disabled={ended || summarize.isPending}
            className="flex items-center gap-1.5 rounded-full border border-white/10 px-3 py-1.5 text-xs text-zinc-300 hover:border-jade-400/40 disabled:opacity-40"
          >
            <Flag className="h-3.5 w-3.5" /> End & summarize
          </button>
        </div>

        {aiError && (
          <div className="mt-4 flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-500/10 px-3 py-2 text-xs text-amber-200">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" />
            {AI_ERROR_COPY[aiError]}
          </div>
        )}

        {/* Messages */}
        <div className="mt-6 space-y-5">
          {messages.map((m, i) =>
            m.role === "user" ? (
              <div key={i} className="flex justify-end">
                <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-jade-500/20 px-4 py-2.5">
                  <p className="text-sm">{m.userText}</p>
                  <p className="mt-0.5 text-[10px] text-jade-300/70 font-mono uppercase">
                    {m.userLang === "en" ? "English" : "Cantonese"}
                  </p>
                </div>
              </div>
            ) : (
              <div key={i} className="flex justify-start items-start gap-2.5">
                {persona && (
                  <img
                    src={persona.avatarImg}
                    alt={persona.name}
                    className={cn(
                      "mt-1 h-9 w-9 shrink-0 rounded-full border object-cover transition-shadow",
                      speaking ? "border-jade-400 shadow-[0_0_14px_rgba(45,212,191,0.5)]" : "border-white/10",
                    )}
                  />
                )}
                <div className="max-w-[85%] rounded-2xl rounded-bl-sm border border-white/5 bg-white/[0.04] px-4 py-3 space-y-2">
                  <CantoneseLine
                    cantonese={m.tutor!.cantonese_reply}
                    jyutping={m.tutor!.jyutping}
                    english={m.tutor!.english_translation}
                  />
                  {m.tutor!.english_note && (
                    <p className="text-xs text-zinc-400 border-l-2 border-jade-500/40 pl-2">{m.tutor!.english_note}</p>
                  )}
                  {m.tutor!.correction.has_error && (
                    <div className="rounded-lg border border-rose-400/20 bg-rose-500/10 p-2.5 text-xs space-y-1">
                      <p className="flex items-center gap-1 font-medium text-rose-200">
                        <XCircle className="h-3.5 w-3.5" /> {m.tutor!.correction.type} correction
                      </p>
                      <p className="text-zinc-300">
                        <span className="line-through opacity-60">{m.tutor!.correction.original}</span>{" "}
                        → <span className="text-jade-300">{m.tutor!.correction.corrected}</span>
                      </p>
                      <p className="text-zinc-400">{m.tutor!.correction.explanation}</p>
                      <button
                        onClick={() => {
                          setMode("yue");
                          start((t) => send(t, "yue"));
                        }}
                        disabled={busy || listening}
                        className="mt-1 flex items-center gap-1.5 rounded-lg bg-rose-500/20 px-2.5 py-1.5 text-[11px] font-medium text-rose-200 hover:bg-rose-500/30 disabled:opacity-40"
                      >
                        <Mic className="h-3 w-3" /> Try again — say: {m.tutor!.correction.corrected}
                      </button>
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    {m.tutor!.engine === "ai" ? (
                      <span className="flex items-center gap-1 text-[10px] font-mono text-jade-400/80">
                        <Sparkles className="h-3 w-3" /> AI tutor
                      </span>
                    ) : (
                      <span className="text-[10px] font-mono text-zinc-500">curriculum coach</span>
                    )}
                    {m.tutor!.saved_phrase.should_save && (
                      <span className="flex items-center gap-1 text-[10px] font-mono text-amber-300/90">
                        <BookmarkCheck className="h-3 w-3" /> saved to phrasebook
                      </span>
                    )}
                  </div>
                </div>
              </div>
            ),
          )}
          {busy && (
            <div className="flex justify-start">
              <div className="rounded-2xl border border-white/5 bg-white/[0.04] px-4 py-3 text-xs text-zinc-500">
                Tutor is thinking…
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>

        {/* Next prompt hint */}
        {messages.length > 0 && messages[messages.length - 1].role === "tutor" && !ended && (
          <div className="mt-4 rounded-lg border border-white/5 bg-white/[0.03] px-3 py-2 text-xs text-zinc-400">
            💡 Try to say: {messages[messages.length - 1].tutor!.next_user_prompt || "…"}
          </div>
        )}

        {/* Input bar */}
        <div className="sticky bottom-4 mt-6">
          <div className="rounded-2xl border border-white/10 bg-[#10161d]/95 p-3 shadow-2xl backdrop-blur">
            <div className="mb-2 flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase text-zinc-500">I speak:</span>
              {(["en", "yue"] as const).map((m) => (
                <button
                  key={m}
                  onClick={() => setMode(m)}
                  className={cn(
                    "rounded-full px-3 py-1 text-xs transition-colors",
                    mode === m ? "bg-jade-500/20 text-jade-200" : "text-zinc-500 hover:text-zinc-300",
                  )}
                >
                  {m === "en" ? "English" : "廣東話"}
                </button>
              ))}
              <span className="ml-auto text-[10px] text-zinc-600">
                {mode === "en" ? "tutor converts & replies in Cantonese" : "tutor corrects your Cantonese"}
              </span>
            </div>
            {listening && (
              <p className="mb-2 text-xs text-jade-300 animate-pulse">
                Listening… {transcript && <span className="text-zinc-300">{transcript}</span>}
              </p>
            )}
            {micError && <p className="mb-2 text-xs text-rose-300">{micError}</p>}
            <div className="flex items-center gap-2">
              <button
                onClick={() => (listening ? stop() : start((t) => send(t)))}
                disabled={busy}
                className={cn(
                  "flex h-11 w-11 shrink-0 items-center justify-center rounded-full transition-all",
                  listening
                    ? "bg-rose-500 text-white shadow-[0_0_20px_rgba(244,63,94,0.4)]"
                    : "bg-jade-500 text-black hover:bg-jade-400",
                )}
              >
                {listening ? <Square className="h-4 w-4" /> : <Mic className="h-5 w-5" />}
              </button>
              <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && send(text)}
                placeholder={mode === "en" ? "…or type in English" : "…或者用廣東話打字"}
                className="h-11 flex-1 rounded-xl border border-white/10 bg-black/30 px-3 text-sm outline-none focus:border-jade-400/50"
              />
              <button
                onClick={() => send(text)}
                disabled={busy || !text.trim()}
                className="flex h-11 w-11 items-center justify-center rounded-full bg-white/10 text-zinc-200 hover:bg-white/20 disabled:opacity-40"
              >
                <Send className="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Summary modal */}
      {summary && (
        <div className="fixed inset-0 z-30 flex items-center justify-center bg-black/70 p-4" onClick={() => setSummary(null)}>
          <div
            className="max-h-[80vh] w-full max-w-lg overflow-y-auto rounded-2xl border border-white/10 bg-[#10161d] p-6"
            onClick={(e) => e.stopPropagation()}
          >
            <h3 className="text-lg font-semibold">Session summary</h3>
            <p className="mt-2 text-sm text-zinc-300">{summary.overall_performance}</p>
            {summary.strengths.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-mono uppercase text-jade-300">Strengths</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-zinc-300">
                  {summary.strengths.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {summary.priority_improvements.length > 0 && (
              <div className="mt-4">
                <p className="text-xs font-mono uppercase text-amber-300">Focus next</p>
                <ul className="mt-1 list-disc space-y-1 pl-5 text-sm text-zinc-300">
                  {summary.priority_improvements.map((s, i) => (
                    <li key={i}>{s}</li>
                  ))}
                </ul>
              </div>
            )}
            {summary.recommended_next_scenario && (
              <p className="mt-4 text-sm text-zinc-400">
                Next up: <span className="text-jade-300">{summary.recommended_next_scenario}</span>
              </p>
            )}
            <p className="mt-4 border-t border-white/10 pt-3 text-sm text-zinc-400">{summary.encouragement}</p>
            <div className="mt-5 flex gap-2">
              <Link
                to="/review"
                className="flex-1 rounded-lg bg-jade-500/20 py-2 text-center text-sm text-jade-200 hover:bg-jade-500/30"
              >
                Review phrases
              </Link>
              <Link
                to="/"
                className="flex-1 rounded-lg bg-white/10 py-2 text-center text-sm text-zinc-200 hover:bg-white/15"
              >
                Back home
              </Link>
            </div>
          </div>
        </div>
      )}
    </Layout>
  );
}
