#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import queue
import readline  # noqa: F401 -- importing installs GNU Readline input handling on Linux
import signal
import selectors
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time
import uuid
from pathlib import Path, PurePosixPath
from typing import Any, Mapping

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.effects.shell.adapter import _copy_binary_and_libraries
from packages.sandbox import NetworkMode, SandboxMount, SandboxSpec, get_selected_backend
from packages.state import EffectReceiptRepository, SQLiteStateStore

from scripts.a004_freetoken_launcher import (
    BASE_URL,
    SERVED_MODEL_ID,
    FreeTokenRuntime,
    probe_exact_endpoint,
    runtime_assets,
)

EXPECTED_TOOLS = ("lac_fs_read", "lac_fs_create", "lac_fs_replace", "lac_shell_exec")
PI_CHECKOUT = Path(
    os.environ.get(
        "LAC_PI_CHECKOUT",
        str(Path.home() / ".cache/local-agent-controller/phase0/upstream/pi"),
    )
).expanduser().resolve()
PYTHON = os.environ.get("LAC_A003_PYTHON", sys.executable)
MODEL_BRIDGE = REPO_ROOT / "scripts" / "a003_model_provider_stream.py"
EFFECT_BRIDGE = REPO_ROOT / "scripts" / "a003_controller_bridge.py"
WORKER = REPO_ROOT / "scripts" / "a004_agent_worker.mjs"
GOVERNED_PI = REPO_ROOT / "packages" / "adapters" / "pi" / "governed_pi.mjs"
SYNTHETIC_CREDENTIAL_NAME = "LAC_A004_SYNTHETIC_SERVICE_CREDENTIAL"
SYNTHETIC_CREDENTIAL_VALUE = "SYNTHETIC-A004-CREDENTIAL-MUST-NOT-INHERIT"
AMBIENT_MARKER = "SYNTHETIC-A004-AMBIENT-HOST-FILE-MUST-NOT-READ"


class A004TerminalError(RuntimeError):
    pass


class A004InputRejected(ValueError):
    pass


def validate_terminal_input(text: str) -> str:
    """Reject residual terminal controls before they can enter the Pi/model JSON path."""
    if not isinstance(text, str):
        raise TypeError("terminal input must be text")
    for character in text:
        codepoint = ord(character)
        if (codepoint < 0x20 and character != "\t") or 0x7F <= codepoint <= 0x9F:
            raise A004InputRejected(
                "terminal control characters are not allowed; edit the line and retry"
            )
    return text


def read_terminal_input(prompt: str) -> str:
    return input(prompt)


def fail(message: str) -> None:
    raise A004TerminalError(message)


def verify_accepted_pins() -> None:
    for script, label in (("verify_pi_pin.py", "Pi"), ("verify_freetoken_pin.py", "FreeToken")):
        proc = subprocess.run(
            [PYTHON, str(REPO_ROOT / "scripts" / script)],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=REPO_ROOT,
            env={**os.environ, "LAC_REPO_ROOT": str(REPO_ROOT)},
            timeout=30,
            check=False,
        )
        if proc.returncode != 0:
            fail(f"accepted {label} pin verification failed: {proc.stdout.strip()[-1600:]}")


def exact_node() -> Path:
    found = shutil.which("node")
    if not found:
        fail("Node.js is required for the pinned Pi process")
    node = Path(found).resolve(strict=True)
    if not node.is_file() or node.is_symlink():
        fail("Node.js executable must resolve to a canonical regular file")
    return node


