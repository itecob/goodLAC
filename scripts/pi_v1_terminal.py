#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import selectors
import signal
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.a004_terminal as baseline
from packages.adapters.pi.production import (PI_V1_APPLICATION_ID, PI_V1_SKILL_ID, canonical_project_root, pi_v1_project_application_id)
from packages.capabilities import PendingPermissionRepository
from packages.lacctl import LacctlClient
from packages.policy import StandingPolicyRule
from packages.state import SQLiteStateStore

EFFECT_BRIDGE = REPO_ROOT / "scripts" / "pi_v1_controller_bridge.py"
ADMIN_SERVER = REPO_ROOT / "scripts" / "pi_v1_admin_server.py"
APPROVAL_WAIT_LIMIT_SECONDS = 3600
PERMISSION_WAIT_LIMIT_SECONDS = 3600
WAIT_POLL_SECONDS = 0.5


class PiV1TerminalError(RuntimeError):
    pass


def default_workspace():
    return Path.cwd()


def default_state():
    return Path.home() / ".local/state/local-agent-controller/pi-v1/controller.db"


def default_trace():
    return Path.home() / ".local/state/local-agent-controller/pi-v1/effect-trace.jsonl"


def system_prompt():
    return "\n".join(
        (
            "You are running inside the explicit Local Agent Controller governed Pi v1 profile.",
            "You have exactly four consequential-effect tools: lac_fs_read, lac_fs_create, lac_fs_replace, lac_shell_exec.",
            "Every effect is submitted to LAC capability validation, standing permission, exact approval when required, dispatch, sandboxing and durable receipts.",
            "If a permission configuration is required, the trusted host suspends the tool turn before you receive a result. The original request remains terminally denied; after owner resolution the host may submit exactly one fresh request from the unchanged captured intent.",
            "Do not retry, mutate, or seek an alternate consequential route while a permission decision is being handled by the trusted host.",
            "For REQUIRE_APPROVAL the trusted host keeps the exact current request pending while the owner decides through lacctl.",
            "All filesystem paths are relative to the governed workspace.",
            "For lac_shell_exec argv excludes argv[0]; the initial profile accepts an empty environment object only.",
            "Do not claim success unless execution_state is SUCCEEDED. Do not expose hidden reasoning or credentials.",
        )
    )


def _bridge(args: list[str], payload: Mapping[str, Any] | None = None):
    proc = subprocess.run(
        [sys.executable, str(EFFECT_BRIDGE), *args],
        input=None if payload is None else json.dumps(dict(payload)),
        text=True,
        capture_output=True,
        cwd=REPO_ROOT,
        timeout=90,
        check=False,
    )
    if proc.returncode:
        raise PiV1TerminalError(
            f"effect bridge exited {proc.returncode}: {proc.stderr[-1200:]}"
        )
    try:
        value = json.loads(proc.stdout)
    except json.JSONDecodeError as exc:
        raise PiV1TerminalError("effect bridge emitted malformed JSON") from exc
    if not isinstance(value, dict):
        raise PiV1TerminalError("effect bridge result must be an object")
    return value


def bridge_json(state, workspace, run_id, payload):
    return _bridge(
        [
            "effect",
            "--state",
            str(state),
            "--workspace",
            str(workspace),
            "--run-id",
            run_id,
        ],
        payload,
    )


def bridge_continuation_status(state, workspace, continuation_id):
    return _bridge(
        ["continuation-status", "--state", str(state), "--workspace", str(workspace), continuation_id]
    )


def bridge_continuation_list(state, workspace, *, recoverable_only=True):
    args = ["continuation-list", "--state", str(state), "--workspace", str(workspace)]
    if recoverable_only:
        args.append("--recoverable-only")
    return _bridge(args)


def bridge_continuation_resume(
    state, workspace, run_id, continuation_id, *, expected_message=None
):
    payload = {}
    if expected_message is not None:
        payload["expected_message"] = dict(expected_message)
    return _bridge(
        [
            "continuation-resume",
            "--state",
            str(state),
            "--workspace",
            str(workspace),
            "--run-id",
            run_id,
            continuation_id,
        ],
        payload,
    )


