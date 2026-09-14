#!/usr/bin/env node
import assert from "node:assert/strict";
import { mkdtemp, writeFile, rm } from "node:fs/promises";
import os from "node:os";
import path from "node:path";

import { createLacModelProviderStreamFn } from "../../packages/adapters/pi/model_stream_bridge.mjs";

function createTestEventStream() {
  const queue = [];
  const waiters = [];
  let ended = false;
  let resultValue;
  let resolveResult;
  const resultPromise = new Promise((resolve) => { resolveResult = resolve; });

  function wake() {
    while (waiters.length && queue.length) waiters.shift()({ value: queue.shift(), done: false });
    if (ended && !queue.length) while (waiters.length) waiters.shift()({ value: undefined, done: true });
  }

  return {
    push(event) { queue.push(event); wake(); },
    end(value) { resultValue = value; ended = true; resolveResult(value); wake(); },
    result() { return resultPromise; },
    [Symbol.asyncIterator]() {
      return {
        next() {
          if (queue.length) return Promise.resolve({ value: queue.shift(), done: false });
          if (ended) return Promise.resolve({ value: undefined, done: true });
          return new Promise((resolve) => waiters.push(resolve));
        },
      };
    },
    get resultValue() { return resultValue; },
  };
}

const tmp = await mkdtemp(path.join(os.tmpdir(), "lac-a003-stream-test-"));
try {
  const bridge = path.join(tmp, "fake_bridge.py");
  await writeFile(bridge, String.raw`import json, os, sys
json.load(sys.stdin)
if os.environ.get("OPENAI_API_KEY") or os.environ.get("AWS_SECRET_ACCESS_KEY") or os.environ.get("HF_TOKEN"):
    print(json.dumps({"kind":"error","message":"credential leaked to child"}), flush=True)
    raise SystemExit(0)
print(json.dumps({"kind":"tool_call_delta","value":[{"index":0,"id":"call-a003","function":{"name":"lac_fs_read","arguments":'{"path":"PROJECT_BRIEF.txt"}'}}]}), flush=True)
print(json.dumps({"kind":"usage","value":{"input_tokens":10,"output_tokens":4,"total_tokens":14,"cached_input_tokens":0}}), flush=True)
print(json.dumps({"kind":"finish","value":"tool_calls"}), flush=True)
print(json.dumps({"kind":"done"}), flush=True)
`);

  process.env.OPENAI_API_KEY = "must-not-leak";
  process.env.AWS_SECRET_ACCESS_KEY = "must-not-leak";
  process.env.HF_TOKEN = "must-not-leak";
  const streamFn = createLacModelProviderStreamFn({
    createAssistantMessageEventStream: createTestEventStream,
    pythonExecutable: process.env.PYTHON || "python3",
    bridgeScript: bridge,
    baseUrl: "http://127.0.0.1:19203",
    timeoutSeconds: 5,
  });
  const stream = streamFn(
    {
      id: "lac-a003-gpt-oss-20b",
      api: "lac-model-provider",
      provider: "lac-freetoken",
      maxTokens: 128,
    },
    { systemPrompt: "test", messages: [{ role: "user", content: "read" }], tools: [] },
    {},
  );
  const events = [];
  for await (const event of stream) events.push(event);
  const result = await stream.result();
  assert.equal(result.stopReason, "toolUse");
  assert.equal(result.content.length, 1);
  assert.deepEqual(result.content[0], {
    type: "toolCall",
    id: "call-a003",
    name: "lac_fs_read",
    arguments: { path: "PROJECT_BRIEF.txt" },
  });
  assert.equal(result.usage.totalTokens, 14);
  assert.ok(events.some((event) => event.type === "toolcall_end"));
  assert.equal(events.at(-1).type, "done");
  console.log("LAC_A003_STREAM_BRIDGE_TEST=PASS");
} finally {
  delete process.env.OPENAI_API_KEY;
  delete process.env.AWS_SECRET_ACCESS_KEY;
  delete process.env.HF_TOKEN;
  await rm(tmp, { recursive: true, force: true });
}
