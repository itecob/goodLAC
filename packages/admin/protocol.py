from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Mapping


ADMIN_REQUEST_SCHEMA = "lac.admin-request/v1"
ADMIN_RESPONSE_SCHEMA = "lac.admin-response/v1"
MAX_ADMIN_MESSAGE_BYTES = 262_144
MAX_ADMIN_REQUEST_ID = 160

ADMIN_OPERATIONS = frozenset(
    {
        "skills.list",
        "skills.show",
        "skills.register",
        "permissions.list",
        "permissions.show",
        "permissions.replace",
        "permissions.revoke",
        "permissions.decide",
        "pending.list",
        "pending.show",
        "pending.resolve",
        "pending.dismiss",
        "emergency.status",
        "emergency.pause",
        "emergency.resume",
        "approvals.list",
        "approvals.show",
        "approvals.approve",
        "approvals.reject",
    }
)


class AdminProtocolError(ValueError):
    """A local administrator protocol message is invalid or unsupported."""


class _DuplicateKey(AdminProtocolError):
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
        raise AdminProtocolError("administrator protocol material must be canonical JSON") from exc


def _required_text(value: Any, field: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AdminProtocolError(f"{field} must be a non-empty trimmed string")
    if len(value) > maximum:
        raise AdminProtocolError(f"{field} exceeds maximum length {maximum}")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise AdminProtocolError(f"{field} contains a control character")
    return value


@dataclass(frozen=True)
class AdminRequest:
    schema: str
    request_id: str
    operation: str
    arguments: dict[str, Any]

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        operation: str,
        arguments: Mapping[str, Any],
        schema: str = ADMIN_REQUEST_SCHEMA,
    ) -> "AdminRequest":
        if schema != ADMIN_REQUEST_SCHEMA:
            raise AdminProtocolError(f"unsupported administrator request schema: {schema!r}")
        normalized_request_id = _required_text(
            request_id, "request_id", maximum=MAX_ADMIN_REQUEST_ID
        )
        normalized_operation = _required_text(operation, "operation", maximum=96)
        if normalized_operation not in ADMIN_OPERATIONS:
            raise AdminProtocolError(f"unsupported administrator operation: {normalized_operation!r}")
        if not isinstance(arguments, Mapping):
            raise AdminProtocolError("arguments must be a JSON object")
        normalized_arguments = dict(arguments)
        # Round-trip through the strict canonical encoder to reject non-JSON values/NaN.
        canonical_json(normalized_arguments)
        return cls(
            schema=ADMIN_REQUEST_SCHEMA,
            request_id=normalized_request_id,
            operation=normalized_operation,
            arguments=normalized_arguments,
        )

    def to_material(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "request_id": self.request_id,
            "operation": self.operation,
            "arguments": self.arguments,
        }


def decode_request_line(payload: bytes) -> AdminRequest:
    if not isinstance(payload, (bytes, bytearray)):
        raise AdminProtocolError("administrator request payload must be bytes")
    raw = bytes(payload)
    if not raw or len(raw) > MAX_ADMIN_MESSAGE_BYTES:
        raise AdminProtocolError("administrator request size is invalid")
    if raw.endswith(b"\n"):
        raw = raw[:-1]
    if not raw:
        raise AdminProtocolError("administrator request is empty")
    try:
        text = raw.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise AdminProtocolError("administrator request must be UTF-8") from exc
    try:
        value = json.loads(text, object_pairs_hook=_strict_pairs)
    except _DuplicateKey:
        raise
    except json.JSONDecodeError as exc:
        raise AdminProtocolError("administrator request is invalid JSON") from exc
    if not isinstance(value, dict) or set(value) != {
        "schema",
        "request_id",
        "operation",
        "arguments",
    }:
        raise AdminProtocolError("administrator request fields are invalid")
    return AdminRequest.create(
        schema=value["schema"],
        request_id=value["request_id"],
        operation=value["operation"],
        arguments=value["arguments"],
    )


def success_response(request_id: str, result: Any) -> dict[str, Any]:
    request_id = _required_text(request_id, "request_id", maximum=MAX_ADMIN_REQUEST_ID)
    canonical_json(result)
    return {
        "schema": ADMIN_RESPONSE_SCHEMA,
        "request_id": request_id,
        "ok": True,
        "result": result,
        "error": None,
    }


def error_response(request_id: str, *, code: str, message: str) -> dict[str, Any]:
    request_id = _required_text(request_id, "request_id", maximum=MAX_ADMIN_REQUEST_ID)
    code = _required_text(code, "error.code", maximum=96)
    message = _required_text(message, "error.message", maximum=1024)
    return {
        "schema": ADMIN_RESPONSE_SCHEMA,
        "request_id": request_id,
        "ok": False,
        "result": None,
        "error": {"code": code, "message": message},
    }


def encode_response(response: Mapping[str, Any]) -> bytes:
    if not isinstance(response, Mapping):
        raise AdminProtocolError("administrator response must be a JSON object")
    value = dict(response)
    if set(value) != {"schema", "request_id", "ok", "result", "error"}:
        raise AdminProtocolError("administrator response fields are invalid")
    if value["schema"] != ADMIN_RESPONSE_SCHEMA:
        raise AdminProtocolError("administrator response schema is invalid")
    if not isinstance(value["ok"], bool):
        raise AdminProtocolError("administrator response ok must be boolean")
    _required_text(value["request_id"], "request_id", maximum=MAX_ADMIN_REQUEST_ID)
    if value["ok"]:
        if value["error"] is not None:
            raise AdminProtocolError("successful administrator response cannot contain error")
    else:
        if value["result"] is not None or not isinstance(value["error"], Mapping):
            raise AdminProtocolError("failed administrator response is malformed")
    encoded = canonical_json(value).encode("utf-8") + b"\n"
    if len(encoded) > MAX_ADMIN_MESSAGE_BYTES:
        raise AdminProtocolError("administrator response exceeds maximum size")
    return encoded