def initialize_state(state, workspace):
    workspace = canonical_project_root(workspace)
    proc = subprocess.run(
        [
            sys.executable,
            str(EFFECT_BRIDGE),
            "init",
            "--state",
            str(state),
            "--workspace",
            str(workspace),
        ],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if proc.returncode:
        raise PiV1TerminalError(
            f"state initialization failed: {proc.stdout}{proc.stderr}"
        )


def start_admin_server(state, workspace):
    proc = subprocess.Popen(
        [
            sys.executable,
            "-u",
            str(ADMIN_SERVER),
            "--state",
            str(state),
            "--workspace",
            str(workspace),
            "--parent-pid",
            str(os.getpid()),
        ],
        cwd=REPO_ROOT,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
    )
    assert proc.stdout is not None
    sel = selectors.DefaultSelector()
    sel.register(proc.stdout, selectors.EVENT_READ)
    try:
        ready = sel.select(timeout=8)
        if not ready:
            stderr = (
                proc.stderr.read()[-1600:]
                if proc.poll() is not None and proc.stderr
                else ""
            )
            proc.kill()
            raise PiV1TerminalError(
                f"admin server did not become ready: {stderr}"
            )
        line = proc.stdout.readline()
    finally:
        sel.close()
    if not line:
        raise PiV1TerminalError("admin server exited before ready")
    try:
        value = json.loads(line)
    except json.JSONDecodeError as exc:
        raise PiV1TerminalError("admin ready message malformed") from exc
    if value.get("schema") != "lac.pi-v1-admin-ready/v1":
        raise PiV1TerminalError(f"unexpected admin ready message: {value!r}")
    return proc


def stop_admin_server(proc):
    if proc is None:
        return
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)


def effect_line(result):
    receipt = result.get("receipt")
    rid = receipt.get("receipt_id") if isinstance(receipt, Mapping) else "-"
    return (
        f"[effect] authority={result.get('authority_outcome', '?')} "
        f"state={result.get('execution_state', '?')} "
        f"request={result.get('request_id', '-')} receipt={rid or '-'}"
    )


def _continuation_line(status: Mapping[str, Any]) -> str:
    owner = status.get("owner_resolution")
    resolution = (
        owner.get("resolution")
        if isinstance(owner, Mapping)
        else "PENDING_OWNER_CONFIGURATION"
    )
    return (
        f"continuation={status.get('continuation_id', '-')} "
        f"state={status.get('state', '?')} original={status.get('original_request_id', '-')} "
        f"fresh={status.get('fresh_request_id') or '-'} owner={resolution}"
    )


