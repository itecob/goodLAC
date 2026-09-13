from __future__ import annotations

import json
import os
import re
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path, PurePosixPath
from types import MappingProxyType
from typing import Mapping, Protocol, Sequence, runtime_checkable


class SandboxError(RuntimeError):
    """Base sandbox construction/execution error."""


class SandboxSpecError(SandboxError):
    """Sandbox specification is malformed or unsafe."""


class SandboxUnavailable(SandboxError):
    """The selected sandbox backend is unavailable or unqualified."""


class NetworkMode(str, Enum):
    NONE = "none"


_ENV_NAME = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_INSTANCE_ID = re.compile(r"^[a-z0-9][a-z0-9_.-]{0,62}$")
_RESERVED_TARGETS = (
    PurePosixPath("/proc"),
    PurePosixPath("/dev"),
    PurePosixPath("/tmp"),
)
_REQUIRED_CONTROLS = (
    "filesystem_visibility",
    "writable_paths",
    "process_isolation",
    "outbound_network",
    "environment_inheritance",
    "credential_exposure",
    "child_process_containment",
    "rootless_user_namespace",
    "lifecycle_cleanup",
    "failure_mode",
)


def _contains_nul(value: str) -> bool:
    return "\x00" in value


def _target_path(value: str | PurePosixPath) -> PurePosixPath:
    target = PurePosixPath(value)
    if not target.is_absolute() or str(target) == "/":
        raise SandboxSpecError("sandbox mount targets must be absolute and cannot replace root")
    if ".." in target.parts:
        raise SandboxSpecError("sandbox mount targets cannot contain parent traversal")
    for reserved in _RESERVED_TARGETS:
        if target == reserved or reserved in target.parents:
            raise SandboxSpecError(f"sandbox mount target is reserved: {target}")
    return target


def _paths_overlap(left: PurePosixPath, right: PurePosixPath) -> bool:
    return left == right or left in right.parents or right in left.parents


@dataclass(frozen=True)
class SandboxMount:
    source: Path
    target: PurePosixPath
    writable: bool = False

    def __post_init__(self) -> None:
        source = Path(self.source)
        if not source.is_absolute():
            raise SandboxSpecError("sandbox mount source must be absolute")
        if _contains_nul(str(source)):
            raise SandboxSpecError("sandbox mount source contains NUL")
        target = _target_path(self.target)
        object.__setattr__(self, "source", source)
        object.__setattr__(self, "target", target)
        if not isinstance(self.writable, bool):
            raise SandboxSpecError("writable must be boolean")


