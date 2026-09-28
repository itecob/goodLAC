#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from collections import deque
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import scripts.a004_terminal as baseline
import scripts.pi_v1_terminal as legacy
from packages.adapters.pi.production import canonical_project_root, pi_v1_project_application_id
from packages.adapters.pi.tui_owner_gate import PiTuiOwnerGate
from packages.capabilities import PendingPermissionRepository
from packages.policy import StandingPolicyRule
from packages.sandbox import NetworkMode, SandboxMount, SandboxSpec, get_selected_backend
from packages.state import SQLiteStateStore

EXTENSION = REPO_ROOT / "scripts" / "pi_native_tui.mjs"
GOVERNED_PI = REPO_ROOT / "packages" / "adapters" / "pi" / "governed_pi.mjs"
EXPECTED_TOOLS = baseline.EXPECTED_TOOLS
PI_SOURCE_CLI_REL = Path("packages/coding-agent/src/cli.ts")
PI_ROOT_TSCONFIG_REL = Path("tsconfig.json")
TSX_CANDIDATES = (
    Path("node_modules/tsx/dist/cli.mjs"),
    Path("node_modules/tsx/dist/cli.cjs"),
    Path("node_modules/.bin/tsx"),
)
SYNTHETIC_CREDENTIAL_NAME = "LAC_PI005_SYNTHETIC_SERVICE_CREDENTIAL"
SYNTHETIC_CREDENTIAL_VALUE = "SYNTHETIC-PI005-CREDENTIAL-MUST-NOT-INHERIT"
AMBIENT_MARKER = "SYNTHETIC-PI005-AMBIENT-HOST-FILE-MUST-NOT-READ"
RESOURCE_CANARIES = (
    "PI005_PROHIBITED_EXTENSION_LOADED",
    "PI005_PROHIBITED_SKILL",
    "PI005_PROHIBITED_PROMPT",
    "PI005_PROHIBITED_CONTEXT",
)


class PiNativeTuiError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise PiNativeTuiError(message)


def _copy_runtime_binary(binary: Path, rootfs: Path) -> None:
    baseline._copy_binary_and_libraries(binary, rootfs)


def _exact_binary(name: str) -> Path:
    found = shutil.which(name)
    if not found:
        fail(f"{name} is required for the native Pi TUI sandbox")
    path = Path(found).resolve(strict=True)
    if not path.is_file() or path.is_symlink():
        fail(f"{name} must resolve to a canonical regular file")
    return path


def verify_native_cli_entrypoint() -> tuple[Path, Path, Path]:
    source = baseline.PI_CHECKOUT / PI_SOURCE_CLI_REL
    if not source.is_file() or source.is_symlink():
        fail(f"pinned Pi source CLI unavailable: {source}")
    tsconfig = baseline.PI_CHECKOUT / PI_ROOT_TSCONFIG_REL
    if not tsconfig.is_file() or tsconfig.is_symlink():
        fail(f"pinned Pi root tsconfig unavailable: {tsconfig}")
    package = baseline.PI_CHECKOUT / "packages" / "coding-agent" / "package.json"
    try:
        metadata = json.loads(package.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"pinned Pi coding-agent metadata unavailable: {exc}")
    if metadata.get("version") != "0.85.1":
        fail(f"unexpected pinned Pi coding-agent version: {metadata.get('version')!r}")
    checkout = baseline.PI_CHECKOUT.resolve(strict=True)
    for rel in TSX_CANDIDATES:
        candidate = checkout / rel
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        try:
            resolved.relative_to(checkout)
        except ValueError:
            continue
        if resolved.is_file():
            return source, resolved, tsconfig
    fail("checkout-local tsx runtime required for pinned Pi source CLI is unavailable")