class PiV1InteractiveSession(baseline.InteractiveSession):
    def __init__(
        self,
        *,
        workspace,
        state,
        trace,
        permission_wait_hook: Callable[[Mapping[str, Any]], None] | None = None,
    ):
        super().__init__(
            workspace=workspace,
            state=state,
            trace=trace,
            system_prompt=system_prompt(),
        )
        self.run_id = f"run:pi-v1:{uuid.uuid4().hex}"
        self.permission_wait_hook = permission_wait_hook

    def _trace_result(self, payload, result):
        self.trace.parent.mkdir(parents=True, exist_ok=True)
        with self.trace.open("a", encoding="utf-8") as f:
            f.write(
                json.dumps(
                    {
                        "toolCallId": payload.get("toolCallId"),
                        "toolName": payload.get("toolName"),
                        "request_id": result.get("request_id"),
                        "authority_outcome": result.get("authority_outcome"),
                        "execution_state": result.get("execution_state"),
                        "decision_id": result.get("decision_id"),
                        "permission_configuration": result.get(
                            "permission_configuration"
                        ),
                        "workflow_continuation": result.get(
                            "workflow_continuation"
                        ),
                        "receipt_id": result.get("receipt", {}).get("receipt_id")
                        if isinstance(result.get("receipt"), Mapping)
                        else None,
                    },
                    sort_keys=True,
                )
                + "\n"
            )

    def _resume_once(self, continuation_id, *, expected_message=None):
        response = bridge_continuation_resume(
            self.state,
            self.workspace,
            self.run_id,
            continuation_id,
            expected_message=expected_message,
        )
        if response.get("ok") is not True:
            return response
        resume = response.get("resume")
        if not isinstance(resume, Mapping):
            raise PiV1TerminalError("continuation resume result malformed")
        return response

    def _permission_wait(self, payload, initial_result):
        continuation = initial_result.get("workflow_continuation")
        if not isinstance(continuation, Mapping):
            raise PiV1TerminalError(
                "configuration-required effect lacks workflow continuation"
            )
        continuation_id = continuation.get("continuation_id")
        pending_id = continuation.get("pending_id")
        if not isinstance(continuation_id, str) or not continuation_id:
            raise PiV1TerminalError("workflow continuation lacks identity")
        if not isinstance(pending_id, str) or not pending_id:
            raise PiV1TerminalError("workflow continuation lacks pending identity")

        print(
            f"[permission] workflow suspended before model continuation; pending={pending_id} "
            f"continuation={continuation_id}. The original effect is terminally closed. "
            "In another owner terminal choose exactly one bounded outcome with: "
            f"lac-owner decide <allow-once|always-allow|ask-every-time|deny-once|always-deny> "
            f"{continuation_id} {pending_id}. "
            "The owner command changes canonical goodLAC permission state only; continuation resume remains separate.",
            flush=True,
        )
        if self.permission_wait_hook is not None:
            self.permission_wait_hook(dict(continuation))

        started = time.monotonic()
        announced_decision = None
        while True:
            status_response = bridge_continuation_status(
                self.state, self.workspace, continuation_id
            )
            if status_response.get("ok") is not True:
                return status_response
            status = status_response.get("continuation")
            if not isinstance(status, Mapping):
                raise PiV1TerminalError("continuation status malformed")

            owner_resolution = status.get("owner_resolution")
            state = status.get("state")
            if (
                state == "WAITING_PERMISSION"
                and owner_resolution is None
                and time.monotonic() - started < PERMISSION_WAIT_LIMIT_SECONDS
            ):
                time.sleep(WAIT_POLL_SECONDS)
                continue

            response = self._resume_once(
                continuation_id, expected_message=payload
            )
            if response.get("ok") is not True:
                return response
            resume = response.get("resume")
            assert isinstance(resume, Mapping)
            result = resume.get("result")
            if resume.get("kind") == "WAITING_PERMISSION":
                if time.monotonic() - started >= PERMISSION_WAIT_LIMIT_SECONDS:
                    raise PiV1TerminalError(
                        "permission workflow remained unresolved beyond bounded wait"
                    )
                time.sleep(WAIT_POLL_SECONDS)
                continue
            if not isinstance(result, Mapping):
                raise PiV1TerminalError(
                    "resolved continuation did not provide explicit workflow result"
                )
            result = dict(result)
            print(effect_line(result), flush=True)

            if (
                result.get("authority_outcome") == "REQUIRE_APPROVAL"
                and result.get("execution_state") == "PENDING_APPROVAL"
            ):
                decision = result.get("decision_id")
                if decision != announced_decision:
                    print(
                        f"[approval] fresh continuation request requires exact owner approval; "
                        f"decision={decision}. In another terminal: lac-owner approvals approve {decision} "
                        "(or reject it). The broker keeps the same fresh canonical request.",
                        flush=True,
                    )
                    announced_decision = decision
                if time.monotonic() - started >= APPROVAL_WAIT_LIMIT_SECONDS:
                    self._trace_result(payload, result)
                    return {
                        "ok": True,
                        "request_id": result.get("request_id"),
                        "result": result,
                    }
                time.sleep(WAIT_POLL_SECONDS)
                continue

            self._trace_result(payload, result)
            return {
                "ok": True,
                "request_id": result.get("request_id"),
                "result": result,
            }

    def _effect(self, payload):
        if not isinstance(payload, Mapping):
            baseline.fail("effect_request payload must be an object")
        print(f"[tool] {baseline.tool_summary(payload)}", flush=True)
        started = time.monotonic()
        announced = False
        while True:
            response = bridge_json(
                self.state, self.workspace, self.run_id, payload
            )
            if response.get("ok") is not True:
                return response
            result = response.get("result")
            if not isinstance(result, Mapping):
                raise PiV1TerminalError("effect result malformed")
            result = dict(result)
            print(effect_line(result), flush=True)
            permission = result.get("permission_configuration")
            if (
                isinstance(permission, Mapping)
                and permission.get("required") is True
            ):
                # Critical D001 behavior: do not return the terminal denial to the Pi worker.
                # The worker's synchronous effect RPC remains blocked here, so the model cannot
                # continue the turn or improvise an alternate effect route.
                return self._permission_wait(payload, result)
            if (
                result.get("authority_outcome") == "REQUIRE_APPROVAL"
                and result.get("execution_state") == "PENDING_APPROVAL"
            ):
                decision = result.get("decision_id")
                if not announced:
                    print(
                        f"[approval] exact owner decision required; decision={decision}. In another terminal: "
                        f"lac-owner approvals approve {decision} (or reject it). "
                        "The broker retries this same canonical request.",
                        flush=True,
                    )
                    announced = True
                if time.monotonic() - started >= APPROVAL_WAIT_LIMIT_SECONDS:
                    self._trace_result(payload, result)
                    return response
                time.sleep(1.0)
                continue
            self._trace_result(payload, result)
            return response

    def tool_probe(self, *, tool_call_id, tool_name, arguments):
        probe_id = "probe-" + uuid.uuid4().hex
        self._write(
            {
                "type": "tool_probe",
                "id": probe_id,
                "toolCallId": tool_call_id,
                "toolName": tool_name,
                "arguments": dict(arguments),
            }
        )
        deadline = time.monotonic() + 120
        while time.monotonic() < deadline:
            message = self._read(min(30, max(0.1, deadline - time.monotonic())))
            if message.get("type") == "rpc":
                if message.get("kind") != "effect_request":
                    baseline.fail("tool probe requested unexpected host capability")
                handled = self._effect(message.get("payload"))
                self._write(
                    {
                        "type": "rpc_response",
                        "id": message.get("id"),
                        "ok": True,
                        "payload": handled,
                    }
                )
                continue
            if message.get("type") == "tool_probe_result":
                if message.get("id") != probe_id:
                    baseline.fail("tool probe result did not bind active probe")
                details = message.get("details")
                if not isinstance(details, Mapping):
                    baseline.fail("tool probe lacks bounded details")
                return dict(details)
            baseline.fail(f"unexpected Pi message during tool probe: {message!r}")
        baseline.fail("tool probe timed out")

    def owner_resume(self, continuation_id: str):
        started = time.monotonic()
        announced_decision = None
        while True:
            response = self._resume_once(continuation_id)
            if response.get("ok") is not True:
                raise PiV1TerminalError(
                    f"continuation resume failed: {response.get('error_type')}: {response.get('error')}"
                )
            resume = response.get("resume")
            if not isinstance(resume, Mapping):
                raise PiV1TerminalError("continuation resume malformed")
            print(_continuation_line(resume.get("workflow_continuation", {})))
            if resume.get("kind") == "WAITING_PERMISSION":
                print(
                    "Continuation remains blocked. Configure/resolve the owner permission item first; no effect was dispatched."
                )
                return
            result = resume.get("result")
            if not isinstance(result, Mapping):
                raise PiV1TerminalError("continuation resume lacks result")
            print(effect_line(result))
            if (
                result.get("authority_outcome") == "REQUIRE_APPROVAL"
                and result.get("execution_state") == "PENDING_APPROVAL"
            ):
                decision = result.get("decision_id")
                if decision != announced_decision:
                    print(
                        f"Exact approval required: lac-owner approvals approve {decision} (or reject it)."
                    )
                    announced_decision = decision
                if time.monotonic() - started >= APPROVAL_WAIT_LIMIT_SECONDS:
                    print("Approval wait ended without dispatch; rerun /resume explicitly.")
                    return
                time.sleep(WAIT_POLL_SECONDS)
                continue
            print(
                "Explicit restart recovery completed the captured effect workflow. Restart recovery never auto-dispatches."
            )
            return


