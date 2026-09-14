import assert from "node:assert/strict";
import {
  GOVERNED_TOOL_NAMES,
  assertGovernedPiToolSurface,
  constructGovernedPiAgent,
  createGovernedLacTools,
} from "../../packages/adapters/pi/governed_pi.mjs";

const Type = {
  String: () => ({ type: "string" }),
  Array: (items) => ({ type: "array", items }),
  Record: (key, value) => ({ type: "object", key, value }),
  Object: (properties, options = {}) => ({ type: "object", properties, ...options }),
};

class FakeAgent {
  constructor(options) {
    this.options = options;
    this.state = {
      ...options.initialState,
      tools: [...options.initialState.tools],
    };
  }
}

const calls = [];
const executeLac = async (call) => {
  calls.push(call);
  return { schema: "test-result/v1", tool: call.toolName, ok: true };
};
const streamFn = async () => {
  throw new Error("streamFn must not be called by construction test");
};

const agent = constructGovernedPiAgent({
  AgentClass: FakeAgent,
  Type,
  streamFn,
  executeLac,
  systemPrompt: "bounded",
  messages: [],
});

assert.deepEqual(agent.state.tools.map((tool) => tool.name), GOVERNED_TOOL_NAMES);
assert.equal(assertGovernedPiToolSurface(agent), true);
assert.equal(agent.options.toolExecution, "sequential");
assert.equal(agent.state.tools.every((tool) => tool.executionMode === "sequential"), true);
assert.equal(agent.state.tools.every((tool) => tool.parameters.additionalProperties === false), true);
for (const stockName of ["bash", "read", "write", "edit"]) {
  assert.equal(agent.state.tools.some((tool) => tool.name === stockName), false);
}

const tools = createGovernedLacTools({ Type, executeLac });
await tools.find((tool) => tool.name === "lac_fs_read").execute("call-read", { path: "x.txt" });
assert.equal(calls.at(-1).toolName, "lac_fs_read");
assert.deepEqual(calls.at(-1).arguments, { path: "x.txt" });
assert.equal(Object.hasOwn(calls.at(-1), "approval_id"), false);
assert.equal(Object.hasOwn(calls.at(-1), "lease_id"), false);
assert.equal(Object.hasOwn(calls.at(-1), "decision_id"), false);

await assert.rejects(
  () => tools.find((tool) => tool.name === "lac_fs_read").execute(
    "call-auth",
    { path: "x.txt", approval_id: "model-chosen" },
  ),
  /cannot supply controller authority identifiers/,
);
await assert.rejects(
  () => tools.find((tool) => tool.name === "lac_shell_exec").execute(
    "call-shape",
    { executable: "/usr/bin/printf", argv: "wrong", cwd: ".", environment: {} },
  ),
  /argv must be an array of strings/,
);

const source = await import("node:fs/promises").then((fs) => fs.readFile(
  new URL("../../packages/adapters/pi/governed_pi.mjs", import.meta.url),
  "utf8",
));
assert.equal(source.includes("@earendil-works/pi-coding-agent"), false);
assert.equal(source.includes("process.env"), false);
assert.equal(source.includes('import("@earendil-works/pi-agent-core")'), true);

console.log("LAC_A001_PI_HARNESS_TEST=PASS");
