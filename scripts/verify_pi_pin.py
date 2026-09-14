#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

PIN = "da840b6216578c2a571d0374ac6a2091a83f9d91"
DEFAULT = Path.home() / ".cache/local-agent-controller/phase0/upstream/pi"
checkout = Path(os.environ.get("LAC_PI_CHECKOUT", str(DEFAULT))).expanduser().resolve()


def fail(message: str) -> None:
    raise SystemExit(f"LAC_A001_PI_PIN_VERIFY=FAIL: {message}")


if not (checkout / ".git").exists():
    fail(f"pinned Pi checkout missing: {checkout}")
try:
    head = subprocess.check_output(
        ["git", "-C", str(checkout), "rev-parse", "HEAD"], text=True, stderr=subprocess.STDOUT
    ).strip()
except subprocess.CalledProcessError as exc:
    fail(f"cannot read Pi checkout HEAD: {exc.output.strip()}")
if head != PIN:
    fail(f"Pi checkout drift: expected {PIN}, observed {head}")

package_json = checkout / "packages/agent/package.json"
agent_ts = checkout / "packages/agent/src/agent.ts"
types_ts = checkout / "packages/agent/src/types.ts"
loop_ts = checkout / "packages/agent/src/agent-loop.ts"
for path in (package_json, agent_ts, types_ts, loop_ts):
    if not path.is_file():
        fail(f"required pinned Pi source missing: {path.relative_to(checkout)}")

package = json.loads(package_json.read_text(encoding="utf-8"))
if package.get("name") != "@earendil-works/pi-agent-core":
    fail("unexpected Pi agent-core package identity")
if package.get("version") != "0.85.1":
    fail("unexpected Pi agent-core version at pinned revision")
if package.get("license") != "MIT":
    fail("unexpected Pi agent-core license metadata")
if package.get("engines", {}).get("node") != ">=22.19.0":
    fail("unexpected Pi agent-core Node engine contract")

agent = agent_ts.read_text(encoding="utf-8")
types = types_ts.read_text(encoding="utf-8")
loop = loop_ts.read_text(encoding="utf-8")
checks = {
    "AgentOptions initialState": "initialState?: Partial<Omit<AgentState" in agent,
    "initial tools copied exactly": "initialState?.tools?.slice() ?? []" in agent,
    "public state getter": "get state(): AgentState" in agent,
    "AgentTool execute contract": "export interface AgentTool" in types and "execute:" in types,
    "context tools are explicit": "tools?: AgentTool<any>[]" in types,
    "tool lookup is configured surface": "currentContext.tools?.find((t) => t.name === toolCall.name)" in loop,
    "unknown tools fail": "Tool ${toolCall.name} not found" in loop,
    "arguments validate before execute": "validateToolArguments(tool, preparedToolCall)" in loop,
}
failed = [name for name, ok in checks.items() if not ok]
if failed:
    fail("pinned Pi integration contract probe failed: " + ", ".join(failed))

print(f"LAC_A001_PI_PIN={PIN}")
print("LAC_A001_PI_AGENT_CORE_VERSION=0.85.1")
print("LAC_A001_PI_PIN_VERIFY=PASS")