def profile_status(session, runtime_mode):
    return (
        f"runtime={runtime_mode} model={baseline.SERVED_MODEL_ID} pi_agent_core=0.85.1\n"
        f"pi_pid={session.pi_pid or '-'} profile=lac-governed-v1 sandbox=bubblewrap network=none\n"
        f"tools={','.join(baseline.EXPECTED_TOOLS)}\n"
        f"application={pi_v1_project_application_id(session.workspace)} skill={PI_V1_SKILL_ID}\n"
        f"workspace={session.workspace}\nstate={session.state}\ntrace={session.trace}\n"
        "standalone_pi=separate_and_not_claimed_as_lac_governed"
    )


def run_profile_probe(workspace, state, trace):
    continued = workspace / "pi-d001-continued.txt"
    continued.unlink(missing_ok=True)
    observed_waits: list[dict[str, Any]] = []

    def resolve_wait(status):
        observed_waits.append(dict(status))
        rule = StandingPolicyRule.create(
            rule_id="pi-d001-profile-probe-allow-create",
            application_id=pi_v1_project_application_id(workspace),
            skill_id=PI_V1_SKILL_ID,
            action="filesystem.create",
            resource_selector="filesystem:workspace",
            decision="ALLOW",
        )
        client = LacctlClient()
        client.call(
            "permissions.replace",
            {"rules": [rule.to_material()], "defaults": []},
        )
        client.call(
            "pending.resolve",
            {
                "pending_id": status["pending_id"],
                "resolution": "POLICY_UPDATED",
            },
        )

    with PiV1InteractiveSession(
        workspace=workspace,
        state=state,
        trace=trace,
        permission_wait_hook=resolve_wait,
    ) as session:
        result = session.tool_probe(
            tool_call_id="pi-d001-profile-continuation",
            tool_name="lac_fs_create",
            arguments={"path": continued.name, "content": "pi-d001-fresh-continuation"},
        )
        if len(observed_waits) != 1:
            raise PiV1TerminalError(
                "real Pi path did not enter exactly one permission wait before returning tool result"
            )
        if result.get("authority_outcome") != "ALLOW" or result.get("execution_state") != "SUCCEEDED":
            raise PiV1TerminalError(
                f"fresh continued request failed: {result!r}"
            )
        continuation = result.get("workflow_continuation")
        if not isinstance(continuation, Mapping):
            raise PiV1TerminalError("fresh result lacks continuation status")
        original_request = continuation.get("original_request_id")
        fresh_request = continuation.get("fresh_request_id")
        if not isinstance(original_request, str) or not isinstance(fresh_request, str):
            raise PiV1TerminalError("continuation request identities are malformed")
        if original_request == fresh_request:
            raise PiV1TerminalError("continuation revived the original request identity")
        if continued.read_text(encoding="utf-8") != "pi-d001-fresh-continuation":
            raise PiV1TerminalError("unexpected continued filesystem content")
        store = SQLiteStateStore(state)
        try:
            closure = PendingPermissionRepository(store).get_closure(original_request)
        finally:
            store.close()
        if closure is None:
            raise PiV1TerminalError("original permission-denied request lost terminal closure")

        replay = session.tool_probe(
            tool_call_id="pi-d001-profile-continuation",
            tool_name="lac_fs_create",
            arguments={"path": continued.name, "content": "pi-d001-fresh-continuation"},
        )
        if replay.get("replayed") is not True:
            raise PiV1TerminalError(
                "duplicate continuation did not replay the one fresh terminal receipt"
            )
        if replay.get("request_id") != fresh_request:
            raise PiV1TerminalError("duplicate continuation changed fresh request identity")

        print(profile_status(session, "profile-probe"))
        print("LAC_PI002_D001_REAL_PI_SUSPENSION_BEFORE_MODEL_CONTINUATION=PASS")
        print("LAC_PI002_D001_ORIGINAL_REQUEST_TERMINAL=PASS")
        print("LAC_PI002_D001_ONE_FRESH_REQUEST=PASS")
        print("LAC_PI001_REAL_PI_PERMISSION_PATH=PASS")
        print("LAC_PI001_REAL_PI_DUPLICATE_PREVENTION=PASS")
    print("LAC_PI001_PROFILE_PROBE=PASS")
    return 0


