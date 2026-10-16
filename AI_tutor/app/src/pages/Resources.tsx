import { ExternalLink, FileText, Github, Boxes } from "lucide-react";
import { Layout } from "@/components/Layout";

interface Item {
  title: string;
  meta: string;
  desc: string;
  url: string;
}

const PAPERS: Item[] = [
  {
    title: "Robust Speech Recognition via Large-Scale Weak Supervision (Whisper)",
    meta: "Radford et al., 2022 · OpenAI",
    desc: "The ASR foundation for English input; strong multilingual base that Cantonese fine-tunes build on.",
    url: "https://arxiv.org/abs/2212.04356",
  },
  {
    title: "SenseVoice: Multilingual Speech Understanding with Rich Transcription",
    meta: "An et al., 2024 · Alibaba FunAudioLLM",
    desc: "Fast ASR with explicit Cantonese (yue) support — the top candidate for the Cantonese ASR slot in production.",
    url: "https://arxiv.org/abs/2407.04051",
  },
  {
    title: "CosyVoice 2: Scalable Streaming Speech Synthesis with Large Language Models",
    meta: "Du et al., 2024 · Alibaba FunAudioLLM",
    desc: "Streaming TTS with Cantonese support and low first-chunk latency — fits the sub-2-second voice-loop target.",
    url: "https://arxiv.org/abs/2412.10117",
  },
  {
    title: "Phone Pronunciation Scoring for Speech Assessment (Goodness of Pronunciation)",
    meta: "Witt & Young, 2000 · Computer Speech & Language",
    desc: "The classic GOP formulation behind most computer-assisted pronunciation training (CAPT) scorers.",
    url: "https://doi.org/10.1006/csla.1999.0149",
  },
  {
    title: "A Stochastic Shortest Path Algorithm for Optimizing Spaced Repetition Scheduling (FSRS)",
    meta: "Ye et al., 2022 · ACM KDD",
    desc: "Modern successor to the SM-2 algorithm this MVP ships with; upgrade path when review data accumulates.",
    url: "https://dl.acm.org/doi/10.1145/3534678.3539081",
  },
  {
    title: "Optimizing Second Language Practice with Spaced Repetition (Half-Life Regression)",
    meta: "Settles & Meeder, 2016 · ACL (Duolingo)",
    desc: "Data-driven memory modelling for vocabulary review at scale — directly applicable to the phrasebook SRS.",
    url: "https://aclanthology.org/P16-1174/",
  },
];

const GITHUB: Item[] = [
  {
    title: "FunAudioLLM/SenseVoice",
    meta: "ASR · Cantonese (yue) supported",
    desc: "Production candidate for Cantonese ASR; ONNX export for on-device or server inference.",
    url: "https://github.com/FunAudioLLM/SenseVoice",
  },
  {
    title: "FunAudioLLM/CosyVoice",
    meta: "TTS · streaming, Cantonese",
    desc: "Cantonese-capable streaming TTS for the tutor voice; supports zero-shot voice cloning for a native-sounding coach.",
    url: "https://github.com/FunAudioLLM/CosyVoice",
  },
  {
    title: "SYSTRAN/faster-whisper",
    meta: "ASR · CTranslate2",
    desc: "Whisper re-implementation, ~4× faster with identical accuracy — for the English leg of the voice loop.",
    url: "https://github.com/SYSTRAN/faster-whisper",
  },
  {
    title: "snakers4/silero-vad",
    meta: "VAD · tiny, real-time",
    desc: "Enterprise-grade voice activity detection for barge-in and end-of-speech — replaces the browser silence timer in production.",
    url: "https://github.com/snakers4/silero-vad",
  },
  {
    title: "pycantonese/pycantonese",
    meta: "Jyutping · NLP toolkit",
    desc: "Cantonese NLP: characters↔Jyutping conversion, tone parsing, and access to the HKCanCor corpus for curriculum mining.",
    url: "https://github.com/pycantonese/pycantonese",
  },
  {
    title: "CanCLID/rime-cantonese",
    meta: "Jyutping lexicon",
    desc: "Community-verified Cantonese pronunciation lexicon (Jyutping) — a QA reference to keep generated Jyutping honest.",
    url: "https://github.com/CanCLID/rime-cantonese",
  },
  {
    title: "rany2/edge-tts",
    meta: "TTS · free zh-HK voices",
    desc: "Edge neural voices HiuMaan / HiuGaai / WanLung (zh-HK) — an easy free upgrade from browser speechSynthesis.",
    url: "https://github.com/rany2/edge-tts",
  },
  {
    title: "typangaa/canto-tts",
    meta: "TTS · Jyutping phoneme tokens",
    desc: "Open-source Hong Kong Cantonese TTS driven by Jyutping phoneme tokens, with English code-switching support.",
    url: "https://github.com/typangaa/canto-tts",
  },
  {
    title: "cantonese.ai — STT & TTS APIs",
    meta: "Managed Cantonese speech APIs",
    desc: "Commercial Cantonese-specialized speech recognition and TTS with Jyutping-guided pronunciation control.",
    url: "https://docs.cantonese.ai/text-to-speech",
  },
];

