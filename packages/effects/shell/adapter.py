from __future__ import annotations

import hashlib
import os
import re
import shutil
import stat
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator, Mapping, Sequence

from packages.core import EffectRequest, EffectRequestError, ExecutionLease, ExecutionLeaseError
from packages.sandbox import NetworkMode, SandboxMount, SandboxSpec, get_selected_backend


SHELL_ADAPTER_ID = "shell:v1"
SHELL_RESULT_SCHEMA = "lac.shell-effect-result/v1"
SHELL_EXEC_ACTION = "shell.exec"
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")
_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_MAX_ARGC = 128
_MAX_ARG_BYTES = 8192
_MAX_ARGV_BYTES = 32768
_MAX_ENV_VALUE_BYTES = 8192

# H003 deliberately excludes interpreters, shells, privilege tools, namespace tools,
# and common command-launching multiplexers from the generic shell surface. A later
# explicitly scoped task may add a separately governed execution contract if needed.
_BLOCKED_EXECUTABLE_NAMES = frozenset(
    {
        "sh",
        "bash",
        "dash",
        "zsh",
        "fish",
        "sudo",
        "su",
        "doas",
        "pkexec",
        "setpriv",
        "unshare",
        "nsenter",
        "chroot",
        "mount",
        "umount",
        "bwrap",
        "podman",
        "busybox",
        "toybox",
        "env",
        "xargs",
        "find",
        "make",
        "ninja",
        "cmake",
        "git",
        "perl",
        "ruby",
        "node",
        "nodejs",
        "php",
        "lua",
        "awk",
        "gawk",
    }
)
_BLOCKED_EXECUTABLE_PREFIXES = ("python", "pypy", "ld-linux", "ld-musl")
_BASE_ENVIRONMENT = {
    "HOME": "/nonexistent",
    "LC_ALL": "C",
    "PATH": "/usr/bin",
}
_RESERVED_ENVIRONMENT_NAMES = frozenset(_BASE_ENVIRONMENT)
_SECRET_ENV_EXACT = frozenset(
    {
        "SSH_AUTH_SOCK",
        "GPG_AGENT_INFO",
        "GIT_ASKPASS",
        "BASH_ENV",
        "ENV",
        "IFS",
        "CDPATH",
        "PROMPT_COMMAND",
    }
)
_SECRET_ENV_PREFIXES = (
    "AWS_",
    "AZURE_",
    "GCP_",
    "GOOGLE_",
    "OPENAI_",
    "ANTHROPIC_",
    "GITHUB_",
    "GH_",
    "SSH_",
    "GPG_",
    "HTTP_PROXY",
    "HTTPS_PROXY",
    "ALL_PROXY",
    "NO_PROXY",
    "LD_",
    "DYLD_",
    "PYTHON",
    "PERL",
    "RUBY",
    "NODE_",
)
_SECRET_ENV_SUFFIXES = (
    "_TOKEN",
    "_SECRET",
    "_PASSWORD",
    "_PASSWD",
    "_API_KEY",
    "_ACCESS_KEY",
    "_PRIVATE_KEY",
    "_CREDENTIAL",
    "_CREDENTIALS",
)


class ShellEffectError(ValueError):
    """The typed shell request or bounded host execution failed closed."""


@dataclass(frozen=True)
class ShellEffectResult:
    schema: str
    adapter_id: str
    request_id: str
    canonical_request_hash: str
    lease_id: str
    action: str
    resource: str
    executable: str
    argv: tuple[str, ...]
    cwd: str
    environment_keys: tuple[str, ...]
    return_code: int
    stdout: str
    stderr: str

    def to_record(self) -> dict[str, object]:
        return {
            "schema": self.schema,
            "adapter_id": self.adapter_id,
            "request_id": self.request_id,
            "canonical_request_hash": self.canonical_request_hash,
            "lease_id": self.lease_id,
            "action": self.action,
            "resource": self.resource,
            "executable": self.executable,
            "argv": list(self.argv),
            "cwd": self.cwd,
            "environment_keys": list(self.environment_keys),
            "return_code": self.return_code,
            "stdout": self.stdout,
            "stderr": self.stderr,
        }


@dataclass(frozen=True)
class _ShellOperation:
    executable: str
    argv: tuple[str, ...]
    cwd: str
    environment: tuple[tuple[str, str], ...]


def _canonical_request(request: EffectRequest) -> EffectRequest:
    if not isinstance(request, EffectRequest):
        raise ShellEffectError("request must be a canonical EffectRequest")
    try:
        canonical = EffectRequest.from_record(request.to_record())
    except (EffectRequestError, TypeError, AttributeError) as exc:
        raise ShellEffectError("request failed canonical integrity validation") from exc
    if canonical != request:
        raise ShellEffectError("request is not canonical")
    return canonical