def sanitized_provider_environment() -> dict[str, str]:
    env = dict(os.environ)
    exact = {
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GITHUB_TOKEN", "GH_TOKEN",
        "AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN",
        "GOOGLE_API_KEY", "AZURE_OPENAI_API_KEY", "SSH_AUTH_SOCK",
        SYNTHETIC_CREDENTIAL_NAME,
    }
    prefixes = (
        "OPENAI_", "ANTHROPIC_", "AWS_", "AZURE_", "GOOGLE_", "HF_",
        "HUGGINGFACE_", "HUGGING_FACE_", "GITHUB_", "GH_", "SSH_",
    )
    suffixes = (
        "_API_KEY", "_ACCESS_TOKEN", "_TOKEN", "_SECRET", "_PASSWORD",
        "_CREDENTIAL", "_CREDENTIALS",
    )
    for key in tuple(env):
        upper = key.upper()
        if key in exact or upper in exact or upper.startswith(prefixes) or upper.endswith(suffixes):
            env.pop(key, None)
    env["LAC_A003_FREETOKEN_URL"] = BASE_URL
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def child_json(executable: str, args: list[str], payload: object | None) -> dict[str, Any]:
    proc = subprocess.run(
        [executable, *args],
        input="" if payload is None else json.dumps(payload),
        text=True,
        capture_output=True,
        timeout=90,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"{Path(executable).name} exited {proc.returncode}: {proc.stderr.strip()[-1600:]}")
    try:
        value = json.loads(proc.stdout.strip())
    except json.JSONDecodeError as exc:
        fail(f"child returned invalid JSON: {exc}; stderr={proc.stderr.strip()[-800:]}")
    if not isinstance(value, dict):
        fail("child JSON result must be an object")
    return value


def model_events(payload: object) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        fail("model_request payload must be an object")
    proc = subprocess.run(
        [PYTHON, str(MODEL_BRIDGE)],
        input=json.dumps(dict(payload)),
        text=True,
        capture_output=True,
        env=sanitized_provider_environment(),
        timeout=330,
        check=False,
    )
    if proc.returncode != 0:
        fail(f"LAC ModelProvider bridge exited {proc.returncode}: {proc.stderr.strip()[-1600:]}")
    events: list[dict[str, Any]] = []
    for raw in proc.stdout.splitlines():
        if not raw.strip():
            continue
        try:
            event = json.loads(raw)
        except json.JSONDecodeError as exc:
            fail(f"LAC ModelProvider bridge emitted invalid JSON: {exc}")
        if not isinstance(event, dict) or not isinstance(event.get("kind"), str):
            fail("LAC ModelProvider bridge emitted malformed event")
        events.append(event)
    if not events or events[-1].get("kind") != "done":
        fail("LAC ModelProvider bridge did not terminate with done")
    return events


def _stage_runtime(rootfs: Path) -> tuple[Path, tuple[SandboxMount, ...]]:
    for rel in ("proc", "dev", "tmp", "lac", "pi", "nonexistent"):
        (rootfs / rel).mkdir(parents=True, exist_ok=True)
    node = exact_node()
    _copy_binary_and_libraries(node, rootfs)
    worker_target = rootfs / "lac" / "worker.mjs"
    governed_target = rootfs / "lac" / "governed_pi.mjs"
    worker_target.touch()
    governed_target.touch()
    return node, (
        SandboxMount(source=PI_CHECKOUT, target=PurePosixPath("/pi"), writable=False),
        SandboxMount(source=WORKER, target=PurePosixPath("/lac/worker.mjs"), writable=False),
        SandboxMount(source=GOVERNED_PI, target=PurePosixPath("/lac/governed_pi.mjs"), writable=False),
    )