def _stage_runtime(rootfs: Path, agent_state: Path, workspace: Path) -> tuple[Path, tuple[SandboxMount, ...]]:
    for rel in ("proc", "dev", "tmp", "lac", "lac/agent", "pi", "nonexistent", "workspace"):
        (rootfs / rel).mkdir(parents=True, exist_ok=True)
    agent_state.mkdir(mode=0o700, parents=True, exist_ok=False)
    agent_state.chmod(0o700)
    node = baseline.exact_node()
    for binary in (node, _exact_binary("fd"), _exact_binary("rg")):
        _copy_runtime_binary(binary, rootfs)

    # Populate conventional resource locations with canaries. The native CLI must
    # ignore these because PI005 supplies explicit --no-* resource flags.
    for base in (rootfs / "workspace" / ".pi", agent_state):
        (base / "extensions").mkdir(parents=True, exist_ok=True)
        (base / "skills" / "canary").mkdir(parents=True, exist_ok=True)
        (base / "prompts").mkdir(parents=True, exist_ok=True)
        (base / "themes").mkdir(parents=True, exist_ok=True)
        (base / "extensions" / "must-not-load.mjs").write_text(
            'throw new Error("PI005_PROHIBITED_EXTENSION_LOADED");\n', encoding="utf-8"
        )
        (base / "skills" / "canary" / "SKILL.md").write_text(
            "---\nname: canary\ndescription: PI005_PROHIBITED_SKILL\n---\n", encoding="utf-8"
        )
        (base / "prompts" / "must-not-load.md").write_text("PI005_PROHIBITED_PROMPT\n", encoding="utf-8")
        (base / "themes" / "must-not-load.json").write_text("{}\n", encoding="utf-8")
    (rootfs / "workspace" / "AGENTS.md").write_text("PI005_PROHIBITED_CONTEXT\n", encoding="utf-8")

    (rootfs / "lac" / "pi_native_tui.mjs").touch()
    (rootfs / "lac" / "governed_pi.mjs").touch()
    return node, (
        SandboxMount(source=baseline.PI_CHECKOUT, target=PurePosixPath("/pi"), writable=False),
        SandboxMount(source=workspace, target=PurePosixPath("/workspace"), writable=False),
        SandboxMount(source=EXTENSION, target=PurePosixPath("/lac/pi_native_tui.mjs"), writable=False),
        SandboxMount(source=GOVERNED_PI, target=PurePosixPath("/lac/governed_pi.mjs"), writable=False),
        SandboxMount(source=agent_state, target=PurePosixPath("/lac/agent"), writable=True),
    )


def _ambient_fixture(root: Path) -> dict[str, Path]:
    host_only = root / "host-only"
    host_only.mkdir(parents=True)
    ambient = host_only / "ambient-sensitive.txt"
    ambient.write_text(AMBIENT_MARKER + "\n", encoding="utf-8")
    process_marker = host_only / "arbitrary-host-process-marker"
    process_marker.unlink(missing_ok=True)
    workspace_probe = root / "host-workspace-probe"
    workspace_probe.mkdir(parents=True)
    probe_read = workspace_probe / "must-not-read.txt"
    probe_read.write_text("PI005-HOST-WORKSPACE-CANARY\n", encoding="utf-8")
    probe_write = workspace_probe / "must-not-write.txt"
    probe_write.unlink(missing_ok=True)
    extension_marker = workspace_probe / "extension-must-not-run.txt"
    extension_marker.unlink(missing_ok=True)
    project_pi = workspace_probe / ".pi" / "extensions"
    project_pi.mkdir(parents=True)
    (project_pi / "escape.mjs").write_text(
        "import { writeFileSync } from 'node:fs';\n"
        f"writeFileSync({json.dumps(str(extension_marker))}, 'extension-ran\\n');\n"
        "export default function () {}\n",
        encoding="utf-8",
    )
    return {
        "ambient": ambient,
        "process_marker": process_marker,
        "probe_read": probe_read,
        "probe_write": probe_write,
        "extension_marker": extension_marker,
    }


def _admin_socket_path() -> Path:
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        return Path(runtime) / "lac" / "admin-v1.sock"
    return Path(f"/run/user/{os.getuid()}") / "lac" / "admin-v1.sock"


def _start_admin_server(state: Path, workspace: Path):
    return legacy.start_admin_server(state, workspace)


def _probe_model_events(request_number: int) -> list[dict[str, Any]]:
    args = json.dumps({"path": "pi005-native-probe.txt", "content": "pi005-native-governed-tui"}, separators=(",", ":"))
    if request_number in (1, 2):
        return [
            {
                "kind": "tool_call_delta",
                "value": [
                    {
                        "index": 0,
                        "id": "pi005-native-fixed-tool-call",
                        "function": {"name": "lac_fs_create", "arguments": args},
                    }
                ],
            },
            {"kind": "finish", "value": "tool_calls"},
            {"kind": "done"},
        ]
    if request_number == 3:
        return [
            {"kind": "text_delta", "value": "PI005_PROFILE_PROBE_DONE"},
            {"kind": "finish", "value": "stop"},
            {"kind": "done"},
        ]
    raise PiNativeTuiError(f"profile probe made unexpected model request #{request_number}")