def _canonical_lease(lease: ExecutionLease) -> ExecutionLease:
    if not isinstance(lease, ExecutionLease):
        raise ShellEffectError("lease must be a canonical ExecutionLease")
    try:
        canonical = ExecutionLease.from_record(lease.to_record())
    except (ExecutionLeaseError, TypeError, AttributeError) as exc:
        raise ShellEffectError("lease failed canonical integrity validation") from exc
    if canonical != lease:
        raise ShellEffectError("lease is not canonical")
    return canonical


def _utf8_length(value: str, field: str) -> int:
    try:
        return len(value.encode("utf-8"))
    except UnicodeEncodeError as exc:
        raise ShellEffectError(f"{field} must be valid UTF-8 text") from exc


def _canonical_executable(value: object) -> str:
    if not isinstance(value, str) or not value or _CONTROL_CHARACTER.search(value):
        raise ShellEffectError("executable must be a non-empty absolute path without control characters")
    path = PurePosixPath(value)
    if not path.is_absolute() or ".." in path.parts or "." in path.parts or str(path) != value:
        raise ShellEffectError("executable must use one canonical absolute POSIX representation")
    name = path.name.lower()
    if name in _BLOCKED_EXECUTABLE_NAMES or any(name.startswith(prefix) for prefix in _BLOCKED_EXECUTABLE_PREFIXES):
        raise ShellEffectError("interpreter, privilege, namespace, or command-launcher executable is unsupported")
    return value


def _canonical_cwd(value: object) -> str:
    if not isinstance(value, str) or not value or _CONTROL_CHARACTER.search(value):
        raise ShellEffectError("cwd must be a non-empty workspace-relative string")
    if value == ".":
        return value
    path = PurePosixPath(value)
    if path.is_absolute() or not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise ShellEffectError("cwd must remain beneath the configured working root")
    if str(path) != value:
        raise ShellEffectError("cwd must use one canonical relative POSIX representation")
    return value


def _canonical_argv(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ShellEffectError("argv must be a JSON array of argument strings excluding argv[0]")
    if len(value) > _MAX_ARGC:
        raise ShellEffectError("argv contains too many arguments")
    normalized: list[str] = []
    total = 0
    for index, item in enumerate(value):
        if not isinstance(item, str) or _CONTROL_CHARACTER.search(item):
            raise ShellEffectError(f"argv[{index}] must be a string without control characters")
        size = _utf8_length(item, f"argv[{index}]")
        if size > _MAX_ARG_BYTES:
            raise ShellEffectError(f"argv[{index}] exceeds the H003 argument bound")
        total += size
        if total > _MAX_ARGV_BYTES:
            raise ShellEffectError("argv exceeds the H003 aggregate argument bound")
        normalized.append(item)
    return tuple(normalized)


def _is_secret_environment_name(name: str) -> bool:
    upper = name.upper()
    if upper in _SECRET_ENV_EXACT:
        return True
    if any(upper.startswith(prefix) for prefix in _SECRET_ENV_PREFIXES):
        return True
    return any(upper.endswith(suffix) for suffix in _SECRET_ENV_SUFFIXES)


def _normalize_allowed_environment(names: Sequence[str]) -> frozenset[str]:
    allowed: set[str] = set()
    for name in tuple(names):
        if not isinstance(name, str) or not _ENV_NAME.fullmatch(name):
            raise ShellEffectError("allowed environment names must use conservative POSIX syntax")
        if name in _RESERVED_ENVIRONMENT_NAMES or _is_secret_environment_name(name):
            raise ShellEffectError(f"environment name is reserved or credential-sensitive: {name}")
        allowed.add(name)
    return frozenset(allowed)


def _canonical_environment(value: object, *, allowed_names: frozenset[str]) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, dict):
        raise ShellEffectError("environment must be a JSON object")
    normalized: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not _ENV_NAME.fullmatch(key):
            raise ShellEffectError("environment contains an invalid variable name")
        if key not in allowed_names or key in _RESERVED_ENVIRONMENT_NAMES or _is_secret_environment_name(key):
            raise ShellEffectError(f"unsupported environment variable: {key}")
        if not isinstance(item, str) or _CONTROL_CHARACTER.search(item):
            raise ShellEffectError(f"environment value for {key!r} must be text without control characters")
        if _utf8_length(item, f"environment[{key}]") > _MAX_ENV_VALUE_BYTES:
            raise ShellEffectError(f"environment value for {key!r} exceeds the H003 bound")
        normalized[key] = item
    return tuple(sorted(normalized.items()))