class ListenerProbe:
    def __init__(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind(("127.0.0.1", 0))
        self.socket.listen(2)
        self.socket.settimeout(0.2)
        self.port = int(self.socket.getsockname()[1])
        self.accepted = False
        self.stop_event = threading.Event()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def _run(self) -> None:
        while not self.stop_event.is_set():
            try:
                conn, _ = self.socket.accept()
            except socket.timeout:
                continue
            except OSError:
                return
            else:
                self.accepted = True
                conn.close()

    def close(self) -> None:
        time.sleep(0.05)
        self.stop_event.set()
        try:
            self.socket.close()
        except OSError:
            pass
        self.thread.join(timeout=1)


def stderr_reader(pipe: Any, output: queue.SimpleQueue[str]) -> None:
    try:
        for line in pipe:
            output.put(line)
    except Exception as exc:
        output.put(f"stderr-reader-error: {exc}\n")


def stderr_text(output: queue.SimpleQueue[str], limit: int = 12000) -> str:
    parts: list[str] = []
    while True:
        try:
            parts.append(output.get_nowait())
        except queue.Empty:
            break
    return "".join(parts)[-limit:]


def tool_summary(payload: Mapping[str, Any]) -> str:
    name = str(payload.get("toolName", "?"))
    args = payload.get("arguments")
    if not isinstance(args, Mapping):
        return name
    if name.startswith("lac_fs_"):
        return f"{name} path={args.get('path')!r}"
    if name == "lac_shell_exec":
        return f"{name} executable={args.get('executable')!r} argv={args.get('argv')!r} cwd={args.get('cwd')!r}"
    return name


def receipt_for_request(state: Path, request_id: str | None) -> dict[str, Any] | None:
    if not request_id:
        return None
    store = SQLiteStateStore(state)
    try:
        receipt = EffectReceiptRepository(store).get_receipt_for_request(request_id)
        return receipt.to_record() if receipt is not None else None
    finally:
        store.close()


class InteractiveSession:
    def __init__(self, *, workspace: Path, state: Path, trace: Path, system_prompt: str) -> None:
        self.workspace = workspace.resolve()
        self.state = state.resolve()
        self.trace = trace.resolve()
        self.system_prompt = system_prompt
        self.run_id = f"run:a004:{uuid.uuid4().hex}"
        self.proc: subprocess.Popen[str] | None = None
        self.stderr_lines: queue.SimpleQueue[str] = queue.SimpleQueue()
        self.stderr_thread: threading.Thread | None = None
        self.listener: ListenerProbe | None = None
        self.tempdir: tempfile.TemporaryDirectory[str] | None = None
        self.turn = 0
        self.model_request_count = 0
        self.pi_pid: int | None = None

    def _write(self, value: Mapping[str, Any]) -> None:
        if self.proc is None or self.proc.stdin is None:
            fail("Pi process stdin unavailable")
        self.proc.stdin.write(json.dumps(dict(value), sort_keys=True) + "\n")
        self.proc.stdin.flush()

    def _read(self, timeout: float) -> dict[str, Any]:
        if self.proc is None or self.proc.stdout is None:
            fail("Pi process stdout unavailable")
        selector = selectors.DefaultSelector()
        selector.register(self.proc.stdout, selectors.EVENT_READ)
        try:
            ready = selector.select(timeout=timeout)
            if not ready:
                if self.proc.poll() is not None:
                    fail(f"sandboxed Pi exited {self.proc.returncode}: {stderr_text(self.stderr_lines)}")
                fail("timed out waiting for sandboxed Pi protocol message")
            line = self.proc.stdout.readline()
        finally:
            selector.close()
        if not line:
            fail(f"sandboxed Pi closed protocol output: {stderr_text(self.stderr_lines)}")
        try:
            value = json.loads(line)
        except json.JSONDecodeError as exc:
            fail(f"sandboxed Pi emitted invalid protocol JSON: {exc}: {line[:300]!r}")
        if not isinstance(value, dict):
            fail("sandboxed Pi protocol message must be an object")
        if value.get("type") == "fatal":
            fail(f"sandboxed Pi fatal: {value.get('error')}")
        return value

    def _ambient_fixture(self, root: Path) -> dict[str, Any]:
        host_only = root / "host-only"
        host_only.mkdir(parents=True)
        ambient = host_only / "ambient-sensitive.txt"
        ambient.write_text(AMBIENT_MARKER + "\n", encoding="utf-8")
        process_marker = host_only / "arbitrary-host-process-marker"
        process_marker.unlink(missing_ok=True)
        probe_dir = root / "ambient-workspace-probe"
        probe_dir.mkdir(parents=True)
        probe_read = probe_dir / "must-use-governed-read.txt"
        probe_read.write_text("A004-WORKSPACE-BYPASS-CANARY\n", encoding="utf-8")
        probe_write = probe_dir / "ambient-write-must-not-exist.txt"
        probe_write.unlink(missing_ok=True)
        return {
            "ambient": ambient,
            "process_marker": process_marker,
            "probe_read": probe_read,
            "probe_write": probe_write,
        }

    def start(self) -> dict[str, Any]:
        backend = get_selected_backend()
        if backend.backend_id != "bubblewrap":
            fail("A004 is bound to the accepted H001 bubblewrap backend")
        if not PI_CHECKOUT.is_dir() or not WORKER.is_file() or not GOVERNED_PI.is_file():
            fail("accepted Pi checkout or A004 worker source unavailable")
        self.workspace.mkdir(parents=True, exist_ok=True)
        self.workspace.chmod(0o700)
        self.state.parent.mkdir(parents=True, exist_ok=True)
        self.trace.parent.mkdir(parents=True, exist_ok=True)
        if not self.state.exists():
            child_json(PYTHON, [str(EFFECT_BRIDGE), "init", "--state", str(self.state), "--workspace", str(self.workspace)], None)
        self.listener = ListenerProbe()
        self.tempdir = tempfile.TemporaryDirectory(prefix="lac-a004-agent-runtime-")
        tmp_root = Path(self.tempdir.name)
        rootfs = tmp_root / "rootfs"
        rootfs.mkdir()
        fixture = self._ambient_fixture(tmp_root)
        node, mounts = _stage_runtime(rootfs)
        spec = SandboxSpec(
            runtime_root=rootfs,
            instance_id="a004-pi-" + hashlib.sha256(self.run_id.encode("utf-8")).hexdigest()[:20],
            mounts=mounts,
            environment={"HOME": "/nonexistent", "LC_ALL": "C", "PATH": "/usr/bin"},
            cwd=PurePosixPath("/lac"),
            network=NetworkMode.NONE,
        )
        argv = backend.build_argv(spec, [str(node), "/lac/worker.mjs"])
        launcher_env = dict(os.environ)
        launcher_env[SYNTHETIC_CREDENTIAL_NAME] = SYNTHETIC_CREDENTIAL_VALUE
        self.proc = subprocess.Popen(
            argv,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            env=launcher_env,
        )
        assert self.proc.stdin is not None and self.proc.stdout is not None and self.proc.stderr is not None
        self.stderr_thread = threading.Thread(target=stderr_reader, args=(self.proc.stderr, self.stderr_lines), daemon=True)
        self.stderr_thread.start()
        self._write({
            "type": "bootstrap",
            "mode": "interactive",
            "modelId": SERVED_MODEL_ID,
            "timeoutSeconds": 300,
            "systemPrompt": self.system_prompt,
            "hostFilePath": str(fixture["ambient"]),
            "workspaceProbeReadPath": str(fixture["probe_read"]),
            "workspaceProbeWritePath": str(fixture["probe_write"]),
            "syntheticCredentialName": SYNTHETIC_CREDENTIAL_NAME,
            "processMarkerPath": str(fixture["process_marker"]),
            "loopbackPort": self.listener.port,
        })
        ready = self._read(30)
        if ready.get("type") != "ready":
            fail(f"sandboxed Pi did not emit ready: {ready!r}")
        if tuple(ready.get("tool_surface") or ()) != EXPECTED_TOOLS:
            fail("Pi tool surface is not exactly the four accepted governed tools")
        probes = ready.get("probes")
        if not isinstance(probes, dict):
            fail("Pi ready message lacks ambient conformance probes")
        prohibited = (
            "host_file_readable", "workspace_file_readable", "workspace_write_effect",
            "synthetic_service_credential_inherited", "arbitrary_host_executable_launched",
            "loopback_connected", "private_network_connected",
        )
        failures = {key: probes.get(key) for key in prohibited if probes.get(key) is not False}
        if failures:
            fail(f"Pi ambient-authority conformance failed: {failures}")
        if self.listener.accepted or fixture["process_marker"].exists() or fixture["probe_write"].exists():
            fail("host verification observed a prohibited Pi ambient effect")
        if SYNTHETIC_CREDENTIAL_VALUE in json.dumps(ready, sort_keys=True):
            fail("synthetic service credential entered Pi-visible evidence")
        self.pi_pid = int(ready.get("pid")) if isinstance(ready.get("pid"), int) else None
        return ready

    def _effect(self, payload: object) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            fail("effect_request payload must be an object")
        print(f"[tool] {tool_summary(payload)}", flush=True)
        response = child_json(
            PYTHON,
            [str(EFFECT_BRIDGE), "effect", "--state", str(self.state), "--workspace", str(self.workspace), "--run-id", self.run_id],
            dict(payload),
        )
        request_id = response.get("request_id") if isinstance(response.get("request_id"), str) else None
        receipt = receipt_for_request(self.state, request_id)
        outcome = receipt.get("outcome") if isinstance(receipt, dict) else None
        receipt_id = receipt.get("receipt_id") if isinstance(receipt, dict) else None
        dispatch = "SUCCEEDED" if response.get("ok") is True else "FAILED"
        # A003's accepted qualification policy is ALLOW for the exact four governed actions.
        print(
            f"[effect] policy=ALLOW dispatch={dispatch} request={request_id or '-'} "
            f"receipt={receipt_id or '-'} outcome={outcome or '-'}",
            flush=True,
        )
        with self.trace.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "toolCallId": payload.get("toolCallId"),
                "toolName": payload.get("toolName"),
                "request_id": request_id,
                "ok": response.get("ok") is True,
                "receipt_id": receipt_id,
                "outcome": outcome,
                "error_type": response.get("error_type"),
            }, sort_keys=True) + "\n")
        return response

    def prompt(self, text: str) -> str:
        if not text.strip():
            return ""
        self.turn += 1
        turn_id = f"turn-{self.turn}"
        self._write({"type": "prompt", "id": turn_id, "text": text})
        deadline = time.monotonic() + 900
        while time.monotonic() < deadline:
            message = self._read(min(330, max(0.1, deadline - time.monotonic())))
            kind = message.get("type")
            if kind == "rpc":
                rpc_id = message.get("id")
                rpc_kind = message.get("kind")
                try:
                    if not isinstance(rpc_id, str) or not rpc_id:
                        fail("sandboxed Pi RPC missing id")
                    if rpc_kind == "model_request":
                        self.model_request_count += 1
                        handled = model_events(message.get("payload"))
                    elif rpc_kind == "effect_request":
                        handled = self._effect(message.get("payload"))
                    else:
                        fail(f"sandboxed Pi requested unsupported host capability: {rpc_kind!r}")
                    response = {"type": "rpc_response", "id": rpc_id, "ok": True, "payload": handled}
                except BaseException as exc:
                    response = {"type": "rpc_response", "id": rpc_id, "ok": False, "error": f"{type(exc).__name__}: {exc}"}
                self._write(response)
                continue
            if kind == "turn_result":
                if message.get("id") != turn_id:
                    fail("turn result did not bind active prompt")
                text_value = message.get("assistant_text")
                if not isinstance(text_value, str):
                    fail("turn result assistant text malformed")
                return text_value
            fail(f"unexpected Pi protocol message during turn: {message!r}")
        fail("interactive turn exceeded bounded timeout")

    def close(self) -> None:
        proc = self.proc
        if proc is not None and proc.poll() is None:
            try:
                self._write({"type": "shutdown"})
                message = self._read(10)
                if message.get("type") != "shutdown_complete":
                    raise A004TerminalError("Pi did not acknowledge clean shutdown")
                if proc.stdin is not None:
                    proc.stdin.close()
                proc.wait(timeout=10)
            except BaseException:
                try:
                    proc.kill()
                except OSError:
                    pass
                try:
                    proc.wait(timeout=5)
                except Exception:
                    pass
        if self.stderr_thread is not None:
            self.stderr_thread.join(timeout=1)
        if self.listener is not None:
            self.listener.close()
            self.listener = None
        if self.tempdir is not None:
            self.tempdir.cleanup()
            self.tempdir = None
        self.proc = None

    def __enter__(self) -> "InteractiveSession":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()


