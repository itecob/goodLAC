#!/usr/bin/env node
import { spawnSync } from "node:child_process";
import path from "node:path";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));
const ROOT = path.resolve(HERE, "..");
const PYTHON = process.env.LAC_A003_PYTHON || "python3";
const RUN_ROOT = path.resolve(process.env.LAC_A003_RUN_ROOT || path.join(ROOT, ".a003-run"));
const BROKER = path.join(ROOT, "scripts", "a003_agent_sandbox.py");

// Compatibility entrypoint only. The Pi Agent is never constructed in this host
// Node process. The Python broker launches the actual pinned Pi process through
// the qualified H001 SandboxBackend and communicates over inherited stdio IPC.
const proc = spawnSync(PYTHON, [BROKER, "qualification", "--run-root", RUN_ROOT], {
  stdio: "inherit",
  env: process.env,
});
if (proc.error) throw proc.error;
process.exit(proc.status ?? 1);
