import { spawn } from "node:child_process";
import { createInterface } from "node:readline";

const ZERO_USAGE = Object.freeze({
  input: 0,
  output: 0,
  cacheRead: 0,
  cacheWrite: 0,
  totalTokens: 0,
  cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
});

function cloneUsage() {
  return {
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    totalTokens: 0,
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  };
}

function sanitizeChildEnvironment(extra = {}) {
  const env = { ...process.env, ...extra };
  const exact = new Set([
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "GOOGLE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "SSH_AUTH_SOCK",
  ]);
  for (const key of Object.keys(env)) {
    const upper = key.toUpperCase();
    if (
      exact.has(upper) ||
      upper.endsWith("_API_KEY") ||
      upper.endsWith("_ACCESS_TOKEN") ||
      upper.endsWith("_TOKEN") ||
      upper.endsWith("_SECRET") ||
      upper.endsWith("_PASSWORD") ||
      upper.endsWith("_CREDENTIAL") ||
      upper.endsWith("_CREDENTIALS") ||
      upper.startsWith("OPENAI_") ||
      upper.startsWith("ANTHROPIC_") ||
      upper.startsWith("AWS_") ||
      upper.startsWith("AZURE_") ||
      upper.startsWith("GOOGLE_") ||
      upper.startsWith("HF_") ||
      upper.startsWith("HUGGINGFACE_") ||
      upper.startsWith("HUGGING_FACE_") ||
      upper.startsWith("GITHUB_") ||
      upper.startsWith("GH_") ||
      upper.startsWith("SSH_")
    ) {
      delete env[key];
    }
  }
  return env;
}

function asErrorMessage(model, message, reason = "error") {
  return {
    role: "assistant",
    content: [],
    api: model?.api ?? "lac-model-provider",
    provider: model?.provider ?? "lac-freetoken",
    model: model?.id ?? "unknown",
    usage: cloneUsage(),
    stopReason: reason,
    errorMessage: String(message),
    timestamp: Date.now(),
  };
}

function mapUsage(raw) {
  if (!raw || typeof raw !== "object") return cloneUsage();
  const inputTokens = Number(raw.input_tokens ?? 0);
  const outputTokens = Number(raw.output_tokens ?? 0);
  const cached = Number(raw.cached_input_tokens ?? 0);
  const total = Number(raw.total_tokens ?? inputTokens + outputTokens);
  return {
    input: Math.max(0, inputTokens - cached),
    output: Math.max(0, outputTokens),
    cacheRead: Math.max(0, cached),
    cacheWrite: 0,
    totalTokens: Math.max(0, total),
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0, total: 0 },
  };
}

function mapFinishReason(raw, hasTools) {
  if (raw === "length") return "length";
  if (raw === "tool_calls" || raw === "tool_use" || hasTools) return "toolUse";
  return "stop";
}

function jsonArguments(raw) {
  if (raw === "" || raw == null) return {};
  if (typeof raw === "object") return raw;
  const parsed = JSON.parse(raw);
  if (parsed === null || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("tool-call arguments must decode to a JSON object");
  }
  return parsed;
}

