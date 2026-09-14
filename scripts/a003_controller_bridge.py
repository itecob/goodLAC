#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

# Direct script execution sets sys.path[0] to <repo>/scripts, not the repository
# root. Pin the import root to this script's owning repository before importing
# any LAC packages so Node-spawned entrypoints cannot depend on caller cwd or
# ambient PYTHONPATH.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.adapters.pi import PiAgentAdapter, PiRunContext
from packages.dispatcher import Dispatcher
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import AgentIdentityRepository, EmergencyPauseRepository, SQLiteStateStore

PRINCIPAL_ID = "principal:owner"
AGENT_ID = "agent:pi"
EXECUTOR_ID = "executor:pi:a003"
POLICY_REVISION = "policy:a003:qualification:v1"


def policy_provider() -> LocalPolicyDecisionProvider:
    actions = {"filesystem.read", "filesystem.create", "filesystem.replace", "shell.exec"}
    resources = {"filesystem:workspace", "shell:workspace"}
    rules = tuple(
        PolicyRule.create(
            rule_id=f"rule:a003:{action}",
            principal_id=PRINCIPAL_ID,
            agent_id=AGENT_ID,
            action=action,
            resource="shell:workspace" if action == "shell.exec" else "filesystem:workspace",
            decision="ALLOW",
        )
        for action in sorted(actions)
    )
    return LocalPolicyDecisionProvider(
        revision=POLICY_REVISION,
        known_principals={PRINCIPAL_ID},
        known_agents={AGENT_ID},
        known_actions=actions,
        known_resources=resources,
        rules=rules,
    )


def canonical_binary(name: str) -> Path:
    expected = Path("/usr/bin") / name
    if not expected.is_file() or expected.is_symlink():
        found = shutil.which(name)
        if not found:
            raise RuntimeError(f"required H003 executable unavailable: {name}")
        resolved = Path(found).resolve(strict=True)
        if resolved.parent != Path("/usr/bin") or resolved.name != name or resolved.is_symlink():
            raise RuntimeError(f"required H003 executable is not canonical /usr/bin/{name}")
        expected = resolved
    return expected


def build_adapter(state_path: Path, workspace: Path, run_id: str) -> tuple[SQLiteStateStore, PiAgentAdapter]:
    store = SQLiteStateStore(state_path)
    dispatcher = Dispatcher(store=store, policy_provider=policy_provider(), lease_seconds=30)
    fs = FilesystemEffectAdapter(workspace)
    shell = ShellEffectAdapter(
        workspace,
        allowed_executables=(canonical_binary("ls"), canonical_binary("cat"), canonical_binary("printf")),
    )
    pi = PiAgentAdapter(
        store=store,
        dispatcher=dispatcher,
        filesystem_adapter=fs,
        shell_adapter=shell,
        context=PiRunContext(
            run_id=run_id,
            principal_id=PRINCIPAL_ID,
            agent_id=AGENT_ID,
            executor_id=EXECUTOR_ID,
        ),
    )
    return store, pi


def cmd_init(args: argparse.Namespace) -> int:
    state = Path(args.state).resolve()
    workspace = Path(args.workspace).resolve(strict=True)
    if state.exists():
        state.unlink()
    store = SQLiteStateStore(state)
    try:
        EmergencyPauseRepository(store).resume()
        AgentIdentityRepository(store).register_active(AGENT_ID, PRINCIPAL_ID)
    finally:
        store.close()
    print(json.dumps({"ok": True, "state": str(state), "workspace": str(workspace)}, sort_keys=True))
    return 0


def cmd_effect(args: argparse.Namespace) -> int:
    state = Path(args.state).resolve(strict=True)
    workspace = Path(args.workspace).resolve(strict=True)
    payload = json.load(sys.stdin)
    if not isinstance(payload, dict):
        raise ValueError("effect bridge input must be a JSON object")
    expected = {"toolCallId", "toolName", "arguments"}
    if set(payload) != expected:
        raise ValueError(f"effect bridge input keys must be exactly {sorted(expected)!r}")
    store, pi = build_adapter(state, workspace, args.run_id)
    request_id: str | None = None
    try:
        request = pi.build_request(
            tool_name=payload["toolName"],
            arguments=payload["arguments"],
            tool_call_id=payload["toolCallId"],
        )
        request_id = request.request_id
        result = pi.execute_message(payload)
        print(json.dumps({"ok": True, "request_id": request_id, "result": result}, sort_keys=True))
    except BaseException as exc:
        print(
            json.dumps(
                {
                    "ok": False,
                    "request_id": request_id,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                },
                sort_keys=True,
            )
        )
    finally:
        store.close()
    return 0


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init")
    init.add_argument("--state", required=True)
    init.add_argument("--workspace", required=True)
    init.set_defaults(func=cmd_init)
    effect = sub.add_parser("effect")
    effect.add_argument("--state", required=True)
    effect.add_argument("--workspace", required=True)
    effect.add_argument("--run-id", required=True)
    effect.set_defaults(func=cmd_effect)
    return p


def main() -> None:
    args = parser().parse_args()
    raise SystemExit(args.func(args))


if __name__ == "__main__":
    main()
