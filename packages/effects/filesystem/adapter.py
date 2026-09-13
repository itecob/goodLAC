from __future__ import annotations

import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Iterator

from packages.core import EffectRequest, EffectRequestError, ExecutionLease, ExecutionLeaseError
from packages.sandbox import NetworkMode, SandboxMount, SandboxSpec, get_selected_backend


FILESYSTEM_ADAPTER_ID = "filesystem:v1"
FILESYSTEM_RESULT_SCHEMA = "lac.filesystem-effect-result/v1"
FILESYSTEM_READ_ACTION = "filesystem.read"
FILESYSTEM_CREATE_ACTION = "filesystem.create"
FILESYSTEM_REPLACE_ACTION = "filesystem.replace"
FILESYSTEM_DELETE_ACTION = "filesystem.delete"
_FILESYSTEM_ACTIONS = frozenset(
    {
        FILESYSTEM_READ_ACTION,
        FILESYSTEM_CREATE_ACTION,
        FILESYSTEM_REPLACE_ACTION,
        FILESYSTEM_DELETE_ACTION,
    }
)
_CONTROL_CHARACTER = re.compile(r"[\x00-\x1f\x7f]")


class FilesystemEffectError(ValueError):
    """The filesystem effect request or host boundary failed closed."""


@dataclass(frozen=True)
class FilesystemEffectResult:
    schema: str
    adapter_id: str
    request_id: str
    canonical_request_hash: str
    lease_id: str
    action: str
    resource: str
    path: str
    byte_count: int
    content_sha256: str
    content: str | None = None

    def to_record(self) -> dict[str, str | int | None]:
        return {
            "schema": self.schema,
            "adapter_id": self.adapter_id,
            "request_id": self.request_id,
            "canonical_request_hash": self.canonical_request_hash,
            "lease_id": self.lease_id,
            "action": self.action,
            "resource": self.resource,
            "path": self.path,
            "byte_count": self.byte_count,
            "content_sha256": self.content_sha256,
            "content": self.content,
        }


@dataclass(frozen=True)
class _FilesystemOperation:
    action: str
    path: str
    content: str | None


def _canonical_request(request: EffectRequest) -> EffectRequest:
    if not isinstance(request, EffectRequest):
        raise FilesystemEffectError("request must be a canonical EffectRequest")
    try:
        canonical = EffectRequest.from_record(request.to_record())
    except (EffectRequestError, TypeError, AttributeError) as exc:
        raise FilesystemEffectError("request failed canonical integrity validation") from exc
    if canonical != request:
        raise FilesystemEffectError("request is not canonical")
    return canonical


def _canonical_lease(lease: ExecutionLease) -> ExecutionLease:
    if not isinstance(lease, ExecutionLease):
        raise FilesystemEffectError("lease must be a canonical ExecutionLease")
    try:
        canonical = ExecutionLease.from_record(lease.to_record())
    except (ExecutionLeaseError, TypeError, AttributeError) as exc:
        raise FilesystemEffectError("lease failed canonical integrity validation") from exc
    if canonical != lease:
        raise FilesystemEffectError("lease is not canonical")
    return canonical


def _canonical_relative_path(value: object) -> str:
    if not isinstance(value, str) or not value:
        raise FilesystemEffectError("filesystem path must be a non-empty string")
    if _CONTROL_CHARACTER.search(value):
        raise FilesystemEffectError("filesystem path contains a control character")
    path = PurePosixPath(value)
    if path.is_absolute():
        raise FilesystemEffectError("filesystem path must be relative to the configured working root")
    if not path.parts or any(part in ("", ".", "..") for part in path.parts):
        raise FilesystemEffectError("filesystem path is not a canonical relative path")
    normalized = str(path)
    if normalized != value:
        raise FilesystemEffectError("filesystem path must use one canonical relative representation")
    return normalized


def _parse_operation(request: EffectRequest, *, resource: str) -> _FilesystemOperation:
    canonical = _canonical_request(request)
    if canonical.resource != resource:
        raise FilesystemEffectError("filesystem request targets a different configured resource")
    if canonical.action not in _FILESYSTEM_ACTIONS:
        raise FilesystemEffectError(f"unsupported filesystem action: {canonical.action!r}")
    arguments = canonical.arguments
    if canonical.action in (FILESYSTEM_READ_ACTION, FILESYSTEM_DELETE_ACTION):
        if set(arguments) != {"path"}:
            raise FilesystemEffectError("filesystem read/delete arguments must contain exactly 'path'")
        path = _canonical_relative_path(arguments["path"])
        return _FilesystemOperation(canonical.action, path, None)
    if set(arguments) != {"path", "content"}:
        raise FilesystemEffectError("filesystem create/replace arguments must contain exactly 'path' and 'content'")
    path = _canonical_relative_path(arguments["path"])
    content = arguments["content"]
    if not isinstance(content, str):
        raise FilesystemEffectError("filesystem content must be UTF-8 text")
    # Python strings may contain lone surrogates which are not valid UTF-8 payloads.
    try:
        content.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise FilesystemEffectError("filesystem content must be valid UTF-8 text") from exc
    return _FilesystemOperation(canonical.action, path, content)


