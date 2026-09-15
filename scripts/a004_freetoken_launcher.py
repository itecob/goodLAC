#!/usr/bin/env python3
from __future__ import annotations

import argparse
import glob
import json
import os
import re
import shutil
import signal
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence

FREETOKEN_PIN = "af71ba43206e124f5ff6419b47ee36c6e9981078"
FREETOKEN_VERSION = "0.1.2"
MODEL_REPO = "openai/gpt-oss-20b"
MODEL_REVISION = "6cee5e81ee83917806bbde320786a8fb61efebee"
SERVED_MODEL_ID = "lac-a003-gpt-oss-20b"
HOST = "127.0.0.1"
PORT = 19203
BASE_URL = f"http://{HOST}:{PORT}"

SECRET_PREFIXES = (
    "OPENAI_", "ANTHROPIC_", "AWS_", "AZURE_", "GOOGLE_", "HF_",
    "HUGGINGFACE_", "HUGGING_FACE_", "GITHUB_", "GH_", "SSH_",
)
SECRET_SUFFIXES = (
    "_API_KEY", "_ACCESS_TOKEN", "_TOKEN", "_SECRET", "_PASSWORD",
    "_CREDENTIAL", "_CREDENTIALS",
)


class A004RuntimeError(RuntimeError):
    pass


@dataclass(frozen=True)
class CudaToolkit:
    root: Path
    nvcc: Path
    release: str


@dataclass(frozen=True)
class RuntimeAssets:
    freetoken_checkout: Path
    freetoken_venv: Path
    ft: Path
    ninja: Path
    model_snapshot: Path