class AuthorityBroker(legacy.PiV1InteractiveSession):
    def __init__(self, *, workspace: Path, state: Path, trace: Path, mode: str, permission_wait_hook=None) -> None:
        super().__init__(workspace=workspace, state=state, trace=trace, permission_wait_hook=permission_wait_hook)
        self.run_id = f"run:pi005:{uuid.uuid4().hex}"
        self.mode = mode
        self.model_request_count = 0
        self.effect_results: list[dict[str, Any]] = []
        self.owner_gate = PiTuiOwnerGate(
            state=self.state,
            workspace=self.workspace,
            session_id=self.run_id,
            owner_uid=os.getuid(),
            continuation_status=lambda continuation_id: legacy.bridge_continuation_status(
                self.state, self.workspace, continuation_id
            ),
            continuation_resume=lambda continuation_id, expected_message: self._resume_once(
                continuation_id, expected_message=expected_message
            ),
            retry_effect=lambda payload: legacy.bridge_json(
                self.state, self.workspace, self.run_id, payload
            ),
            trace_result=lambda payload, result: self._trace_result(payload, result),
        )

    def close_owner_gate(self) -> None:
        gate = getattr(self, "owner_gate", None)
        if gate is not None:
            gate.close()
            self.owner_gate = None

    def _permission_wait(self, payload, initial_result):
        if self.mode == "probe":
            return super()._permission_wait(payload, initial_result)
        continuation = initial_result.get("workflow_continuation")
        if not isinstance(continuation, Mapping):
            fail("configuration-required effect lacks workflow continuation")
        continuation_id = continuation.get("continuation_id")
        pending_id = continuation.get("pending_id")
        if not isinstance(continuation_id, str) or not continuation_id:
            fail("workflow continuation lacks identity")
        if not isinstance(pending_id, str) or not pending_id:
            fail("workflow continuation lacks pending identity")
        return self.owner_gate.permission_challenge(
            continuation_id,
            pending_id=pending_id,
            expected_message=payload,
        )

    def _effect(self, payload):
        legacy.probe_admin_control_plane(self.state)
        if self.mode == "probe":
            return super()._effect(payload)
        if not isinstance(payload, Mapping):
            fail("effect_request payload must be an object")
        print(f"[tool] {baseline.tool_summary(payload)}", flush=True)
        response = legacy.bridge_json(self.state, self.workspace, self.run_id, payload)
        if response.get("ok") is not True:
            return response
        result = response.get("result")
        if not isinstance(result, Mapping):
            fail("effect result malformed")
        result = dict(result)
        print(legacy.effect_line(result), flush=True)
        permission = result.get("permission_configuration")
        if isinstance(permission, Mapping) and permission.get("required") is True:
            return self._permission_wait(payload, result)
        if (
            result.get("authority_outcome") == "REQUIRE_APPROVAL"
            and result.get("execution_state") == "PENDING_APPROVAL"
        ):
            return self.owner_gate.exact_approval_for_effect(result, payload)
        self._trace_result(payload, result)
        return response

    def handle_rpc(self, kind: object, payload: object) -> object:
        if kind == "model_request":
            self.model_request_count += 1
            if self.mode == "probe":
                raw = json.dumps(payload, sort_keys=True)
                for canary in RESOURCE_CANARIES:
                    if canary in raw:
                        fail(f"prohibited Pi resource entered model context: {canary}")
                return _probe_model_events(self.model_request_count)
            return baseline.model_events(payload)
        if kind == "continuation_list":
            material = {} if payload is None else payload
            if not isinstance(material, Mapping) or set(material) - {"recoverable_only"}:
                fail("native Pi continuation-list request is malformed")
            recoverable_only = material.get("recoverable_only", True)
            if not isinstance(recoverable_only, bool):
                fail("native Pi continuation-list recoverable_only must be boolean")
            response = legacy.bridge_continuation_list(self.state, self.workspace, recoverable_only=recoverable_only)
            if not isinstance(response, Mapping):
                fail("native Pi continuation-list response is malformed")
            if response.get("ok") is not True:
                return dict(response)
            items = response.get("continuations")
            if not isinstance(items, list):
                fail("native Pi continuation-list result is malformed")
            return {"ok": True, "continuations": items}
        if kind == "continuation_resume":
            if not isinstance(payload, Mapping) or set(payload) != {"continuation_id"}:
                fail("native Pi continuation-resume request is malformed")
            continuation_id = payload.get("continuation_id")
            if not isinstance(continuation_id, str) or not continuation_id or continuation_id != continuation_id.strip():
                fail("native Pi continuation-resume identity is invalid")
            response = self._resume_once(continuation_id)
            if not isinstance(response, Mapping):
                fail("native Pi continuation-resume response is malformed")
            return dict(response)
        if kind == "permission_challenge":
            if not isinstance(payload, Mapping) or set(payload) != {"continuation_id"}:
                fail("native Pi permission-challenge request is malformed")
            return self.owner_gate.permission_challenge(payload["continuation_id"])
        if kind == "permission_decide":
            if not isinstance(payload, Mapping) or set(payload) != {"challenge_id", "choice"}:
                fail("native Pi permission-decision request is malformed")
            return self.owner_gate.permission_decide(payload["challenge_id"], payload["choice"])
        if kind == "permission_cancel":
            if not isinstance(payload, Mapping) or set(payload) != {"challenge_id"}:
                fail("native Pi permission-cancel request is malformed")
            return self.owner_gate.permission_cancel(payload["challenge_id"])
        if kind == "continuation_approval_challenge":
            if not isinstance(payload, Mapping) or set(payload) != {"continuation_id"}:
                fail("native Pi continuation approval request is malformed")
            return self.owner_gate.continuation_approval_challenge(payload["continuation_id"])
        if kind == "approval_decide":
            if not isinstance(payload, Mapping) or set(payload) != {"challenge_id", "approve"}:
                fail("native Pi exact-approval request is malformed")
            return self.owner_gate.approval_decide(payload["challenge_id"], payload["approve"])
        if kind == "effect_request":
            result = self._effect(payload)
            if isinstance(result, dict):
                self.effect_results.append(dict(result))
            return result
        fail(f"native Pi requested unsupported host capability: {kind!r}")


