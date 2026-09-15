#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import { readFileSync, writeFileSync } from "node:fs";
import net from "node:net";
import { createInterface } from "node:readline";
import { pathToFileURL } from "node:url";

import { constructGovernedPiAgent, assertGovernedPiToolSurface, GOVERNED_TOOL_NAMES } from "./governed_pi.mjs";

const protocolOut = (value) => process.stdout.write(`${JSON.stringify(value)}\n`);
console.log = (...args) => console.error(...args);
console.info = (...args) => console.error(...args);

const rl = createInterface({ input: process.stdin, crlfDelay: Infinity });
const input = rl[Symbol.asyncIterator]();
let rpcCounter = 0;

async function nextMessage() {
  const item = await input.next();
  if (item.done) throw new Error("host IPC closed unexpectedly");
  let parsed;
  try {
    parsed = JSON.parse(item.value);
  } catch (error) {
    throw new Error(`invalid host IPC JSON: ${error.message}`);
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("host IPC message must be an object");
  }
  return parsed;
}

async function rpc(kind, payload) {
  const id = `rpc-${++rpcCounter}`;
  protocolOut({ type: "rpc", id, kind, payload });
  const response = await nextMessage();
  if (response.type !== "rpc_response" || response.id !== id || typeof response.ok !== "boolean") {
    throw new Error("host IPC response did not bind the active request");
  }
  if (!response.ok) throw new Error(`host IPC ${kind} failed: ${String(response.error || "unknown")}`);
  return response.payload;
}

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

function makeRpcStreamFn(createAssistantMessageEventStream, timeoutSeconds) {
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
      let started = false;
      let textIndex = null;
      let thinkingIndex = null;
      let finishReason = null;
      const toolStates = new Map();
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
        const message = {
          role: "assistant",
          content: started ? partial.content : [],
          api: model.api,
          provider: model.provider,
          model: model.id,
          usage: cloneUsage(),
          stopReason: reason,
          errorMessage: error instanceof Error ? error.message : String(error),
          timestamp: Date.now(),
        };
        stream.push({ type: "error", reason, error: message });
        stream.end(message);
      };

      try {
        start();
        const events = await rpc("model_request", {
          model: model.id,
          context,
          options: {
            maxTokens: options.maxTokens ?? Math.min(Number(model.maxTokens || 1024), 2048),
            temperature: options.temperature ?? 0,
            toolChoice: options.toolChoice ?? "auto",
            reasoning: options.reasoning,
            timeoutSeconds,
          },
        });
        if (!Array.isArray(events)) throw new Error("model broker response must be an event array");
        for (const event of events) {
          if (!event || typeof event !== "object") throw new Error("model broker event must be an object");
          if (event.kind === "error") throw new Error(event.message || "LAC ModelProvider failed closed");
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
          throw new Error(`unknown LAC ModelProvider event: ${String(event.kind)}`);
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
        const message = { ...partial, stopReason: reason, timestamp: Date.now() };
        stream.push({ type: "done", reason, message });
        stream.end(message);
      } catch (error) {
        fail(error);
      }
    });
    return stream;
  };
}

function sanitizedMessages(messages) {
  const output = [];
  for (const message of messages || []) {
    if (message?.role === "assistant") {
      const blocks = [];
      for (const block of message.content || []) {
        if (block?.type === "text") blocks.push({ type: "text", text: block.text });
        else if (block?.type === "toolCall") blocks.push({ type: "toolCall", id: block.id, name: block.name, arguments: block.arguments });
      }
      output.push({ role: "assistant", content: blocks, stopReason: message.stopReason, model: message.model });
    } else if (message?.role === "user") {
      output.push({ role: "user", content: message.content });
    } else if (message?.role === "toolResult") {
      output.push({ role: "toolResult", toolCallId: message.toolCallId, toolName: message.toolName, isError: message.isError });
    }
  }
  return output;
}

function assistantText(messages) {
  for (let i = messages.length - 1; i >= 0; i -= 1) {
    const message = messages[i];
    if (message?.role !== "assistant") continue;
    const parts = [];
    for (const block of message.content || []) {
      if (block?.type === "text" && typeof block.text === "string") parts.push(block.text);
    }
    return parts.join("\n");
  }
  return "";
}

async function connectProbe(host, port) {
  return await new Promise((resolve) => {
    const socket = net.createConnection({ host, port: Number(port) });
    let settled = false;
    const done = (connected, detail) => {
      if (settled) return;
      settled = true;
      socket.destroy();
      resolve({ connected, detail: String(detail || "") });
    };
    socket.setTimeout(500, () => done(false, "timeout"));
    socket.once("connect", () => done(true, "connected"));
    socket.once("error", (error) => done(false, error.code || error.message));
  });
}

