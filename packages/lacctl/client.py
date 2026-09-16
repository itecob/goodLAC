from __future__ import annotations

import hashlib
import json
import os
import socket
import stat
import struct
import sys
from pathlib import Path
from typing import Any, Mapping

ADMIN_REQUEST_SCHEMA = "lac.admin-request/v1"
ADMIN_RESPONSE_SCHEMA = "lac.admin-response/v1"
ADMIN_SOCKET_RELATIVE_PATH = Path("lac") / "admin-v1.sock"
MAX_ADMIN_MESSAGE_BYTES = 262_144
MAX_ADMIN_REQUEST_ID = 160
CLIENT_TIMEOUT_SECONDS = 2.0

ADMIN_OPERATIONS = frozenset(
    {
        "skills.list",
        "skills.show",
        "permissions.list",
        "permissions.show",
        "permissions.replace",
        "permissions.revoke",
        "pending.list",
        "pending.show",
        "pending.resolve",
        "pending.dismiss",
        "approvals.list",
        "approvals.show",
        "approvals.approve",
        "approvals.reject",
    }
)


class LacctlError(RuntimeError):
    """Base fail-closed lacctl client error."""

    code = "LACCTL_ERROR"


class LacctlBoundaryError(LacctlError):
    code = "ADMIN_BOUNDARY_FAILURE"


class LacctlUnavailable(LacctlError):
    code = "ADMIN_ENDPOINT_UNAVAILABLE"


class LacctlProtocolError(LacctlError):
    code = "ADMIN_PROTOCOL_FAILURE"


class LacctlRequestRejected(LacctlError):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


class _DuplicateKey(ValueError):
    pass