def _copy_binary_and_libraries(binary: Path, rootfs: Path) -> Path:
    resolved = binary.resolve(strict=True)
    if not resolved.is_file():
        raise FilesystemEffectError(f"required sandbox helper is not a file: {resolved}")
    destination = rootfs / resolved.relative_to("/")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(resolved, destination)
    ldd = shutil.which("ldd")
    if not ldd:
        raise FilesystemEffectError("ldd is required to construct the bounded filesystem runtime")
    probe = subprocess.run(
        [ldd, str(resolved)],
        text=True,
        capture_output=True,
        check=False,
    )
    if probe.returncode != 0:
        raise FilesystemEffectError(f"ldd failed for sandbox helper: {resolved}")
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
    return resolved


@contextmanager
def _minimal_runtime(*, needs_input: bool) -> Iterator[tuple[Path, Path, Path, Path | None]]:
    bash = shutil.which("bash")
    cat = shutil.which("cat")
    if not bash or not cat:
        raise FilesystemEffectError("bash and cat are required by the fixed H002 filesystem helper")
    with tempfile.TemporaryDirectory(prefix="lac-h002-fs-runtime-") as tmp_name:
        base = Path(tmp_name)
        rootfs = base / "rootfs"
        for name in ("proc", "dev", "tmp", "workspace", "input"):
            (rootfs / name).mkdir(parents=True, exist_ok=True)
        input_file: Path | None = None
        if needs_input:
            input_file = base / "content"
            input_file.write_bytes(b"")
            (rootfs / "input" / "content").touch()
        bash_path = _copy_binary_and_libraries(Path(bash), rootfs)
        cat_path = _copy_binary_and_libraries(Path(cat), rootfs)
        yield rootfs, bash_path, cat_path, input_file


_FIXED_HELPER = r'''set -euo pipefail
umask 077
op="$1"
rel="$2"
cat_bin="$3"
cur="/workspace"
IFS='/' read -r -a parts <<< "$rel"
for part in "${parts[@]}"; do
  [[ -n "$part" && "$part" != "." && "$part" != ".." ]] || exit 64
  cur="$cur/$part"
  [[ ! -L "$cur" ]] || exit 65
done
case "$op" in
  read)
    [[ -f "$cur" && ! -L "$cur" ]] || exit 66
    "$cat_bin" -- "$cur"
    ;;
  create)
    [[ -d "${cur%/*}" ]] || exit 67
    [[ ! -e "$cur" && ! -L "$cur" ]] || exit 68
    set -C
    "$cat_bin" -- /input/content > "$cur"
    ;;
  replace)
    [[ -f "$cur" && ! -L "$cur" ]] || exit 69
    "$cat_bin" -- /input/content > "$cur"
    ;;
  *)
    exit 70
    ;;
esac
'''