const HF: Item[] = [
  {
    title: "iic/SenseVoiceSmall",
    meta: "ASR model · 234M params",
    desc: "Lightweight SenseVoice checkpoint with yue (Cantonese) language tag support — runs on CPU.",
    url: "https://huggingface.co/iic/SenseVoiceSmall",
  },
  {
    title: "FunAudioLLM/CosyVoice2-0.5B",
    meta: "TTS model · streaming",
    desc: "Streaming speech synthesis checkpoint supporting Cantonese output for the tutor voice.",
    url: "https://huggingface.co/FunAudioLLM/CosyVoice2-0.5B",
  },
  {
    title: "openai/whisper-large-v3-turbo",
    meta: "ASR model · English leg",
    desc: "Near-large-v3 accuracy at ~8× speed — good fit for the sub-2-second English ASR budget.",
    url: "https://huggingface.co/openai/whisper-large-v3-turbo",
  },
  {
    title: "typangaa/canto-tts-nano",
    meta: "TTS model · lightweight",
    desc: "Compact Jyutping-token Cantonese TTS checkpoint — small enough for edge/server deployment without a GPU.",
    url: "https://huggingface.co/typangaa/canto-tts-nano",
  },
  {
    title: "Cantonese ASR fine-tunes (community)",
    meta: "Whisper fine-tunes · search hub",
    desc: "Community Whisper checkpoints fine-tuned on Cantonese speech; evaluate on a curated HK test set before adopting.",
    url: "https://huggingface.co/models?search=cantonese%20whisper",
  },
];

function Section({ icon: Icon, title, items }: { icon: typeof FileText; title: string; items: Item[] }) {
  return (
    <section className="mt-8">
      <div className="flex items-center gap-2">
        <Icon className="h-4 w-4 text-jade-300" />
        <h2 className="font-semibold">{title}</h2>
      </div>
      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        {items.map((it) => (
          <a
            key={it.title}
            href={it.url}
            target="_blank"
            rel="noreferrer"
            className="group rounded-xl border border-white/5 bg-white/[0.03] p-4 transition-colors hover:border-jade-400/30"
          >
            <div className="flex items-start justify-between gap-2">
              <p className="text-sm font-medium leading-snug group-hover:text-jade-200">{it.title}</p>
              <ExternalLink className="h-3.5 w-3.5 shrink-0 text-zinc-600 group-hover:text-jade-300" />
            </div>
            <p className="mt-1 text-[10px] font-mono uppercase tracking-wide text-zinc-500">{it.meta}</p>
            <p className="mt-2 text-xs leading-relaxed text-zinc-400">{it.desc}</p>
          </a>
        ))}
      </div>
    </section>
  );
}

export default function Resources() {
  return (
    <Layout>
      <div className="mx-auto max-w-3xl pt-8">
        <h1 className="text-xl font-semibold">Research & production resources</h1>
        <p className="mt-1 text-sm text-zinc-400">
          The evidence base behind this app's design — and the production upgrade path for each component
          (ASR → LLM tutor → TTS, pronunciation scoring, SRS scheduling).
        </p>

        <div className="mt-5 rounded-xl border border-white/5 bg-white/[0.03] p-4 text-xs text-zinc-400 leading-relaxed">
          <p className="font-medium text-zinc-200">Current prototype stack</p>
          <p className="mt-1">
            Browser Web Speech API (English + Cantonese recognition, zh-HK TTS) · Kimi LLM gateway with the PDR prompt
            pack and a scripted curriculum fallback · SM-2 spaced repetition · tRPC + MySQL persistence. Each box below
            maps to a hardened replacement that keeps this app's interfaces intact.
          </p>
        </div>

        <Section icon={FileText} title="Research papers" items={PAPERS} />
        <Section icon={Github} title="GitHub" items={GITHUB} />
        <Section icon={Boxes} title="Hugging Face models" items={HF} />
      </div>
    </Layout>
  );
}