class BrokerProcess:
    def __init__(self, *, workspace: Path, state: Path, trace: Path, mode: str, permission_wait_hook=None) -> None:
        self.workspace = canonical_project_root(workspace)
        self.state = state.resolve()
        self.trace = trace.resolve()
        self.mode = mode
        self.authority = AuthorityBroker(
            workspace=self.workspace,
            state=self.state,
            trace=self.trace,
            mode=mode,
            permission_wait_hook=permission_wait_hook,
        )
        self.proc: subprocess.Popen[bytes] | None = None
        self.host_sock: socket.socket | None = None
        self.broker_listener: socket.socket | None = None
        self.broker_path: Path | None = None
        self.tempdir: tempfile.TemporaryDirectory[str] | None = None
        self.listener: baseline.ListenerProbe | None = None
        self.fixture: dict[str, Path] | None = None
        self.ready: dict[str, Any] | None = None
        self.stderr_tail: deque[str] = deque(maxlen=120)
        self.stderr_thread: threading.Thread | None = None
        self.last_broker_phase = "constructed"


    def _stderr_text(self) -> str:
        return "".join(self.stderr_tail)[-12000:]

    def _child_failure(self, message: str) -> None:
        diagnostics = (
            f"broker_phase={self.last_broker_phase} "
            f"model_requests={self.authority.model_request_count} "
            f"effects={len(self.authority.effect_results)}"
        )
        tail = self._stderr_text().strip()
        if tail:
            fail(f"{message}; {diagnostics}; native Pi stderr tail:\n{tail}")
        fail(f"{message}; {diagnostics}")

    def _capture_stderr(self) -> None:
        if self.proc is None or self.proc.stderr is None:
            return
        while True:
            chunk = self.proc.stderr.readline()
            if not chunk:
                return
            text = chunk.decode("utf-8", errors="replace")
            self.stderr_tail.append(text)
            try:
                sys.stderr.write(text)
                sys.stderr.flush()
            except Exception:
                pass

    def _send(self, value: Mapping[str, Any]) -> None:
        if self.host_sock is None:
            fail("native Pi broker socket unavailable")
        self.host_sock.sendall(json.dumps(dict(value), sort_keys=True).encode("utf-8") + b"\n")

    def _recv(self, timeout: float | None = 360.0) -> dict[str, Any]:
        if self.host_sock is None:
            fail("native Pi broker socket unavailable")
        deadline = None if timeout is None else time.monotonic() + timeout
        parts: list[bytes] = []
        size = 0
        while True:
            if self.proc is not None and self.proc.poll() is not None:
                if self.proc.returncode == 0:
                    raise EOFError("native Pi exited cleanly")
                self._child_failure(f"native Pi exited {self.proc.returncode} while broker was waiting")
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                self._child_failure("timed out waiting for native Pi broker message")
            self.host_sock.settimeout(0.25 if remaining is None else min(0.25, remaining))
            try:
                chunk = self.host_sock.recv(1)
            except socket.timeout:
                continue
            if not chunk:
                if self.proc is not None:
                    grace_deadline = time.monotonic() + 2.0
                    while self.proc.poll() is None and time.monotonic() < grace_deadline:
                        time.sleep(0.05)
                    if self.proc.poll() == 0:
                        self.last_broker_phase = "broker_eof_after_clean_exit"
                        raise EOFError("native Pi broker closed after clean exit")
                    if self.proc.poll() is not None:
                        self._child_failure(f"native Pi broker closed with child rc={self.proc.returncode}")
                self._child_failure("native Pi broker closed unexpectedly")
            if chunk == b"\n":
                break
            parts.append(chunk)
            size += 1
            if size > 16 * 1024 * 1024:
                fail("native Pi broker message exceeded size limit")
        try:
            value = json.loads(b"".join(parts).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            fail(f"native Pi broker emitted malformed JSON: {exc}")
        if not isinstance(value, dict):
            fail("native Pi broker message must be an object")
        return value

    def _verify_ready(self, value: Mapping[str, Any]) -> None:
        if tuple(value.get("tool_surface") or ()) != EXPECTED_TOOLS:
            fail("native Pi tool surface is not exactly the four governed tools")
        if tuple(value.get("owner_commands") or ()) != ("lac-continuations", "lac-resume"):
            fail("native Pi owner recovery command surface is unexpected")
        if value.get("frontend") != "PiSourceCLI" or value.get("entrypoint") != "/pi/packages/coding-agent/src/cli.ts":
            fail("native Pi did not start through the pinned Pi source CLI")
        resources = value.get("resources")
        expected = {
            "extension_discovery": False,
            "skills": False,
            "prompt_templates": False,
            "themes": False,
            "context_files": False,
            "session_persistence": False,
        }
        if resources != expected:
            fail(f"native Pi resource lockdown report is unexpected: {resources!r}")
        probes = value.get("probes")
        if not isinstance(probes, Mapping):
            fail("native Pi ambient conformance probes are missing")
        prohibited = (
            "host_file_readable",
            "host_workspace_readable",
            "host_workspace_write_effect",
            "synthetic_service_credential_inherited",
            "arbitrary_host_executable_launched",
            "loopback_connected",
            "private_network_connected",
            "admin_socket_visible",
        )
        failures = {key: probes.get(key) for key in prohibited if probes.get(key) is not False}
        if failures:
            fail(f"native Pi ambient-authority conformance failed: {failures}")
        if SYNTHETIC_CREDENTIAL_VALUE in json.dumps(value, sort_keys=True):
            fail("synthetic credential entered Pi-visible evidence")
        assert self.fixture is not None
        for key in ("process_marker", "probe_write", "extension_marker"):
            if self.fixture[key].exists():
                fail(f"host verification observed prohibited effect: {key}")

    def start(self) -> dict[str, Any]:
        backend = get_selected_backend()
        if backend.backend_id != "bubblewrap":
            fail("PI005 is bound to the accepted H001 bubblewrap backend")
        baseline.verify_accepted_pins()
        source_cli, tsx_cli, root_tsconfig = verify_native_cli_entrypoint()
        if not EXTENSION.is_file() or not GOVERNED_PI.is_file():
            fail("PI005 trusted extension or governed Pi adapter is unavailable")
        self.workspace = canonical_project_root(self.workspace)
        self.trace.parent.mkdir(parents=True, exist_ok=True)
        self.listener = baseline.ListenerProbe()
        self.tempdir = tempfile.TemporaryDirectory(prefix="lac-pi005-native-tui-")
        tmp_root = Path(self.tempdir.name)
        rootfs = tmp_root / "rootfs"
        rootfs.mkdir()
        self.fixture = _ambient_fixture(tmp_root)
        agent_state = tmp_root / "agent-state"
        node, mounts = _stage_runtime(rootfs, agent_state, self.workspace)
        self.broker_path = rootfs / "lac" / "broker.sock"
        self.broker_listener = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.broker_listener.bind(str(self.broker_path))
        os.chmod(self.broker_path, 0o600)
        self.broker_listener.listen(1)
        self.last_broker_phase = "broker_listening"
        spec = SandboxSpec(
            runtime_root=rootfs,
            instance_id="pi005-" + hashlib.sha256(self.authority.run_id.encode("utf-8")).hexdigest()[:20],
            mounts=mounts,
            environment={
                "HOME": "/nonexistent",
                "LC_ALL": "C.UTF-8",
                "PATH": "/usr/bin",
                "PI_CODING_AGENT_DIR": "/lac/agent",
                "PI_OFFLINE": "1",
                "PI_SKIP_VERSION_CHECK": "1",
                "PI_TELEMETRY": "0",
                "LAC_PI005_BROKER_SOCKET": "/lac/broker.sock",
                "TERM": os.environ.get("TERM", "xterm-256color"),
            },
            cwd=PurePosixPath("/workspace"),
            network=NetworkMode.NONE,
        )
        tsx_rel = tsx_cli.relative_to(baseline.PI_CHECKOUT.resolve(strict=True))
        source_rel = source_cli.relative_to(baseline.PI_CHECKOUT.resolve(strict=True))
        tsconfig_rel = root_tsconfig.relative_to(baseline.PI_CHECKOUT.resolve(strict=True))
        pi_args = [
            str(node),
            "/pi/" + tsx_rel.as_posix(),
            "--tsconfig", "/pi/" + tsconfig_rel.as_posix(),
            "/pi/" + source_rel.as_posix(),
            "--no-builtin-tools",
            "--tools", ",".join(EXPECTED_TOOLS),
            "--no-extensions", "-e", "/lac/pi_native_tui.mjs",
            "--no-skills",
            "--no-prompt-templates",
            "--no-themes",
            "--no-context-files",
            "--no-session",
            "--provider", "lac-freetoken",
            "--model", baseline.SERVED_MODEL_ID,
            "--system-prompt", legacy.system_prompt(),
        ]
        if self.mode == "probe":
            pi_args += ["--print", "PI005 deterministic governed native CLI probe"]
        raw_argv = list(backend.build_argv(spec, pi_args))
        launcher_env = dict(os.environ)
        launcher_env[SYNTHETIC_CREDENTIAL_NAME] = SYNTHETIC_CREDENTIAL_VALUE
        self.last_broker_phase = "launching_native_pi"
        self.proc = subprocess.Popen(
            raw_argv,
            cwd=REPO_ROOT,
            env=launcher_env,
            close_fds=True,
            stderr=subprocess.PIPE if self.mode == "probe" else None,
        )
        if self.mode == "probe":
            self.stderr_thread = threading.Thread(target=self._capture_stderr, daemon=True)
            self.stderr_thread.start()
        assert self.broker_listener is not None
        deadline = time.monotonic() + 60
        while self.host_sock is None:
            if self.proc.poll() is not None:
                self._child_failure(f"native Pi exited {self.proc.returncode} before broker connection")
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                self._child_failure("timed out waiting for native Pi broker connection")
            self.broker_listener.settimeout(min(0.25, remaining))
            try:
                connection, _ = self.broker_listener.accept()
            except socket.timeout:
                continue
            self.host_sock = connection
            self.last_broker_phase = "broker_connected"
        self.broker_listener.close()
        self.broker_listener = None
        self._send({
            "type": "bootstrap",
            "mode": self.mode,
            "modelId": baseline.SERVED_MODEL_ID,
            "timeoutSeconds": 300,
            "hostFilePath": str(self.fixture["ambient"]),
            "workspaceProbeReadPath": str(self.fixture["probe_read"]),
            "workspaceProbeWritePath": str(self.fixture["probe_write"]),
            "processMarkerPath": str(self.fixture["process_marker"]),
            "syntheticCredentialName": SYNTHETIC_CREDENTIAL_NAME,
            "loopbackPort": self.listener.port,
            "adminSocketPath": str(_admin_socket_path()),
        })
        self.last_broker_phase = "awaiting_extension_ready"
        ready = self._recv(60)
        if ready.get("type") != "ready":
            fail(f"native Pi did not emit ready: {ready!r}")
        self._verify_ready(ready)
        self.ready = dict(ready)
        self._send({"type": "ready_ack", "ok": True})
        self.last_broker_phase = "ready_ack_sent"
        return dict(ready)

    def serve(self) -> None:
        if self.proc is None:
            fail("native Pi process is not started")
        receive_timeout = 45.0 if self.mode == "probe" else None
        while self.proc.poll() is None:
            self.last_broker_phase = (
                f"awaiting_rpc:model_requests={self.authority.model_request_count}:"
                f"effects={len(self.authority.effect_results)}"
            )
            try:
                message = self._recv(receive_timeout)
            except EOFError:
                break
            except PiNativeTuiError as exc:
                if self.proc.poll() is not None:
                    break
                raise exc
            if message.get("type") != "rpc":
                fail(f"unexpected native Pi broker message: {message!r}")
            rpc_id = message.get("id")
            if not isinstance(rpc_id, str) or not rpc_id:
                fail("native Pi RPC is missing identity")
            kind = message.get("kind")
            self.last_broker_phase = f"handling_rpc:{kind}"
            try:
                handled = self.authority.handle_rpc(kind, message.get("payload"))
                response = {"type": "rpc_response", "id": rpc_id, "ok": True, "payload": handled}
            except BaseException as exc:
                response = {"type": "rpc_response", "id": rpc_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
            self._send(response)
            self.last_broker_phase = (
                f"served_rpc:{kind}:model_requests={self.authority.model_request_count}:"
                f"effects={len(self.authority.effect_results)}"
            )
        rc = self.proc.wait(timeout=30)
        self.last_broker_phase = f"child_exited:rc={rc}"
        if rc != 0:
            self._child_failure(f"native Pi TUI process exited {rc}")

    def close(self) -> None:
        if self.proc is not None and self.proc.poll() is None:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill(); self.proc.wait(timeout=5)
        self.authority.close_owner_gate()
        for sock in (self.host_sock, self.broker_listener):
            if sock is not None:
                try: sock.close()
                except OSError: pass
        self.host_sock = None
        self.broker_listener = None
        if self.stderr_thread is not None:
            self.stderr_thread.join(timeout=1)
            self.stderr_thread = None
        self.broker_path = None
        if self.listener is not None:
            self.listener.close(); self.listener = None
        if self.tempdir is not None:
            self.tempdir.cleanup(); self.tempdir = None

    def __enter__(self) -> "BrokerProcess":
        self.start(); return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def _unwrap_native_effect_result(value: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        fail("native Pi effect observation is not an object")
    if value.get("ok") is True:
        inner = value.get("result")
        if not isinstance(inner, Mapping):
            fail(f"native Pi broker effect envelope lacks native result: {dict(value)!r}")
        return dict(inner)
    if "authority_outcome" in value and "execution_state" in value:
        return dict(value)
    fail(f"native Pi effect observation has unexpected shape: {dict(value)!r}")


def _profile_permission_hook(status: Mapping[str, Any], workspace: Path) -> None:
    rule = StandingPolicyRule.create(
        rule_id="pi005-native-probe-allow-create",
        application_id=pi_v1_project_application_id(workspace),
        skill_id=legacy.PI_V1_SKILL_ID,
        action="filesystem.create",
        resource_selector="filesystem:workspace",
        decision="ALLOW",
    )
    client = legacy.LacctlClient()
    client.call("permissions.replace", {"rules": [rule.to_material()], "defaults": []})
    client.call("pending.resolve", {"pending_id": status["pending_id"], "resolution": "POLICY_UPDATED"})


def run_profile_probe(workspace: Path, state: Path, trace: Path) -> int:
    target = workspace / "pi005-native-probe.txt"
    target.unlink(missing_ok=True)
    observed_waits: list[dict[str, Any]] = []
    configured_workflow: tuple[str, str] | None = None

    def hook(status: Mapping[str, Any]) -> None:
        nonlocal configured_workflow
        snapshot = dict(status)
        observed_waits.append(snapshot)
        continuation_id = snapshot.get("continuation_id")
        pending_id = snapshot.get("pending_id")
        if not isinstance(continuation_id, str) or not continuation_id or not isinstance(pending_id, str) or not pending_id:
            fail("native Pi permission wait lacks stable continuation/pending identity")
        workflow = (continuation_id, pending_id)
        if configured_workflow is None:
            configured_workflow = workflow
            _profile_permission_hook(snapshot, workspace)
        elif workflow != configured_workflow:
            fail("native Pi duplicate probe entered a second permission workflow")
        # A duplicate call may re-observe the same already-resolved continuation.
        # Do not repeat owner policy mutation; _permission_wait will resume the same workflow.

    with BrokerProcess(workspace=workspace, state=state, trace=trace, mode="probe", permission_wait_hook=hook) as native:
        native.serve()
        effects = native.authority.effect_results
        if len(effects) != 2:
            fail(f"native Pi profile probe expected two governed effect executions, observed {len(effects)}")
        first_envelope, second_envelope = effects
        first = _unwrap_native_effect_result(first_envelope)
        second = _unwrap_native_effect_result(second_envelope)
        if not observed_waits or configured_workflow is None:
            fail("native Pi path did not enter the required permission configuration workflow")
        unique_workflows = {
            (item.get("continuation_id"), item.get("pending_id"))
            for item in observed_waits
        }
        if unique_workflows != {configured_workflow}:
            fail(f"native Pi path observed multiple permission workflows: {sorted(unique_workflows)!r}")
        if first.get("authority_outcome") != "ALLOW" or first.get("execution_state") != "SUCCEEDED":
            fail(f"native Pi fresh continued request failed: {first!r}")
        continuation = first.get("workflow_continuation")
        if not isinstance(continuation, Mapping):
            fail("native Pi fresh result lacks continuation status")
        original_request = continuation.get("original_request_id")
        fresh_request = continuation.get("fresh_request_id")
        if not isinstance(original_request, str) or not isinstance(fresh_request, str) or original_request == fresh_request:
            fail("native Pi continuation request identities are invalid")
        store = SQLiteStateStore(state)
        try:
            closure = PendingPermissionRepository(store).get_closure(original_request)
        finally:
            store.close()
        if closure is None:
            fail("native Pi original permission-denied request lost terminal closure")
        if second.get("replayed") is not True or second.get("request_id") != fresh_request:
            fail("native Pi duplicate effect did not replay the one fresh terminal receipt")
        first_receipt = first.get("receipt")
        second_receipt = second.get("receipt")
        if not isinstance(first_receipt, Mapping) or not isinstance(second_receipt, Mapping):
            fail("native Pi governed effect results lack durable receipts")
        if first_receipt.get("receipt_id") != second_receipt.get("receipt_id"):
            fail("native Pi duplicate effect changed the fresh terminal receipt identity")
        if target.read_text(encoding="utf-8") != "pi005-native-governed-tui":
            fail("native Pi governed filesystem effect produced unexpected content")
        assert native.ready is not None
        print(f"native_tui=PiSourceCLI pi_pid={native.ready.get('probes',{}).get('pid')} sandbox=bubblewrap network=none")
        print("entrypoint=/pi/packages/coding-agent/src/cli.ts")
        print("tools=" + ",".join(EXPECTED_TOOLS))
        print("resources=extension_discovery:off,skills:off,prompts:off,themes:off,context_files:off,sessions:off")
        print("LAC_PI005_NATIVE_TUI_CLI=PASS")
        print("LAC_PI005_RESOURCE_LOADING_CLOSED=PASS")
        print("LAC_PI005_AMBIENT_BOUNDARY=PASS")
        print("LAC_PI005_GOVERNED_TOOL_PATH=PASS")
        print("LAC_PI005_PERMISSION_WORKFLOW_UNIQUE=PASS")
        print("LAC_PI005_DUPLICATE_RECEIPT_REPLAY=PASS")
        print("LAC_PI005_PROFILE_PROBE=PASS")
    return 0


def run_interactive(workspace: Path, state: Path, trace: Path, runtime_mode: str) -> int:
    with BrokerProcess(workspace=workspace, state=state, trace=trace, mode="interactive") as native:
        print("LAC-governed native Pi CLI/TUI: exact pinned Pi source CLI inside Bubblewrap; effects remain controller-backed.", flush=True)
        print(f"runtime={runtime_mode} model={baseline.SERVED_MODEL_ID} sandbox=bubblewrap network=none tools={','.join(EXPECTED_TOOLS)}", flush=True)
        native.serve()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Native Pi CLI/TUI bound to the LAC-governed v1 authority path")
    parser.add_argument("--workspace", type=Path, default=Path.cwd())
    parser.add_argument("--state", type=Path, default=legacy.default_state())
    parser.add_argument("--trace", type=Path, default=legacy.default_trace())
    parser.add_argument("--runtime", choices=("manage", "external"), default="manage")
    parser.add_argument("--profile-probe", action="store_true")
    parser.add_argument("--control-plane-attach-probe-seconds", type=float)
    args = parser.parse_args()

    workspace = canonical_project_root(args.workspace)
    state = args.state.expanduser().resolve()
    trace = args.trace.expanduser().resolve()
    legacy.initialize_state(state, workspace)
    admin = None
    runtime = None
    try:
        admin = _start_admin_server(state, workspace)
        if args.control_plane_attach_probe_seconds is not None:
            hold = args.control_plane_attach_probe_seconds
            if hold < 0 or hold > 30:
                fail("control-plane attach probe duration must be between 0 and 30 seconds")
            print(
                json.dumps(
                    {
                        "schema": "goodlac.r5-r001-native-host-attach/v1",
                        "pid": os.getpid(),
                        "workspace": str(workspace),
                        "application_id": pi_v1_project_application_id(workspace),
                        "control_plane_pid": admin.server_pid,
                    },
                    sort_keys=True,
                ),
                flush=True,
            )
            time.sleep(hold)
            return 0
        if args.profile_probe:
            return run_profile_probe(workspace, state, trace)
        runtime_mode = "external"
        if args.runtime == "manage":
            runtime = baseline.FreeTokenRuntime(); runtime_mode = runtime.ensure()
        else:
            exact, detail = baseline.probe_exact_endpoint(baseline.runtime_assets())
            if not exact:
                fail(f"external FreeToken endpoint is not exact accepted runtime: {detail}")
        return run_interactive(workspace, state, trace, runtime_mode)
    finally:
        if runtime is not None: runtime.stop()
        if args.profile_probe and admin is not None:
            legacy.stop_owned_admin_control_plane(admin)
        else:
            legacy.stop_admin_server(admin)


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nLAC_PI005_NATIVE_TUI_SHUTDOWN=INTERRUPTED_CLEAN")
        raise SystemExit(130)
    except (PiNativeTuiError, legacy.PiV1TerminalError, baseline.A004TerminalError) as exc:
        print(f"LAC_PI005_NATIVE_TUI=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