async function ambientProbes(bootstrap) {
  let hostFileReadable = false;
  try { readFileSync(String(bootstrap.hostFilePath), "utf8"); hostFileReadable = true; } catch {}
  let workspaceFileReadable = false;
  try { readFileSync(String(bootstrap.workspaceProbeReadPath), "utf8"); workspaceFileReadable = true; } catch {}
  let workspaceWriteEffect = false;
  try { writeFileSync(String(bootstrap.workspaceProbeWritePath), "escaped\n", "utf8"); workspaceWriteEffect = true; } catch {}
  const envName = String(bootstrap.syntheticCredentialName);
  const inheritedCredential = Object.prototype.hasOwnProperty.call(process.env, envName);
  const launched = spawnSync("/usr/bin/touch", [String(bootstrap.processMarkerPath)], { encoding: "utf8" });
  const loopback = await connectProbe("127.0.0.1", bootstrap.loopbackPort);
  const privateNet = await connectProbe("10.255.255.1", 9);
  return {
    schema: "lac.a004-pi-process-ambient-conformance/v1",
    pid: process.pid,
    host_file_readable: hostFileReadable,
    workspace_file_readable: workspaceFileReadable,
    workspace_write_effect: workspaceWriteEffect,
    synthetic_service_credential_inherited: inheritedCredential,
    arbitrary_host_executable_launched: !launched.error,
    loopback_connected: loopback.connected,
    loopback_detail: loopback.detail,
    private_network_connected: privateNet.connected,
    private_network_detail: privateNet.detail,
    cwd: process.cwd(),
    environment_keys: Object.keys(process.env).sort(),
  };
}

async function main() {
  const bootstrap = await nextMessage();
  if (bootstrap.type !== "bootstrap" || bootstrap.mode !== "interactive") {
    throw new Error("first host IPC message must be A004 interactive bootstrap");
  }
  const agentUrl = pathToFileURL("/pi/packages/agent/dist/index.js").href;
  const aiUrl = pathToFileURL("/pi/packages/ai/dist/index.js").href;
  const [{ Agent }, piAi] = await Promise.all([import(agentUrl), import(aiUrl)]);
  const { Type, createAssistantMessageEventStream } = piAi;
  if (!Type || typeof createAssistantMessageEventStream !== "function") {
    throw new Error("pinned Pi dist does not expose Type/createAssistantMessageEventStream");
  }

  const executeLac = async ({ toolCallId, toolName, arguments: toolArguments }) => {
    const response = await rpc("effect_request", { toolCallId, toolName, arguments: toolArguments });
    if (!response || response.ok !== true) {
      throw new Error(`LAC governed effect failed closed (${String(response?.error_type || "unknown")})`);
    }
    return response.result;
  };
  const streamFn = makeRpcStreamFn(createAssistantMessageEventStream, Number(bootstrap.timeoutSeconds || 300));
  const model = {
    id: String(bootstrap.modelId),
    name: "LAC A004 gpt-oss-20b",
    api: "lac-model-provider",
    provider: "lac-freetoken",
    reasoning: true,
    input: ["text"],
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    contextWindow: 131072,
    maxTokens: 2048,
  };
  const agent = constructGovernedPiAgent({
    AgentClass: Agent,
    Type,
    streamFn,
    executeLac,
    systemPrompt: String(bootstrap.systemPrompt || ""),
    model,
    messages: [],
  });
  assertGovernedPiToolSurface(agent);
  const probes = await ambientProbes(bootstrap);
  protocolOut({
    type: "ready",
    tool_surface: [...GOVERNED_TOOL_NAMES],
    probes,
    pid: process.pid,
  });

  while (true) {
    const command = await nextMessage();
    if (command.type === "shutdown") {
      protocolOut({ type: "shutdown_complete" });
      return;
    }
    if (command.type !== "prompt" || typeof command.id !== "string" || typeof command.text !== "string") {
      throw new Error("host control message must be prompt or shutdown");
    }
    const before = agent.state.messages.length;
    await agent.prompt(command.text);
    await agent.waitForIdle();
    if (agent.state.errorMessage) throw new Error(`Pi Agent ended with error: ${agent.state.errorMessage}`);
    const delta = agent.state.messages.slice(before);
    protocolOut({
      type: "turn_result",
      id: command.id,
      assistant_text: assistantText(delta),
      transcript_delta: sanitizedMessages(delta),
      total_messages: agent.state.messages.length,
    });
  }
}

main().catch((error) => {
  protocolOut({ type: "fatal", error: String(error?.stack || error) });
  process.exitCode = 1;
});
