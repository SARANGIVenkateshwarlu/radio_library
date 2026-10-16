import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import { listModels } from "./ai-client";

interface NodeLikeProcess {
  env?: Record<string, string | undefined>;
  loadEnvFile?: (path?: string) => void;
}

function readEnv(key: string): string {
  const proc = (globalThis as { process?: NodeLikeProcess }).process;
  let value = proc?.env?.[key];
  if (!value) {
    try {
      proc?.loadEnvFile?.();
      value = proc?.env?.[key];
    } catch {
      /* fall through */
    }
  }
  return value ?? "";
}

type Provider = ReturnType<typeof createOpenAICompatible>;

let cachedProvider: Provider | undefined;
let cachedDefault: string | undefined;

/** Lazily create the gateway provider so .env is loaded before first use. */
export function kimiGw(): Provider {
  if (!cachedProvider) {
    cachedProvider = createOpenAICompatible({
      name: "kimi-gw",
      baseURL: readEnv("KIMI_AGENTGW_BASE_URL"),
      apiKey: readEnv("KIMI_AGENTGW_API_KEY"),
      includeUsage: true,
      supportsStructuredOutputs: true,
    });
  }
  return cachedProvider;
}

/** Resolve the site's default model id at runtime — never hardcode. */
export async function defaultModelId(): Promise<string> {
  if (!cachedDefault) {
    const { defaultModelId } = await listModels();
    cachedDefault = defaultModelId;
  }
  return cachedDefault;
}