@dataclass(frozen=True)
class SandboxSpec:
    runtime_root: Path
    instance_id: str
    mounts: tuple[SandboxMount, ...] = ()
    environment: Mapping[str, str] = field(default_factory=dict)
    cwd: PurePosixPath = PurePosixPath("/")
    network: NetworkMode = NetworkMode.NONE

    def __post_init__(self) -> None:
        root = Path(self.runtime_root)
        if not root.is_absolute():
            raise SandboxSpecError("runtime_root must be absolute")
        if _contains_nul(str(root)):
            raise SandboxSpecError("runtime_root contains NUL")
        if not isinstance(self.instance_id, str) or not _INSTANCE_ID.fullmatch(self.instance_id):
            raise SandboxSpecError("instance_id must match conservative container identifier syntax")
        mounts = tuple(self.mounts)
        if not all(isinstance(item, SandboxMount) for item in mounts):
            raise SandboxSpecError("mounts must contain SandboxMount values")
        for index, mount in enumerate(mounts):
            for other in mounts[index + 1 :]:
                if _paths_overlap(mount.target, other.target):
                    raise SandboxSpecError("overlapping sandbox mount targets fail closed")
        env: dict[str, str] = {}
        for key, value in dict(self.environment).items():
            if not isinstance(key, str) or not _ENV_NAME.fullmatch(key):
                raise SandboxSpecError(f"invalid environment name: {key!r}")
            if not isinstance(value, str) or _contains_nul(value):
                raise SandboxSpecError(f"invalid environment value for {key!r}")
            env[key] = value
        cwd = PurePosixPath(self.cwd)
        if not cwd.is_absolute() or ".." in cwd.parts:
            raise SandboxSpecError("cwd must be an absolute normalized sandbox path")
        if not isinstance(self.network, NetworkMode):
            try:
                network = NetworkMode(self.network)
            except (TypeError, ValueError) as exc:
                raise SandboxSpecError("unknown network authority fails closed") from exc
        else:
            network = self.network
        if network is not NetworkMode.NONE:
            raise SandboxSpecError("H001 permits only network=none")
        object.__setattr__(self, "runtime_root", root)
        object.__setattr__(self, "mounts", mounts)
        object.__setattr__(self, "environment", MappingProxyType(dict(sorted(env.items()))))
        object.__setattr__(self, "cwd", cwd)
        object.__setattr__(self, "network", network)

    def validate_host_inputs(self) -> None:
        if not self.runtime_root.is_dir():
            raise SandboxSpecError("runtime_root must exist as a directory")
        if self.runtime_root.is_symlink():
            raise SandboxSpecError("runtime_root cannot be a symlink")
        for mount in self.mounts:
            if not mount.source.exists():
                raise SandboxSpecError(f"sandbox mount source does not exist: {mount.source}")
            host_target = self.runtime_root.joinpath(*mount.target.parts[1:])
            if not host_target.exists():
                raise SandboxSpecError(
                    f"sandbox mount target must exist inside runtime_root before root is read-only: {mount.target}"
                )
            relative = host_target.relative_to(self.runtime_root)
            cursor = self.runtime_root
            for part in relative.parts:
                cursor = cursor / part
                if cursor.is_symlink():
                    raise SandboxSpecError(
                        f"sandbox mount target path cannot traverse a symlink: {mount.target}"
                    )
            if mount.source.is_dir() != host_target.is_dir():
                raise SandboxSpecError(
                    f"sandbox mount source/target type mismatch: {mount.target}"
                )
            if mount.source.is_file() != host_target.is_file():
                raise SandboxSpecError(
                    f"sandbox mount source/target type mismatch: {mount.target}"
                )
        host_cwd = self.runtime_root.joinpath(*self.cwd.parts[1:])
        if not host_cwd.is_dir():
            raise SandboxSpecError("cwd must exist inside runtime_root")