def default_workspace() -> Path:
    return Path.home() / ".local/share/local-agent-controller/a004-baseline-workspace"


def default_state() -> Path:
    return Path.home() / ".local/state/local-agent-controller/a004/controller.db"


def default_trace() -> Path:
    return Path.home() / ".local/state/local-agent-controller/a004/effect-trace.jsonl"


def system_prompt() -> str:
    return "\n".join((
        "You are the Local Agent Controller A004 baseline test agent.",
        "You have exactly four governed tools: lac_fs_read, lac_fs_create, lac_fs_replace, lac_shell_exec.",
        "All filesystem paths are relative to the dedicated baseline workspace.",
        "Use governed tools when the user requests workspace inspection or changes.",
        "For lac_shell_exec, executable is the program path; argv contains only arguments after the executable and excludes argv[0].",
        "For a plain /usr/bin/ls workspace listing use executable=/usr/bin/ls, argv=[], cwd=., environment={}.",
        "Do not claim a tool succeeded unless its result says it succeeded.",
        "Do not expose hidden reasoning. Give concise user-facing answers.",
    ))


def status_text(session: InteractiveSession, runtime_mode: str) -> str:
    return (
        f"runtime={runtime_mode} endpoint={BASE_URL} model={SERVED_MODEL_ID}\n"
        f"pi_pid={session.pi_pid or '-'} sandbox=bubblewrap network=none\n"
        f"tools={','.join(EXPECTED_TOOLS)}\n"
        f"workspace={session.workspace}\nstate={session.state}\ntrace={session.trace}"
    )