def _strict_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise _DuplicateKey(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise LacctlProtocolError("administrator material must be canonical JSON") from exc


def strict_json_loads(text: str) -> Any:
    try:
        return json.loads(text, object_pairs_hook=_strict_pairs)
    except _DuplicateKey as exc:
        raise LacctlProtocolError(str(exc)) from exc
    except json.JSONDecodeError as exc:
        raise LacctlProtocolError("administrator material is invalid JSON") from exc


def _bounded_text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise LacctlProtocolError(f"{field} must be a bounded non-empty trimmed string")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise LacctlProtocolError(f"{field} contains a control character")
    return value


def _require_owner_private_directory(path: Path, *, owner_uid: int) -> Path:
    if not path.is_absolute():
        raise LacctlBoundaryError("administrator runtime directory must be absolute")
    try:
        info = path.lstat()
    except FileNotFoundError as exc:
        raise LacctlUnavailable("administrator runtime directory is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISDIR(info.st_mode):
        raise LacctlBoundaryError("administrator runtime directory must be a real directory")
    if info.st_uid != owner_uid:
        raise LacctlBoundaryError("administrator runtime directory has unexpected owner UID")
    if stat.S_IMODE(info.st_mode) & 0o077:
        raise LacctlBoundaryError("administrator runtime directory grants group/other permissions")
    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise LacctlBoundaryError("administrator runtime directory cannot be resolved safely") from exc
    if resolved != path:
        raise LacctlBoundaryError("administrator runtime directory must be canonical and non-symlinked")
    return path


def resolve_admin_socket_path() -> Path:
    if os.name != "posix" or not sys.platform.startswith("linux") or not hasattr(socket, "SO_PEERCRED"):
        raise LacctlBoundaryError("LAC v0.1 administrator client requires Linux SO_PEERCRED")
    owner_uid = os.getuid()
    runtime_dir = Path(os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{owner_uid}")
    runtime_dir = _require_owner_private_directory(runtime_dir, owner_uid=owner_uid)
    lac_dir = runtime_dir / "lac"
    _require_owner_private_directory(lac_dir, owner_uid=owner_uid)
    socket_path = lac_dir / "admin-v1.sock"
    try:
        info = socket_path.lstat()
    except FileNotFoundError as exc:
        raise LacctlUnavailable("administrator endpoint is unavailable") from exc
    if stat.S_ISLNK(info.st_mode) or not stat.S_ISSOCK(info.st_mode):
        raise LacctlBoundaryError("administrator endpoint is not a real Unix socket")
    if info.st_uid != owner_uid:
        raise LacctlBoundaryError("administrator endpoint has unexpected owner UID")
    if stat.S_IMODE(info.st_mode) != 0o600:
        raise LacctlBoundaryError("administrator endpoint must be mode 0600")
    return socket_path


def _request_id(operation: str, arguments: Mapping[str, Any]) -> str:
    material = canonical_json({"operation": operation, "arguments": dict(arguments)})
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"admin:lacctl:{digest}"


def encode_request(operation: str, arguments: Mapping[str, Any]) -> tuple[str, bytes]:
    if operation not in ADMIN_OPERATIONS:
        raise LacctlProtocolError(f"unsupported administrator operation: {operation!r}")
    if not isinstance(arguments, Mapping):
        raise LacctlProtocolError("administrator arguments must be an object")
    normalized = dict(arguments)
    request_id = _request_id(operation, normalized)
    payload = {
        "schema": ADMIN_REQUEST_SCHEMA,
        "request_id": request_id,
        "operation": operation,
        "arguments": normalized,
    }
    encoded = canonical_json(payload).encode("utf-8") + b"\n"
    if len(encoded) > MAX_ADMIN_MESSAGE_BYTES:
        raise LacctlProtocolError("administrator request exceeds maximum size")
    return request_id, encoded


def decode_response_line(payload: bytes, *, expected_request_id: str) -> Any:
    if not isinstance(payload, (bytes, bytearray)):
        raise LacctlProtocolError("administrator response payload must be bytes")
    raw = bytes(payload)
    if not raw or len(raw) > MAX_ADMIN_MESSAGE_BYTES:
        raise LacctlProtocolError("administrator response size is invalid")
    if not raw.endswith(b"\n"):
        raise LacctlProtocolError("administrator response framing requires newline")
    raw = raw[:-1]
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise LacctlProtocolError("administrator response must be UTF-8") from exc
    value = strict_json_loads(text)
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "request_id",
        "ok",
        "result",
        "error",
    }:
        raise LacctlProtocolError("administrator response fields are invalid")
    if value["schema"] != ADMIN_RESPONSE_SCHEMA:
        raise LacctlProtocolError("unsupported administrator response schema")
    response_request_id = _bounded_text(value["request_id"], "request_id", MAX_ADMIN_REQUEST_ID)
    if response_request_id != expected_request_id:
        raise LacctlProtocolError("administrator response request_id does not match request")
    if not isinstance(value["ok"], bool):
        raise LacctlProtocolError("administrator response ok must be boolean")
    # Reject non-canonical JSON values such as NaN even if Python's parser accepted them.
    canonical_json(value)
    if value["ok"]:
        if value["error"] is not None:
            raise LacctlProtocolError("successful administrator response contains error material")
        return value["result"]
    if value["result"] is not None or not isinstance(value["error"], dict):
        raise LacctlProtocolError("failed administrator response is malformed")
    error = value["error"]
    if set(error) != {"code", "message"}:
        raise LacctlProtocolError("administrator error response fields are invalid")
    code = _bounded_text(error["code"], "error.code", 96)
    message = _bounded_text(error["message"], "error.message", 1024)
    raise LacctlRequestRejected(code, message)


def _receive_one_line(connection: socket.socket) -> bytes:
    data = bytearray()
    while True:
        room = MAX_ADMIN_MESSAGE_BYTES + 1 - len(data)
        if room <= 0:
            raise LacctlProtocolError("administrator response exceeds maximum size")
        chunk = connection.recv(min(65536, room))
        if not chunk:
            raise LacctlProtocolError("administrator connection closed before response newline")
        data.extend(chunk)
        if len(data) > MAX_ADMIN_MESSAGE_BYTES:
            raise LacctlProtocolError("administrator response exceeds maximum size")
        if b"\n" in data:
            break
    first, separator, trailing = bytes(data).partition(b"\n")
    if not separator:
        raise LacctlProtocolError("administrator response framing requires newline")
    if trailing.strip():
        raise LacctlProtocolError("administrator connection returned multiple response objects")
    return first + b"\n"


class LacctlClient:
    """Thin P004 v1 local administrator client with no canonical-state access."""

    def call(self, operation: str, arguments: Mapping[str, Any]) -> Any:
        request_id, payload = encode_request(operation, arguments)
        socket_path = resolve_admin_socket_path()
        owner_uid = os.getuid()
        connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        connection.settimeout(CLIENT_TIMEOUT_SECONDS)
        try:
            try:
                connection.connect(str(socket_path))
            except OSError as exc:
                raise LacctlUnavailable("administrator endpoint connection failed") from exc
            try:
                credentials = connection.getsockopt(
                    socket.SOL_SOCKET, socket.SO_PEERCRED, struct.calcsize("3i")
                )
                pid, peer_uid, gid = struct.unpack("3i", credentials)
            except (OSError, struct.error) as exc:
                raise LacctlBoundaryError("administrator peer identity could not be verified") from exc
            if pid <= 0 or peer_uid != owner_uid or gid < 0:
                raise LacctlBoundaryError("administrator peer identity does not match owner boundary")
            # No request bytes are sent until the server-side peer UID has been verified locally.
            try:
                connection.sendall(payload)
                response = _receive_one_line(connection)
            except socket.timeout as exc:
                raise LacctlUnavailable("administrator endpoint timed out") from exc
            except OSError as exc:
                raise LacctlUnavailable("administrator endpoint transport failed") from exc
        finally:
            connection.close()
        return decode_response_line(response, expected_request_id=request_id)