@runtime_checkable
class SandboxBackend(Protocol):
    @property
    def backend_id(self) -> str:
        ...

    @property
    def binary(self) -> Path:
        ...

    def build_argv(self, spec: SandboxSpec, command: Sequence[str]) -> tuple[str, ...]:
        ...

    def run(
        self,
        spec: SandboxSpec,
        command: Sequence[str],
        *,
        timeout: float | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        ...


def _validate_command(command: Sequence[str]) -> tuple[str, ...]:
    values = tuple(command)
    if not values:
        raise SandboxSpecError("sandbox command cannot be empty")
    if not all(isinstance(value, str) and value and not _contains_nul(value) for value in values):
        raise SandboxSpecError("sandbox command contains an invalid argument")
    executable = PurePosixPath(values[0])
    if not executable.is_absolute() or ".." in executable.parts:
        raise SandboxSpecError("sandbox executable must be an absolute normalized path")
    return values


class BubblewrapBackend:
    def __init__(self, binary: str | os.PathLike[str] = "/usr/bin/bwrap") -> None:
        self._binary = Path(binary)
        if not self._binary.is_absolute():
            raise SandboxSpecError("bubblewrap binary path must be absolute")

    @property
    def backend_id(self) -> str:
        return "bubblewrap"

    @property
    def binary(self) -> Path:
        return self._binary

    def build_argv(self, spec: SandboxSpec, command: Sequence[str]) -> tuple[str, ...]:
        if not isinstance(spec, SandboxSpec):
            raise SandboxSpecError("spec must be a SandboxSpec")
        spec.validate_host_inputs()
        values = _validate_command(command)
        argv: list[str] = [
            str(self.binary),
            "--unshare-user",
            "--unshare-pid",
            "--unshare-net",
            "--unshare-ipc",
            "--unshare-uts",
                "--cap-drop",
            "ALL",
            "--die-with-parent",
            "--new-session",
            "--clearenv",
            "--ro-bind",
            str(spec.runtime_root),
            "/",
            "--proc",
            "/proc",
            "--dev",
            "/dev",
            "--tmpfs",
            "/tmp",
        ]
        for mount in spec.mounts:
            argv.extend(
                ["--bind" if mount.writable else "--ro-bind", str(mount.source), str(mount.target)]
            )
        argv.extend(["--chdir", str(spec.cwd)])
        for key, value in spec.environment.items():
            argv.extend(["--setenv", key, value])
        argv.append("--")
        argv.extend(values)
        return tuple(argv)

    def run(
        self,
        spec: SandboxSpec,
        command: Sequence[str],
        *,
        timeout: float | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        if not self.binary.is_file():
            raise SandboxUnavailable(f"bubblewrap binary unavailable: {self.binary}")
        return subprocess.run(
            self.build_argv(spec, command),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=check,
        )


class RootlessPodmanBackend:
    def __init__(self, binary: str | os.PathLike[str] = "/usr/bin/podman") -> None:
        self._binary = Path(binary)
        if not self._binary.is_absolute():
            raise SandboxSpecError("podman binary path must be absolute")

    @property
    def backend_id(self) -> str:
        return "rootless_podman"

    @property
    def binary(self) -> Path:
        return self._binary

    def build_argv(self, spec: SandboxSpec, command: Sequence[str]) -> tuple[str, ...]:
        if not isinstance(spec, SandboxSpec):
            raise SandboxSpecError("spec must be a SandboxSpec")
        spec.validate_host_inputs()
        values = _validate_command(command)
        argv: list[str] = [
            str(self.binary),
            "run",
            "--rm",
            "--name",
            f"lac-{spec.instance_id}",
            "--read-only",
            "--network=none",
            "--http-proxy=false",
            "--no-hosts",
            "--no-hostname",
            "--pid=private",
            "--ipc=private",
            "--userns=keep-id",
            "--cap-drop=ALL",
            "--security-opt=no-new-privileges",
            "--pids-limit=128",
            "--tmpfs=/tmp:rw,noexec,nosuid,nodev,size=16m",
            "--workdir",
            str(spec.cwd),
        ]
        for mount in spec.mounts:
            if "," in str(mount.source) or "," in str(mount.target):
                raise SandboxSpecError("podman bind paths containing comma fail closed")
            option = f"type=bind,src={mount.source},dst={mount.target}"
            if not mount.writable:
                option += ",ro=true"
            argv.extend(["--mount", option])
        for key, value in spec.environment.items():
            argv.extend(["--env", f"{key}={value}"])
        # Podman --rootfs is a mode flag: the following positional argument
        # occupies the image slot and is interpreted as the exploded rootfs.
        argv.extend(["--rootfs", str(spec.runtime_root)])
        argv.extend(values)
        return tuple(argv)

    def run(
        self,
        spec: SandboxSpec,
        command: Sequence[str],
        *,
        timeout: float | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        if not self.binary.is_file():
            raise SandboxUnavailable(f"podman binary unavailable: {self.binary}")
        return subprocess.run(
            self.build_argv(spec, command),
            text=True,
            capture_output=True,
            timeout=timeout,
            check=check,
        )


def load_selected_backend(evidence_path: str | os.PathLike[str]) -> SandboxBackend:
    path = Path(evidence_path)
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SandboxUnavailable("sandbox qualification evidence is unavailable or malformed") from exc
    if payload.get("schema") != "lac.sandbox-qualification/v1" or payload.get("status") != "PASS":
        raise SandboxUnavailable("sandbox qualification evidence is not a passing v1 record")
    selected = payload.get("selected_backend")
    candidates = payload.get("candidates")
    if not isinstance(candidates, dict) or selected not in candidates:
        raise SandboxUnavailable("selected sandbox backend is not represented in evidence")
    candidate = candidates[selected]
    if not isinstance(candidate, dict) or candidate.get("status") != "PASS":
        raise SandboxUnavailable("selected sandbox backend did not qualify")
    controls = candidate.get("controls")
    if not isinstance(controls, dict) or any(controls.get(name) is not True for name in _REQUIRED_CONTROLS):
        raise SandboxUnavailable("selected sandbox backend lacks a required isolation control")
    binary = candidate.get("binary")
    if not isinstance(binary, str) or not binary.startswith("/"):
        raise SandboxUnavailable("selected sandbox backend has no absolute qualified binary")
    if selected == "bubblewrap":
        return BubblewrapBackend(binary)
    if selected == "rootless_podman":
        return RootlessPodmanBackend(binary)
    raise SandboxUnavailable("unknown selected sandbox backend fails closed")


def default_evidence_path() -> Path:
    return Path(__file__).resolve().parents[2] / "qualification" / "evidence" / "h001_sandbox.json"


def get_selected_backend() -> SandboxBackend:
    return load_selected_backend(default_evidence_path())