def run_smoke(workspace: Path, state: Path, trace: Path, runtime_mode: str) -> int:
    with InteractiveSession(workspace=workspace, state=state, trace=trace, system_prompt=system_prompt()) as session:
        first_pid = session.pi_pid
        text1 = session.prompt("Reply briefly that the baseline session is ready. Do not call a tool.")
        text2 = session.prompt("Reply briefly that this is the second turn in the same conversation. Do not call a tool.")
        if session.pi_pid != first_pid:
            fail("Pi process identity changed across multi-turn smoke")
        if session.model_request_count < 2:
            fail("multi-turn smoke did not traverse the LAC ModelProvider twice")
        if not isinstance(text1, str) or not isinstance(text2, str):
            fail("multi-turn smoke returned malformed assistant text")
        print(status_text(session, runtime_mode))
        print(f"LAC_A004_MULTI_TURN_SMOKE=PASS model_requests={session.model_request_count}")
    return 0


def run_interactive(workspace: Path, state: Path, trace: Path, runtime_mode: str) -> int:
    workspace.mkdir(parents=True, exist_ok=True)
    workspace.chmod(0o700)
    guide_file = workspace / "BASELINE_WORKSPACE.txt"
    if not guide_file.exists():
        guide_file.write_text("Dedicated Local Agent Controller A004 owner-test workspace.\n", encoding="utf-8")
    with InteractiveSession(workspace=workspace, state=state, trace=trace, system_prompt=system_prompt()) as session:
        print("LAC A004 baseline terminal. Type /help for controls.")
        print(status_text(session, runtime_mode))
        while True:
            try:
                raw = read_terminal_input("\nlac> ")
            except EOFError:
                raw = "/quit"
            try:
                raw = validate_terminal_input(raw)
            except A004InputRejected as exc:
                print(f"input> rejected: {exc}")
                continue
            command = raw.strip()
            if command in {"/quit", "quit", "exit"}:
                break
            if command in {"/help", "help"}:
                print("/help  show controls\n/status show runtime/sandbox/workspace status\n/quit  clean shutdown\nAny other text is sent as the next conversation turn.")
                continue
            if command in {"/status", "status"}:
                print(status_text(session, runtime_mode))
                continue
            if not command:
                continue
            answer = session.prompt(raw)
            print(f"assistant> {answer}")
    print("LAC_A004_TERMINAL_SHUTDOWN=CLEAN")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Interactive owner terminal for the accepted A003 governed Pi path")
    parser.add_argument("--workspace", type=Path, default=default_workspace())
    parser.add_argument("--state", type=Path, default=default_state())
    parser.add_argument("--trace", type=Path, default=default_trace())
    parser.add_argument("--runtime", choices=("manage", "external"), default="manage")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()

    verify_accepted_pins()

    def _terminate(_signum: int, _frame: object) -> None:
        raise KeyboardInterrupt

    previous_sigterm = signal.getsignal(signal.SIGTERM)
    signal.signal(signal.SIGTERM, _terminate)
    runtime: FreeTokenRuntime | None = None
    runtime_mode = "external"
    try:
        if args.runtime == "manage":
            runtime = FreeTokenRuntime()
            runtime_mode = runtime.ensure()
        else:
            assets = runtime_assets()
            exact, detail = probe_exact_endpoint(assets)
            if not exact:
                fail(f"external FreeToken endpoint is not the exact accepted runtime: {detail}")
        if args.smoke:
            return run_smoke(args.workspace.expanduser(), args.state.expanduser(), args.trace.expanduser(), runtime_mode)
        return run_interactive(args.workspace.expanduser(), args.state.expanduser(), args.trace.expanduser(), runtime_mode)
    finally:
        signal.signal(signal.SIGTERM, previous_sigterm)
        if runtime is not None:
            runtime.stop()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nLAC_A004_TERMINAL_SHUTDOWN=INTERRUPTED_CLEAN")
        raise SystemExit(130)
    except A004TerminalError as exc:
        print(f"LAC_A004_TERMINAL=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
