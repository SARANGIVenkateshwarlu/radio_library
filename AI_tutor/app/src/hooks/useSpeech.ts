import { useCallback, useEffect, useRef, useState } from "react";


interface SpeechRecognitionLike {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  onresult: ((ev: { results: ArrayLike<ArrayLike<{ transcript: string }> & { isFinal?: boolean }>; resultIndex: number }) => void) | null;
  onerror: ((ev: { error: string }) => void) | null;
  onend: (() => void) | null;
  start: () => void;
  stop: () => void;
  abort: () => void;
}

function getRecognitionCtor(): (new () => SpeechRecognitionLike) | null {
  const w = window as unknown as Record<string, unknown>;
  return (w.SpeechRecognition ?? w.webkitSpeechRecognition ?? null) as
    | (new () => SpeechRecognitionLike)
    | null;
}

export const speechSupported = !!getRecognitionCtor();

/**
 * Browser speech recognition (Web Speech API).
 * lang: "en-US" for English input, "yue-HK" (falls back to zh-HK) for Cantonese.
 * Includes lightweight VAD: auto-stops after `silenceMs` of no results.
 */
export function useSpeechRecognition(lang: "en-US" | "yue-HK", silenceMs = 1600) {
  const [listening, setListening] = useState(false);
  const [transcript, setTranscript] = useState("");
  const [error, setError] = useState<string | null>(null);
  const recogRef = useRef<SpeechRecognitionLike | null>(null);
  const silenceTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const finalRef = useRef("");
  const onFinalRef = useRef<((text: string) => void) | null>(null);

  const stop = useCallback(() => {
    try {
      recogRef.current?.stop();
    } catch {
      /* noop */
    }
  }, []);

  const start = useCallback(
    (onFinal?: (text: string) => void) => {
      const Ctor = getRecognitionCtor();
      if (!Ctor) {
        setError("Speech recognition is not supported in this browser. Try Chrome or Edge.");
        return;
      }
      setError(null);
      setTranscript("");
      finalRef.current = "";
      onFinalRef.current = onFinal ?? null;

      const r = new Ctor();
      r.lang = lang;
      r.continuous = false;
      r.interimResults = true;
      r.maxAlternatives = 1;

      const armSilenceTimer = () => {
        if (silenceTimer.current) clearTimeout(silenceTimer.current);
        silenceTimer.current = setTimeout(() => stop(), silenceMs);
      };

      r.onresult = (ev) => {
        let interim = "";
        for (let i = 0; i < ev.results.length; i++) {
          const res = ev.results[i] as unknown as { 0: { transcript: string }; isFinal: boolean };
          const text = res[0]?.transcript ?? "";
          if (res.isFinal) finalRef.current += text;
          else interim += text;
        }
        const combined = finalRef.current + interim;
        setTranscript(combined);
        armSilenceTimer();
      };
      r.onerror = (ev) => {
        if (ev.error === "not-allowed") setError("Microphone permission denied. Allow mic access and retry.");
        else if (ev.error !== "aborted" && ev.error !== "no-speech") setError(`Recognition error: ${ev.error}`);
      };
      r.onend = () => {
        setListening(false);
        if (silenceTimer.current) clearTimeout(silenceTimer.current);
        const text = finalRef.current.trim();
        if (text && onFinalRef.current) onFinalRef.current(text);
      };

      recogRef.current = r;
      setListening(true);
      try {
        r.start();
      } catch {
        setListening(false);
      }
    },
    [lang, silenceMs, stop],
  );

  useEffect(
    () => () => {
      if (silenceTimer.current) clearTimeout(silenceTimer.current);
      try {
        recogRef.current?.abort();
      } catch {
        /* noop */
      }
    },
    [],
  );

  return { listening, transcript, error, start, stop };
}

/** Cantonese text-to-speech with rate control (1.0 / 0.75 / 0.5). */
export function useCantoneseTTS() {
  const [speaking, setSpeaking] = useState(false);
  const [supported] = useState(typeof speechSynthesis !== "undefined");
  const voiceRef = useRef<SpeechSynthesisVoice | null>(null);

  const pickVoice = useCallback(() => {
    const voices = speechSynthesis.getVoices();
    const exact =
      voices.find((v) => v.lang.toLowerCase() === "zh-hk") ??
      voices.find((v) => /cantonese|hong\s?kong|hiu ?(maan|gaai)|wan ?lung/i.test(v.name)) ??
      voices.find((v) => v.lang.toLowerCase().startsWith("zh") && /hk/i.test(v.lang)) ??
      voices.find((v) => v.lang.toLowerCase().startsWith("zh"));
    voiceRef.current = exact ?? null;
    return exact;
  }, []);

  useEffect(() => {
    if (!supported) return;
    pickVoice();
    speechSynthesis.onvoiceschanged = pickVoice;
    return () => {
      speechSynthesis.onvoiceschanged = null;
    };
  }, [supported, pickVoice]);

  const speak = useCallback(
    (text: string, rate = 1.0, onEnd?: () => void) => {
      if (!supported) return;
      speechSynthesis.cancel();
      const u = new SpeechSynthesisUtterance(text);
      u.lang = "zh-HK";
      const v = voiceRef.current ?? pickVoice();
      if (v) u.voice = v;
      u.rate = rate;
      u.onstart = () => setSpeaking(true);
      u.onend = () => {
        setSpeaking(false);
        onEnd?.();
      };
      u.onerror = () => setSpeaking(false);
      speechSynthesis.speak(u);
    },
    [supported, pickVoice],
  );

  const cancel = useCallback(() => {
    if (!supported) return;
    speechSynthesis.cancel();
    setSpeaking(false);
  }, [supported]);

  return { speak, cancel, speaking, supported, voiceName: voiceRef.current?.name };
}
