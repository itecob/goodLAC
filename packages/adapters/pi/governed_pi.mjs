const GOVERNED_TOOL_NAMES = Object.freeze([
  "lac_fs_read",
  "lac_fs_create",
  "lac_fs_replace",
  "lac_shell_exec",
]);

const AUTHORITY_KEYS = new Set([
  "approval_id",
  "decision_id",
  "executor_id",
  "idempotency_key",
  "lease_id",
  "principal_id",
  "agent_id",
  "request_id",
  "run_id",
]);

function assertPlainObject(value, label) {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    throw new TypeError(`${label} must be an object`);
  }
}

function assertExactKeys(value, keys, label) {
  assertPlainObject(value, label);
  const observed = Object.keys(value).sort();
  for (const key of observed) {
    if (AUTHORITY_KEYS.has(key)) {
      throw new TypeError(`${label} cannot supply controller authority identifiers`);
    }
  }
  const expected = [...keys].sort();
  if (observed.length !== expected.length || observed.some((key, index) => key !== expected[index])) {
    throw new TypeError(`${label} must contain exactly: ${expected.join(", ")}`);
  }
}

function validateToolArguments(toolName, args) {
  if (toolName === "lac_fs_read") {
    assertExactKeys(args, ["path"], toolName);
    if (typeof args.path !== "string") throw new TypeError(`${toolName}.path must be a string`);
    return;
  }
  if (toolName === "lac_fs_create" || toolName === "lac_fs_replace") {
    assertExactKeys(args, ["path", "content"], toolName);
    if (typeof args.path !== "string" || typeof args.content !== "string") {
      throw new TypeError(`${toolName}.path and .content must be strings`);
    }
    return;
  }
  if (toolName === "lac_shell_exec") {
    assertExactKeys(args, ["executable", "argv", "cwd", "environment"], toolName);
    if (typeof args.executable !== "string" || typeof args.cwd !== "string") {
      throw new TypeError(`${toolName}.executable and .cwd must be strings`);
    }
    if (!Array.isArray(args.argv) || args.argv.some((value) => typeof value !== "string")) {
      throw new TypeError(`${toolName}.argv must be an array of strings`);
    }
    assertPlainObject(args.environment, `${toolName}.environment`);
    for (const [key, value] of Object.entries(args.environment)) {
      if (typeof key !== "string" || typeof value !== "string") {
        throw new TypeError(`${toolName}.environment must map strings to strings`);
      }
    }
    return;
  }
  throw new TypeError(`unknown governed Pi tool: ${toolName}`);
}

function makeSchemas(Type) {
  if (!Type || typeof Type.Object !== "function" || typeof Type.String !== "function") {
    throw new TypeError("TypeBox Type API is required");
  }
  if (typeof Type.Array !== "function" || typeof Type.Record !== "function") {
    throw new TypeError("TypeBox Array and Record APIs are required");
  }
  const closed = { additionalProperties: false };
  return {
    lac_fs_read: Type.Object({ path: Type.String() }, closed),
    lac_fs_create: Type.Object({ path: Type.String(), content: Type.String() }, closed),
    lac_fs_replace: Type.Object({ path: Type.String(), content: Type.String() }, closed),
    lac_shell_exec: Type.Object(
      {
        executable: Type.String(),
        argv: Type.Array(Type.String()),
        cwd: Type.String(),
        environment: Type.Record(Type.String(), Type.String()),
      },
      closed,
    ),
  };
}

function toText(payload) {
  if (typeof payload === "string") return payload;
  return JSON.stringify(payload);
}

export function createGovernedLacTools({ Type, executeLac }) {
  if (typeof executeLac !== "function") throw new TypeError("executeLac callback is required");
  const schemas = makeSchemas(Type);
  const descriptions = {
    lac_fs_read: "Read one UTF-8 file through the LAC governed filesystem adapter.",
    lac_fs_create: "Create one UTF-8 file through the LAC governed filesystem adapter.",
    lac_fs_replace: "Replace one UTF-8 file through the LAC governed filesystem adapter.",
    lac_shell_exec: "Execute one exact command through the LAC governed shell adapter. executable is the program path; argv contains only arguments after the executable and excludes argv[0] (do not repeat the executable in argv).",
  };

  return GOVERNED_TOOL_NAMES.map((name) => ({
    name,
    label: name,
    description: descriptions[name],
    parameters: schemas[name],
    replay: name === "lac_fs_read" ? "safe" : "never",
    executionMode: "sequential",
    async execute(toolCallId, params, signal) {
      validateToolArguments(name, params);
      if (signal?.aborted) throw new Error("Operation aborted");
      const payload = await executeLac({
        toolCallId,
        toolName: name,
        arguments: params,
        signal,
      });
      return {
        content: [{ type: "text", text: toText(payload) }],
        details: payload,
      };
    },
  }));
}

export function constructGovernedPiAgent({ AgentClass, Type, streamFn, executeLac, systemPrompt = "", model, messages = [] }) {
  if (typeof AgentClass !== "function") throw new TypeError("Pi Agent constructor is required");
  if (typeof streamFn !== "function") throw new TypeError("Pi streamFn is required");
  if (!Array.isArray(messages)) throw new TypeError("messages must be an array");
  const tools = createGovernedLacTools({ Type, executeLac });
  const initialState = { systemPrompt, messages: [...messages], tools };
  if (model !== undefined) initialState.model = model;
  const agent = new AgentClass({
    initialState,
    streamFn,
    toolExecution: "sequential",
  });
  assertGovernedPiToolSurface(agent);
  return agent;
}

export async function createGovernedPiAgent(options) {
  const [{ Agent }, { Type }] = await Promise.all([
    import("@earendil-works/pi-agent-core"),
    import("typebox"),
  ]);
  return constructGovernedPiAgent({ ...options, AgentClass: Agent, Type });
}

export function assertGovernedPiToolSurface(agent) {
  const tools = agent?.state?.tools;
  if (!Array.isArray(tools)) throw new TypeError("Pi Agent state.tools is unavailable");
  const names = tools.map((tool) => tool?.name);
  if (names.length !== GOVERNED_TOOL_NAMES.length || names.some((name, index) => name !== GOVERNED_TOOL_NAMES[index])) {
    throw new Error(`unexpected Pi tool surface: ${JSON.stringify(names)}`);
  }
  return true;
}

export { GOVERNED_TOOL_NAMES };