def _http_json(path: str, *, timeout: float = 2.0) -> dict:
    req = urllib.request.Request(BASE_URL + path, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as response:
        if response.status != 200:
            raise A004RuntimeError(f"HTTP {response.status} from {path}")
        value = json.loads(response.read().decode("utf-8"))
    if not isinstance(value, dict):
        raise A004RuntimeError(f"non-object JSON from {path}")
    return value


def _candidate_nvcc(env: Mapping[str, str]) -> list[Path]:
    candidates: list[Path] = []
    found = shutil.which("nvcc", path=env.get("PATH"))
    if found:
        candidates.append(Path(found))
    for key in ("CUDA_HOME", "CUDA_PATH"):
        raw = env.get(key)
        if raw:
            candidates.append(Path(raw).expanduser() / "bin" / "nvcc")
    for pattern in (
        "/opt/cuda/bin/nvcc",
        "/opt/cuda-*/bin/nvcc",
        "/usr/local/cuda/bin/nvcc",
        "/usr/local/cuda-*/bin/nvcc",
    ):
        for item in sorted(glob.glob(pattern)):
            candidates.append(Path(item))
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _validate_nvcc(candidate: Path) -> CudaToolkit | None:
    try:
        nvcc = candidate.expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None
    if not nvcc.is_file() or not os.access(nvcc, os.X_OK) or nvcc.name != "nvcc":
        return None
    root = nvcc.parent.parent.resolve()
    header_candidates = (
        root / "include" / "cuda.h",
        root / "targets" / "x86_64-linux" / "include" / "cuda.h",
    )
    library_candidates = (
        root / "lib64",
        root / "lib",
        root / "targets" / "x86_64-linux" / "lib",
    )
    if not any(path.is_file() for path in header_candidates):
        return None
    if not any(path.is_dir() for path in library_candidates):
        return None
    proc = subprocess.run(
        [str(nvcc), "--version"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=10,
        check=False,
    )
    if proc.returncode != 0:
        return None
    match = re.search(r"release\s+(\d+)\.(\d+)", proc.stdout)
    if not match:
        return None
    major = int(match.group(1))
    release = f"{match.group(1)}.{match.group(2)}"
    if major != 13:
        return None
    return CudaToolkit(root=root, nvcc=nvcc, release=release)


def discover_cuda_toolkit(env: Mapping[str, str] | None = None) -> CudaToolkit:
    source = dict(os.environ if env is None else env)
    tried: list[str] = []
    for candidate in _candidate_nvcc(source):
        tried.append(str(candidate))
        toolkit = _validate_nvcc(candidate)
        if toolkit is not None:
            return toolkit
    detail = ", ".join(tried) if tried else "no nvcc candidates discovered"
    raise A004RuntimeError(
        "CUDA 13 toolkit qualification failed. FreeToken requires a real CUDA toolkit with nvcc, "
        f"cuda.h, and runtime libraries. Candidates checked: {detail}"
    )


def runtime_assets(home: Path | None = None) -> RuntimeAssets:
    home = (home or Path.home()).expanduser().resolve()
    checkout = home / ".cache/local-agent-controller/phase0/upstream/freetoken"
    venv = home / ".cache/local-agent-controller/a003" / f"freetoken-{FREETOKEN_PIN}"
    snapshot = home / ".cache/huggingface/hub/models--openai--gpt-oss-20b/snapshots" / MODEL_REVISION
    return RuntimeAssets(
        freetoken_checkout=checkout,
        freetoken_venv=venv,
        ft=venv / "bin" / "ft",
        ninja=venv / "bin" / "ninja",
        model_snapshot=snapshot,
    )


def validate_runtime_assets(assets: RuntimeAssets) -> None:
    if not (assets.freetoken_checkout / ".git").is_dir():
        raise A004RuntimeError(f"qualified FreeToken checkout missing: {assets.freetoken_checkout}")
    if not assets.ft.is_file() or not os.access(assets.ft, os.X_OK):
        raise A004RuntimeError(f"accepted A003 FreeToken CLI missing: {assets.ft}")
    if not assets.ninja.is_file() or not os.access(assets.ninja, os.X_OK):
        raise A004RuntimeError(f"accepted A003 JIT build dependency missing: {assets.ninja}")
    if not (assets.model_snapshot / "config.json").is_file():
        raise A004RuntimeError(
            "exact accepted model snapshot is unavailable; A004 will not download or substitute a model: "
            f"{assets.model_snapshot}"
        )


def _resolve_model_root(value: object) -> Path | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        return Path(value).expanduser().resolve(strict=True)
    except (FileNotFoundError, OSError):
        return None


def probe_exact_endpoint(assets: RuntimeAssets, *, timeout: float = 2.0) -> tuple[bool, str]:
    try:
        health = _http_json("/health", timeout=timeout)
        models = _http_json("/v1/models", timeout=timeout)
    except (OSError, urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError, A004RuntimeError) as exc:
        return False, f"unavailable: {type(exc).__name__}: {exc}"
    if health.get("status") != "ok" or health.get("maintenance") not in (None, "serving"):
        return False, f"health not ready: {health!r}"
    if health.get("version") != FREETOKEN_VERSION:
        return False, f"FreeToken version mismatch: {health.get('version')!r}"
    if health.get("model") != SERVED_MODEL_ID:
        return False, f"served model mismatch: {health.get('model')!r}"
    data = models.get("data")
    if not isinstance(data, list) or len(data) != 1 or not isinstance(data[0], dict):
        return False, "unexpected /v1/models shape"
    model = data[0]
    if model.get("id") != SERVED_MODEL_ID:
        return False, f"model id mismatch: {model.get('id')!r}"
    root = _resolve_model_root(model.get("root"))
    if root is not None and root != assets.model_snapshot.resolve():
        return False, f"model snapshot mismatch: {root}"
    return True, "exact accepted endpoint"


def _can_bind(port: int) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind((HOST, port))
        return True
    except OSError:
        return False
    finally:
        sock.close()


def _sanitized_runtime_env(toolkit: CudaToolkit, assets: RuntimeAssets) -> dict[str, str]:
    env = dict(os.environ)
    for key in tuple(env):
        upper = key.upper()
        if upper.startswith(SECRET_PREFIXES) or upper.endswith(SECRET_SUFFIXES):
            env.pop(key, None)
    env["CUDA_HOME"] = str(toolkit.root)
    env["CUDA_PATH"] = str(toolkit.root)
    env["CUDACXX"] = str(toolkit.nvcc)
    original_path = env.get("PATH", "")
    required_path = [str(toolkit.root / "bin"), str(assets.freetoken_venv / "bin")]
    if original_path:
        required_path.append(original_path)
    env["PATH"] = os.pathsep.join(required_path)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _tail(path: Path, *, limit: int = 6000) -> str:
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return data[-limit:]


class FreeTokenRuntime:
    def __init__(self, *, log_path: Path | None = None, startup_timeout: float = 900.0) -> None:
        self.assets = runtime_assets()
        self.log_path = (log_path or (Path.home() / ".cache/local-agent-controller/a004/freetoken.log")).expanduser().resolve()
        self.startup_timeout = startup_timeout
        self.process: subprocess.Popen[str] | None = None
        self.owned = False
        self.toolkit: CudaToolkit | None = None
        self._log_handle = None

    def ensure(self) -> str:
        validate_runtime_assets(self.assets)
        exact, detail = probe_exact_endpoint(self.assets)
        if exact:
            return "connected"
        # If 19203 is occupied but not by the exact accepted runtime, never kill or reuse it.
        if not _can_bind(PORT):
            raise A004RuntimeError(f"loopback port {PORT} is occupied by a non-qualified endpoint: {detail}")
        # FreeToken 0.1.2 uses server_port + 1 for its local distributed worker.
        if not _can_bind(PORT + 1):
            raise A004RuntimeError(f"required FreeToken companion loopback port {PORT + 1} is already in use")
        self.toolkit = discover_cuda_toolkit()
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self._log_handle = self.log_path.open("a", encoding="utf-8")
        command = [
            str(self.assets.ft),
            "serve",
            "--model", str(self.assets.model_snapshot),
            "--served-model-name", SERVED_MODEL_ID,
            "--host", HOST,
            "--port", str(PORT),
        ]
        self.process = subprocess.Popen(
            command,
            cwd=str(self.assets.freetoken_checkout),
            env=_sanitized_runtime_env(self.toolkit, self.assets),
            stdout=self._log_handle,
            stderr=subprocess.STDOUT,
            text=True,
            start_new_session=True,
        )
        self.owned = True
        deadline = time.monotonic() + self.startup_timeout
        last_detail = "starting"
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                rc = self.process.returncode
                tail = _tail(self.log_path)
                self.stop()
                raise A004RuntimeError(
                    f"FreeToken exited before readiness with rc={rc}; log tail:\n{tail}"
                )
            exact, last_detail = probe_exact_endpoint(self.assets, timeout=2.0)
            if exact:
                return "started"
            time.sleep(1.0)
        tail = _tail(self.log_path)
        self.stop()
        raise A004RuntimeError(f"FreeToken did not reach exact readiness: {last_detail}; log tail:\n{tail}")

    def stop(self) -> None:
        proc = self.process
        if proc is not None and self.owned and proc.poll() is None:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                proc.wait(timeout=5)
        if self._log_handle is not None:
            self._log_handle.close()
            self._log_handle = None
        self.process = None
        self.owned = False

    def __enter__(self) -> "FreeTokenRuntime":
        self.ensure()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()


def doctor() -> int:
    assets = runtime_assets()
    validate_runtime_assets(assets)
    toolkit = discover_cuda_toolkit()
    exact, detail = probe_exact_endpoint(assets)
    print(json.dumps({
        "schema": "lac.a004-runtime-doctor/v1",
        "freetoken_pin": FREETOKEN_PIN,
        "freetoken_version": FREETOKEN_VERSION,
        "model_repo": MODEL_REPO,
        "model_revision": MODEL_REVISION,
        "served_model_id": SERVED_MODEL_ID,
        "base_url": BASE_URL,
        "cuda_home": str(toolkit.root),
        "nvcc": str(toolkit.nvcc),
        "cuda_release": toolkit.release,
        "endpoint_exact": exact,
        "endpoint_detail": detail,
    }, indent=2, sort_keys=True))
    return 0


def run_child(argv: Sequence[str]) -> int:
    if not argv:
        raise A004RuntimeError("run requires a child command after --")
    runtime = FreeTokenRuntime()
    mode = runtime.ensure()
    previous_handlers: dict[int, object] = {}

    def _terminate(signum: int, _frame: object) -> None:
        runtime.stop()
        raise SystemExit(128 + signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        previous_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, _terminate)
    try:
        env = dict(os.environ)
        env["LAC_A003_FREETOKEN_URL"] = BASE_URL
        env["LAC_A003_MODEL_ID"] = SERVED_MODEL_ID
        env.setdefault("LAC_PI_CHECKOUT", str(Path.home() / ".cache/local-agent-controller/phase0/upstream/pi"))
        env.setdefault("LAC_A003_PYTHON", sys.executable)
        env["LAC_A004_RUNTIME_MODE"] = mode
        proc = subprocess.run(list(argv), env=env, check=False)
        return int(proc.returncode)
    finally:
        for signum, handler in previous_handlers.items():
            signal.signal(signum, handler)
        runtime.stop()


def main() -> int:
    parser = argparse.ArgumentParser(description="A004 exact FreeToken runtime lifecycle wrapper")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("doctor")
    run = sub.add_parser("run")
    run.add_argument("argv", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    if args.command == "doctor":
        return doctor()
    if args.command == "run":
        argv = list(args.argv)
        if argv and argv[0] == "--":
            argv = argv[1:]
        return run_child(argv)
    raise A004RuntimeError("unknown command")


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except A004RuntimeError as exc:
        print(f"LAC_A004_FREETOKEN=FAIL: {exc}", file=sys.stderr)
        raise SystemExit(1)