class FilesystemEffectAdapter:
    """Typed UTF-8 workspace adapter bounded by the H001-selected Linux sandbox."""

    def __init__(
        self,
        working_root: str | os.PathLike[str],
        *,
        resource: str = "filesystem:workspace",
    ) -> None:
        root = Path(working_root)
        if not root.is_absolute():
            raise FilesystemEffectError("working_root must be absolute")
        if not isinstance(resource, str) or not resource or resource != resource.strip():
            raise FilesystemEffectError("resource must be a non-empty trimmed string")
        try:
            resolved = root.resolve(strict=True)
        except OSError as exc:
            raise FilesystemEffectError("working_root must exist") from exc
        if resolved != root or root.is_symlink() or not root.is_dir():
            raise FilesystemEffectError("working_root must be an existing non-symlink canonical directory")
        self._working_root = root
        self._resource = resource
        self._backend = get_selected_backend()

    @property
    def adapter_id(self) -> str:
        return FILESYSTEM_ADAPTER_ID

    @property
    def working_root(self) -> Path:
        return self._working_root

    @property
    def resource(self) -> str:
        return self._resource

    def supports(self, request: EffectRequest) -> bool:
        try:
            _parse_operation(request, resource=self._resource)
        except FilesystemEffectError:
            return False
        return True

    def _validate_host_shape(self, operation: _FilesystemOperation) -> None:
        cursor = self._working_root
        parts = PurePosixPath(operation.path).parts
        for index, part in enumerate(parts):
            cursor = cursor / part
            is_leaf = index == len(parts) - 1
            if cursor.is_symlink():
                raise FilesystemEffectError("filesystem path cannot traverse a symlink")
            if not is_leaf and not cursor.is_dir():
                raise FilesystemEffectError("filesystem parent path must exist as a real directory")
        leaf = self._working_root.joinpath(*parts)
        if operation.action == FILESYSTEM_READ_ACTION:
            if not leaf.is_file() or leaf.is_symlink():
                raise FilesystemEffectError("filesystem read requires an existing regular non-symlink file")
        elif operation.action == FILESYSTEM_CREATE_ACTION:
            if leaf.exists() or leaf.is_symlink():
                raise FilesystemEffectError("filesystem create requires an absent leaf")
            if not leaf.parent.is_dir() or leaf.parent.is_symlink():
                raise FilesystemEffectError("filesystem create parent must be an existing real directory")
        elif operation.action == FILESYSTEM_REPLACE_ACTION:
            if not leaf.is_file() or leaf.is_symlink():
                raise FilesystemEffectError("filesystem replace requires an existing regular non-symlink file")
        elif operation.action == FILESYSTEM_DELETE_ACTION:
            # Deletion is recognized so policy DENY can be evaluated, but H002 does not
            # expose a mutation implementation for it.
            return
        else:
            raise FilesystemEffectError("unknown filesystem action fails closed")

    def _run_operation(self, operation: _FilesystemOperation) -> str:
        if operation.action == FILESYSTEM_DELETE_ACTION:
            raise FilesystemEffectError("filesystem deletion is denied and has no H002 mutation implementation")
        self._validate_host_shape(operation)
        needs_input = operation.action in (FILESYSTEM_CREATE_ACTION, FILESYSTEM_REPLACE_ACTION)
        with _minimal_runtime(needs_input=needs_input) as (rootfs, bash_path, cat_path, input_file):
            mounts = [
                SandboxMount(
                    source=self._working_root,
                    target=PurePosixPath("/workspace"),
                    writable=needs_input,
                )
            ]
            op_name = "read"
            if needs_input:
                assert operation.content is not None and input_file is not None
                input_file.write_bytes(operation.content.encode("utf-8"))
                mounts.append(
                    SandboxMount(
                        source=input_file,
                        target=PurePosixPath("/input/content"),
                        writable=False,
                    )
                )
                op_name = "create" if operation.action == FILESYSTEM_CREATE_ACTION else "replace"
            instance = "fs-" + hashlib.sha256(
                f"{self._resource}\0{operation.action}\0{operation.path}".encode("utf-8")
            ).hexdigest()[:24]
            spec = SandboxSpec(
                runtime_root=rootfs,
                instance_id=instance,
                mounts=tuple(mounts),
                environment={"PATH": "/usr/bin", "HOME": "/nonexistent"},
                cwd=PurePosixPath("/workspace"),
                network=NetworkMode.NONE,
            )
            proc = self._backend.run(
                spec,
                [
                    str(bash_path),
                    "-c",
                    _FIXED_HELPER,
                    "lac-h002-filesystem",
                    op_name,
                    operation.path,
                    str(cat_path),
                ],
                timeout=10.0,
                check=False,
            )
            if proc.returncode != 0:
                detail = (proc.stderr or "").strip().replace("\n", " ")[-300:]
                raise FilesystemEffectError(
                    f"bounded filesystem helper failed closed (rc={proc.returncode})"
                    + (f": {detail}" if detail else "")
                )
            return proc.stdout if operation.action == FILESYSTEM_READ_ACTION else ""

    def invoke(
        self,
        request: EffectRequest,
        *,
        lease: ExecutionLease,
    ) -> FilesystemEffectResult:
        canonical_request = _canonical_request(request)
        canonical_lease = _canonical_lease(lease)
        if canonical_lease.request_id != canonical_request.request_id:
            raise FilesystemEffectError("execution lease binds a different request_id")
        operation = _parse_operation(canonical_request, resource=self._resource)
        output = self._run_operation(operation)
        content = output if operation.action == FILESYSTEM_READ_ACTION else operation.content
        assert content is not None
        encoded = content.encode("utf-8")
        digest = "sha256:" + hashlib.sha256(encoded).hexdigest()
        return FilesystemEffectResult(
            schema=FILESYSTEM_RESULT_SCHEMA,
            adapter_id=FILESYSTEM_ADAPTER_ID,
            request_id=canonical_request.request_id,
            canonical_request_hash=canonical_request.canonical_hash,
            lease_id=canonical_lease.lease_id,
            action=canonical_request.action,
            resource=canonical_request.resource,
            path=operation.path,
            byte_count=len(encoded),
            content_sha256=digest,
            content=output if operation.action == FILESYSTEM_READ_ACTION else None,
        )

    def reconcile(
        self,
        request: EffectRequest,
        *,
        lease: ExecutionLease,
    ) -> FilesystemEffectResult | None:
        operation = _parse_operation(request, resource=self._resource)
        if operation.action != FILESYSTEM_READ_ACTION:
            # PREPARED mutations are intentionally not guessed. A retry must not
            # duplicate or reinterpret an ambiguous host mutation.
            return None
        return self.invoke(request, lease=lease)