def _parse_operation(
    request: EffectRequest,
    *,
    resource: str,
    allowed_executables: Mapping[str, Path],
    allowed_environment: frozenset[str],
) -> _ShellOperation:
    canonical = _canonical_request(request)
    if canonical.resource != resource:
        raise ShellEffectError("shell request targets a different configured resource")
    if canonical.action != SHELL_EXEC_ACTION:
        raise ShellEffectError(f"unsupported shell action: {canonical.action!r}")
    arguments = canonical.arguments
    if set(arguments) != {"executable", "argv", "cwd", "environment"}:
        raise ShellEffectError(
            "shell.exec arguments must contain exactly executable, argv, cwd, and environment"
        )
    executable = _canonical_executable(arguments["executable"])
    if executable not in allowed_executables:
        raise ShellEffectError("executable is not in the configured H003 allowlist")
    argv = _canonical_argv(arguments["argv"])
    cwd = _canonical_cwd(arguments["cwd"])
    environment = _canonical_environment(arguments["environment"], allowed_names=allowed_environment)
    return _ShellOperation(executable=executable, argv=argv, cwd=cwd, environment=environment)


def _copy_binary_and_libraries(binary: Path, rootfs: Path) -> Path:
    try:
        resolved = binary.resolve(strict=True)
    except OSError as exc:
        raise ShellEffectError(f"configured executable is unavailable: {binary}") from exc
    if resolved != binary or binary.is_symlink() or not binary.is_file():
        raise ShellEffectError("configured executable must remain a canonical regular non-symlink file")
    destination = rootfs / binary.relative_to("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(binary, destination)
    ldd = shutil.which("ldd")
    if not ldd:
        raise ShellEffectError("ldd is required to construct the bounded shell runtime")
    probe = subprocess.run([ldd, str(binary)], text=True, capture_output=True, check=False)
    if probe.returncode != 0:
        raise ShellEffectError(f"ldd failed for configured executable: {binary}")
    libraries: set[Path] = set()
    for line in probe.stdout.splitlines():
        for raw in re.findall(r"(?:=>\s*)?(/[^\s(]+)", line):
            candidate = Path(raw)
            if candidate.is_file():
                libraries.add(candidate)
    for library in sorted(libraries, key=str):
        target = rootfs / library.relative_to("/")
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(library, target)
    return destination


@contextmanager
def _minimal_runtime(binary: Path, *, cwd: str) -> Iterator[Path]:
    with tempfile.TemporaryDirectory(prefix="lac-h003-shell-runtime-") as tmp_name:
        rootfs = Path(tmp_name) / "rootfs"
        for name in ("proc", "dev", "tmp", "workspace"):
            (rootfs / name).mkdir(parents=True, exist_ok=True)
        if cwd != ".":
            (rootfs / "workspace").joinpath(*PurePosixPath(cwd).parts).mkdir(parents=True, exist_ok=True)
        _copy_binary_and_libraries(binary, rootfs)
        yield rootfs


class ShellEffectAdapter:
    """Exact typed argv execution inside the H001 sandbox and H002 workspace boundary."""

    def __init__(
        self,
        working_root: str | os.PathLike[str],
        *,
        allowed_executables: Sequence[str | os.PathLike[str]],
        allowed_environment: Sequence[str] = (),
        resource: str = "shell:workspace",
        timeout_seconds: float = 10.0,
    ) -> None:
        root = Path(working_root)
        if not root.is_absolute():
            raise ShellEffectError("working_root must be absolute")
        try:
            resolved_root = root.resolve(strict=True)
        except OSError as exc:
            raise ShellEffectError("working_root must exist") from exc
        if resolved_root != root or root.is_symlink() or not root.is_dir():
            raise ShellEffectError("working_root must be an existing non-symlink canonical directory")
        if not isinstance(resource, str) or not resource or resource != resource.strip():
            raise ShellEffectError("resource must be a non-empty trimmed string")
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool):
            raise ShellEffectError("timeout_seconds must be numeric")
        timeout = float(timeout_seconds)
        if timeout <= 0 or timeout > 30:
            raise ShellEffectError("timeout_seconds must be within (0, 30]")

        executable_map: dict[str, Path] = {}
        for raw in tuple(allowed_executables):
            path = Path(raw)
            if not path.is_absolute():
                raise ShellEffectError("allowed executable paths must be absolute")
            canonical_text = _canonical_executable(path.as_posix())
            try:
                resolved = path.resolve(strict=True)
            except OSError as exc:
                raise ShellEffectError(f"allowed executable does not exist: {path}") from exc
            try:
                mode = resolved.stat().st_mode
            except OSError as exc:
                raise ShellEffectError(f"allowed executable metadata is unavailable: {path}") from exc
            if resolved != path or path.is_symlink() or not path.is_file() or not os.access(path, os.X_OK):
                raise ShellEffectError("allowed executables must be canonical executable regular files")
            if mode & (stat.S_ISUID | stat.S_ISGID):
                raise ShellEffectError("setuid/setgid executables are unsupported")
            executable_map[canonical_text] = path
        if not executable_map:
            raise ShellEffectError("at least one explicitly allowed executable is required")

        self._working_root = root
        self._resource = resource
        self._allowed_executables = dict(sorted(executable_map.items()))
        self._allowed_environment = _normalize_allowed_environment(allowed_environment)
        self._timeout_seconds = timeout
        self._backend = get_selected_backend()

    @property
    def adapter_id(self) -> str:
        return SHELL_ADAPTER_ID

    @property
    def working_root(self) -> Path:
        return self._working_root

    @property
    def resource(self) -> str:
        return self._resource

    @property
    def backend_id(self) -> str:
        return self._backend.backend_id

    @property
    def allowed_executables(self) -> tuple[str, ...]:
        return tuple(self._allowed_executables)

    @property
    def allowed_environment(self) -> tuple[str, ...]:
        return tuple(sorted(self._allowed_environment))

    def supports(self, request: EffectRequest) -> bool:
        try:
            _parse_operation(
                request,
                resource=self._resource,
                allowed_executables=self._allowed_executables,
                allowed_environment=self._allowed_environment,
            )
        except ShellEffectError:
            return False
        return True

    def _host_cwd(self, cwd: str) -> Path:
        candidate = self._working_root if cwd == "." else self._working_root.joinpath(*PurePosixPath(cwd).parts)
        try:
            resolved = candidate.resolve(strict=True)
        except OSError as exc:
            raise ShellEffectError("cwd must be an existing directory beneath the configured working root") from exc
        if resolved != candidate or candidate.is_symlink() or not candidate.is_dir():
            raise ShellEffectError("cwd cannot traverse a symlink or non-directory")
        try:
            resolved.relative_to(self._working_root)
        except ValueError as exc:
            raise ShellEffectError("cwd escaped the configured working root") from exc
        return candidate

    def _run_operation(self, operation: _ShellOperation) -> subprocess.CompletedProcess[str]:
        host_binary = self._allowed_executables[operation.executable]
        self._host_cwd(operation.cwd)
        environment = dict(_BASE_ENVIRONMENT)
        environment.update(dict(operation.environment))
        sandbox_cwd = PurePosixPath("/workspace")
        if operation.cwd != ".":
            sandbox_cwd = sandbox_cwd.joinpath(*PurePosixPath(operation.cwd).parts)
        with _minimal_runtime(host_binary, cwd=operation.cwd) as rootfs:
            instance = "sh-" + hashlib.sha256(
                (
                    operation.executable
                    + "\0"
                    + "\0".join(operation.argv)
                    + "\0"
                    + operation.cwd
                    + "\0"
                    + "\0".join(f"{k}={v}" for k, v in operation.environment)
                ).encode("utf-8")
            ).hexdigest()[:24]
            spec = SandboxSpec(
                runtime_root=rootfs,
                instance_id=instance,
                mounts=(
                    SandboxMount(
                        source=self._working_root,
                        target=PurePosixPath("/workspace"),
                        writable=True,
                    ),
                ),
                environment=environment,
                cwd=sandbox_cwd,
                network=NetworkMode.NONE,
            )
            try:
                return self._backend.run(
                    spec,
                    [operation.executable, *operation.argv],
                    timeout=self._timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                raise ShellEffectError("bounded shell execution exceeded its fixed timeout") from exc

    def invoke(self, request: EffectRequest, *, lease: ExecutionLease) -> ShellEffectResult:
        canonical_request = _canonical_request(request)
        canonical_lease = _canonical_lease(lease)
        if canonical_lease.request_id != canonical_request.request_id:
            raise ShellEffectError("execution lease binds a different request_id")
        operation = _parse_operation(
            canonical_request,
            resource=self._resource,
            allowed_executables=self._allowed_executables,
            allowed_environment=self._allowed_environment,
        )
        proc = self._run_operation(operation)
        return ShellEffectResult(
            schema=SHELL_RESULT_SCHEMA,
            adapter_id=SHELL_ADAPTER_ID,
            request_id=canonical_request.request_id,
            canonical_request_hash=canonical_request.canonical_hash,
            lease_id=canonical_lease.lease_id,
            action=canonical_request.action,
            resource=canonical_request.resource,
            executable=operation.executable,
            argv=operation.argv,
            cwd=operation.cwd,
            environment_keys=tuple(key for key, _ in operation.environment),
            return_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )

    def reconcile(self, request: EffectRequest, *, lease: ExecutionLease) -> None:
        # Generic shell effects may mutate workspace state. A PREPARED execution is
        # therefore intentionally not re-run or guessed after a crash.
        canonical_request = _canonical_request(request)
        canonical_lease = _canonical_lease(lease)
        if canonical_lease.request_id != canonical_request.request_id:
            raise ShellEffectError("execution lease binds a different request_id")
        return None