def _show_recoverable(state, workspace):
    response = bridge_continuation_list(state, workspace, recoverable_only=True)
    if response.get("ok") is not True:
        raise PiV1TerminalError(
            f"continuation recovery inspection failed: {response.get('error')}"
        )
    items = response.get("continuations")
    if not isinstance(items, list):
        raise PiV1TerminalError("continuation recovery list malformed")
    if items:
        print(
            f"Recovered {len(items)} blocked workflow continuation(s). No effect was dispatched on restart. "
            "Use /continuations to inspect and /resume <continuation_id> for an explicit recovery event."
        )
    return items


def run_interactive(workspace, state, trace, runtime_mode):
    with PiV1InteractiveSession(workspace=workspace, state=state, trace=trace) as session:
        print("LAC-governed Pi v1 profile. Type /help for controls.")
        print(profile_status(session, runtime_mode))
        _show_recoverable(state, workspace)
        while True:
            try:
                raw = baseline.read_terminal_input("\nlac-pi> ")
            except EOFError:
                raw = "/quit"
            try:
                raw = baseline.validate_terminal_input(raw)
            except baseline.A004InputRejected as exc:
                print(f"input> rejected: {exc}")
                continue
            cmd = raw.strip()
            if cmd in {"/quit", "quit", "exit"}:
                break
            if cmd in {"/help", "help"}:
                print(
                    "/help show controls\n/status show governed profile status\n"
                    "/continuations show blocked/recoverable workflow continuations\n"
                    "/resume <continuation_id> explicitly resume one recovered continuation\n"
                    "/quit clean shutdown\n"
                    "Other text is sent to pinned Pi. Use lac-owner in another owner terminal for admin."
                )
                continue
            if cmd in {"/status", "status"}:
                print(profile_status(session, runtime_mode))
                continue
            if cmd == "/continuations":
                items = _show_recoverable(state, workspace)
                if not items:
                    print("No recoverable workflow continuations.")
                else:
                    for item in items:
                        if not isinstance(item, Mapping):
                            raise PiV1TerminalError(
                                "continuation recovery item malformed"
                            )
                        print(_continuation_line(item))
                continue
            if cmd.startswith("/resume "):
                continuation_id = cmd[len("/resume ") :].strip()
                if not continuation_id:
                    print("usage: /resume <continuation_id>")
                    continue
                session.owner_resume(continuation_id)
                continue
            if not cmd:
                continue
            print(f"assistant> {session.prompt(raw)}")
    print("LAC_PI_V1_TERMINAL_SHUTDOWN=CLEAN")
    return 0