export function createLacModelProviderStreamFn({
  createAssistantMessageEventStream,
  pythonExecutable,
  bridgeScript,
  baseUrl,
  timeoutSeconds = 300,
}) {
  if (typeof createAssistantMessageEventStream !== "function") {
    throw new TypeError("createAssistantMessageEventStream is required");
  }
  if (typeof pythonExecutable !== "string" || !pythonExecutable) throw new TypeError("pythonExecutable is required");
  if (typeof bridgeScript !== "string" || !bridgeScript) throw new TypeError("bridgeScript is required");
  if (typeof baseUrl !== "string" || !baseUrl) throw new TypeError("baseUrl is required");

  return (model, context, options = {}) => {
    const stream = createAssistantMessageEventStream();
    const partial = {
      role: "assistant",
      content: [],
      api: model.api,
      provider: model.provider,
      model: model.id,
      usage: cloneUsage(),
      stopReason: "pending",
      timestamp: Date.now(),
    };

    queueMicrotask(async () => {
      let child;
      let started = false;
      let textIndex = null;
      let thinkingIndex = null;
      let finishReason = null;
      const toolStates = new Map();
      let stderr = "";

      const start = () => {
        if (!started) {
          started = true;
          stream.push({ type: "start", partial });
        }
      };
      const endText = () => {
        if (textIndex !== null) {
          const block = partial.content[textIndex];
          stream.push({ type: "text_end", contentIndex: textIndex, content: block.text, partial });
          textIndex = null;
        }
      };
      const endThinking = () => {
        if (thinkingIndex !== null) {
          const block = partial.content[thinkingIndex];
          stream.push({ type: "thinking_end", contentIndex: thinkingIndex, content: block.thinking, partial });
          thinkingIndex = null;
        }
      };
      const fail = (error, reason = "error") => {
        try {
          if (child && !child.killed) child.kill("SIGTERM");
        } catch {}
        const message = asErrorMessage(model, error instanceof Error ? error.message : error, reason);
        if (started) message.content = partial.content;
        stream.push({ type: "error", reason, error: message });
        stream.end(message);
      };

      try {
        start();
        const requestPayload = {
          model: model.id,
          context,
          options: {
            maxTokens: options.maxTokens ?? Math.min(Number(model.maxTokens || 1024), 2048),
            temperature: options.temperature ?? 0,
            toolChoice: options.toolChoice ?? "auto",
            reasoning: options.reasoning,
            timeoutSeconds,
          },
        };

        child = spawn(pythonExecutable, [bridgeScript], {
          stdio: ["pipe", "pipe", "pipe"],
          env: sanitizeChildEnvironment({ LAC_A003_FREETOKEN_URL: baseUrl }),
        });
        const exitPromise = new Promise((resolve, reject) => {
          child.once("error", reject);
          child.once("close", resolve);
        });
        child.stderr.setEncoding("utf8");
        child.stderr.on("data", (chunk) => {
          stderr += chunk;
          if (stderr.length > 8000) stderr = stderr.slice(-8000);
        });

        let aborted = false;
        const onAbort = () => {
          aborted = true;
          try { child.kill("SIGTERM"); } catch {}
        };
        if (options.signal) {
          if (options.signal.aborted) onAbort();
          else options.signal.addEventListener("abort", onAbort, { once: true });
        }

        child.stdin.end(JSON.stringify(requestPayload));
        const rl = createInterface({ input: child.stdout, crlfDelay: Infinity });
        let providerError = null;

        for await (const line of rl) {
          if (!line.trim()) continue;
          let event;
          try {
            event = JSON.parse(line);
          } catch (error) {
            providerError = new Error(`invalid LAC model-provider bridge event: ${error.message}`);
            break;
          }
          if (event.kind === "error") {
            providerError = new Error(event.message || "LAC ModelProvider failed closed");
            break;
          }
          if (event.kind === "text_delta") {
            endThinking();
            if (textIndex === null) {
              textIndex = partial.content.length;
              partial.content.push({ type: "text", text: "" });
              stream.push({ type: "text_start", contentIndex: textIndex, partial });
            }
            const delta = String(event.value ?? "");
            partial.content[textIndex].text += delta;
            stream.push({ type: "text_delta", contentIndex: textIndex, delta, partial });
            continue;
          }
          if (event.kind === "reasoning_delta") {
            endText();
            if (thinkingIndex === null) {
              thinkingIndex = partial.content.length;
              partial.content.push({ type: "thinking", thinking: "" });
              stream.push({ type: "thinking_start", contentIndex: thinkingIndex, partial });
            }
            const delta = String(event.value ?? "");
            partial.content[thinkingIndex].thinking += delta;
            stream.push({ type: "thinking_delta", contentIndex: thinkingIndex, delta, partial });
            continue;
          }
          if (event.kind === "tool_call_delta") {
            endText();
            endThinking();
            if (!Array.isArray(event.value)) throw new Error("tool_call_delta value must be an array");
            for (const delta of event.value) {
              if (!delta || typeof delta !== "object") throw new Error("tool_call_delta item must be an object");
              const modelIndex = Number.isInteger(delta.index) ? delta.index : 0;
              let state = toolStates.get(modelIndex);
              if (!state) {
                const contentIndex = partial.content.length;
                state = { contentIndex, id: "", name: "", argumentsText: "" };
                toolStates.set(modelIndex, state);
                partial.content.push({ type: "toolCall", id: "pending", name: "pending", arguments: {} });
                stream.push({ type: "toolcall_start", contentIndex, partial });
              }
              if (typeof delta.id === "string") state.id += delta.id;
              const fn = delta.function;
              if (fn && typeof fn === "object") {
                if (typeof fn.name === "string") state.name += fn.name;
                if (typeof fn.arguments === "string") {
                  state.argumentsText += fn.arguments;
                  stream.push({ type: "toolcall_delta", contentIndex: state.contentIndex, delta: fn.arguments, partial });
                } else if (fn.arguments && typeof fn.arguments === "object") {
                  const encoded = JSON.stringify(fn.arguments);
                  state.argumentsText += encoded;
                  stream.push({ type: "toolcall_delta", contentIndex: state.contentIndex, delta: encoded, partial });
                }
              }
            }
            continue;
          }
          if (event.kind === "usage") {
            partial.usage = mapUsage(event.value);
            continue;
          }
          if (event.kind === "finish") {
            finishReason = String(event.value ?? "stop");
            continue;
          }
          if (event.kind === "done") continue;
          throw new Error(`unknown LAC model-provider bridge event: ${String(event.kind)}`);
        }

        if (providerError && child && !child.killed) {
          try { child.kill("SIGTERM"); } catch {}
        }
        const exitCode = await exitPromise;
        if (options.signal) options.signal.removeEventListener?.("abort", onAbort);
        if (aborted) {
          fail("Request was aborted", "aborted");
          return;
        }
        if (providerError) {
          fail(providerError);
          return;
        }
        if (exitCode !== 0) {
          fail(`LAC ModelProvider bridge exited ${exitCode}: ${stderr.trim().slice(-1000)}`);
          return;
        }

        endText();
        endThinking();
        for (const [, state] of [...toolStates.entries()].sort((a, b) => a[0] - b[0])) {
          const toolCall = {
            type: "toolCall",
            id: state.id || `lac-tool-${state.contentIndex}`,
            name: state.name,
            arguments: jsonArguments(state.argumentsText),
          };
          if (!toolCall.name) throw new Error("FreeToken tool call ended without a function name");
          partial.content[state.contentIndex] = toolCall;
          stream.push({ type: "toolcall_end", contentIndex: state.contentIndex, toolCall, partial });
        }

        const reason = mapFinishReason(finishReason, toolStates.size > 0);
        const message = {
          ...partial,
          usage: partial.usage ?? ZERO_USAGE,
          stopReason: reason,
          timestamp: Date.now(),
        };
        stream.push({ type: "done", reason, message });
        stream.end(message);
      } catch (error) {
        fail(error);
      }
    });

    return stream;
  };
}