def main():
    p = argparse.ArgumentParser(description="Production LAC-governed Pi v1 profile")
    p.add_argument("--workspace", type=Path, default=default_workspace())
    p.add_argument("--state", type=Path, default=default_state())
    p.add_argument("--trace", type=Path, default=default_trace())
    p.add_argument("--runtime", choices=("manage", "external"), default="manage")
    p.add_argument("--profile-probe", action="store_true")
    a = p.parse_args()
    baseline.verify_accepted_pins()
    workspace = canonical_project_root(a.workspace)
    state = a.state.expanduser().resolve()
    trace = a.trace.expanduser().resolve()
    initialize_state(state, workspace)
    admin = None
    runtime = None
    old = signal.getsignal(signal.SIGTERM)

    def terminate(_s, _f):
        raise KeyboardInterrupt

    signal.signal(signal.SIGTERM, terminate)
    try:
        admin = start_admin_server(state, workspace)
        if a.profile_probe:
            return run_profile_probe(workspace, state, trace)
        mode = "external"
        if a.runtime == "manage":
            runtime = baseline.FreeTokenRuntime()
            mode = runtime.ensure()
        else:
            exact, detail = baseline.probe_exact_endpoint(baseline.runtime_assets())
            if not exact:
                raise PiV1TerminalError(
                    f"external FreeToken endpoint is not exact accepted runtime: {detail}"
                )
        return run_interactive(workspace, state, trace, mode)
    finally:
        signal.signal(signal.SIGTERM, old)
        if runtime is not None:
            runtime.stop()
        stop_admin_server(admin)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nLAC_PI_V1_TERMINAL_SHUTDOWN=INTERRUPTED_CLEAN")
        raise SystemExit(130)
    except (PiV1TerminalError, baseline.A004TerminalError) as exc:
        print(f"LAC_PI_V1_TERMINAL=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
