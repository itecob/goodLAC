from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping

from packages.core import EffectRequest
from packages.state.store import SQLiteStateStore, StateStoreError

from .manifest import CAPABILITY_MANIFEST_VERSION
from .registry import CapabilityRegistry, CapabilityRegistryError


PENDING_PERMISSION_RECORD_SCHEMA = "lac.pending-permission/v1"
PENDING_PERMISSION_QUEUE_SCHEMA = "lac.pending-permission-queue/v1"
CAPABILITY_DENIAL_SCHEMA = "lac.capability-denial/v1"
CAPABILITY_VALIDATION_SCHEMA = "lac.capability-validation/v1"

MAX_PENDING_PERMISSION_RECORDS = 128
MAX_PENDING_COUNT = 2_147_483_647
MAX_SHAPE_DEPTH = 6
MAX_SHAPE_NODES = 128
MAX_SHAPE_KEYS = 64

_QUEUE_KEY = "pending_permission.queue.v1"
_CLOSURE_PREFIX = "capability_denial.request."
_CREDENTIAL_KEY_RE = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|credential|authorization|cookie|private[_-]?key)",
    re.IGNORECASE,
)


class CapabilityRequestError(StateStoreError):
    """Base fail-closed error for P002 capability validation/quarantine."""


class CapabilityRequestIntegrityError(CapabilityRequestError):
    """Trusted registry or pending-permission durable state is inconsistent."""


class CapabilityRequestDenied(CapabilityRequestError):
    """The request is terminally closed by P002 capability validation."""

    def __init__(self, reason: str, pending_id: str | None = None):
        self.reason = reason
        self.pending_id = pending_id
        super().__init__(
            f"capability request terminally denied: {reason}"
            + (f" pending_id={pending_id}" if pending_id else "")
        )


@dataclass(frozen=True)
class CapabilityRequestContext:
    application_id: str
    skill_id: str
    capability_revision: int
    manifest_version: int
    resource_type: str

    def __post_init__(self) -> None:
        for field in ("application_id", "skill_id", "resource_type"):
            value = getattr(self, field)
            if not isinstance(value, str) or not value or value != value.strip():
                raise CapabilityRequestError(f"{field} must be a non-empty trimmed string")
        for field in ("capability_revision", "manifest_version"):
            value = getattr(self, field)
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise CapabilityRequestError(f"{field} must be a positive integer")


@dataclass(frozen=True)
class CapabilityValidation:
    schema: str
    application_id: str
    skill_id: str
    capability_revision: int
    manifest_version: int
    security_hash: str
    security_properties: tuple[str, ...]
    action: str
    resource_type: str
    resource: str


def _json(value: Any) -> str:
    try:
        return json.dumps(
            value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
        )
    except (TypeError, ValueError) as exc:
        raise CapabilityRequestError("P002 state must be canonical JSON") from exc


def _closure_key(request_id: str) -> str:
    digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
    return f"{_CLOSURE_PREFIX}{digest}"


def _shape_key(key: str) -> str:
    if _CREDENTIAL_KEY_RE.search(key):
        return "<credential-key>"
    return key[:128]


def _shape(value: Any, *, depth: int = 0, nodes: list[int] | None = None) -> Any:
    if nodes is None:
        nodes = [0]
    nodes[0] += 1
    if nodes[0] > MAX_SHAPE_NODES or depth > MAX_SHAPE_DEPTH:
        return {"type": "truncated"}
    if value is None:
        return {"type": "null"}
    if isinstance(value, bool):
        return {"type": "boolean"}
    if isinstance(value, int) and not isinstance(value, bool):
        return {"type": "integer"}
    if isinstance(value, float):
        return {"type": "number"}
    if isinstance(value, str):
        return {"type": "string"}
    if isinstance(value, list):
        return {
            "type": "array",
            "count_bucket": min(len(value), 9),
            "items": [_shape(v, depth=depth + 1, nodes=nodes) for v in value[:8]],
        }
    if isinstance(value, dict):
        keys = sorted(str(k) for k in value)[:MAX_SHAPE_KEYS]
        return {
            "type": "object",
            "properties": {
                _shape_key(k): _shape(value[k], depth=depth + 1, nodes=nodes) for k in keys
            },
            "truncated": len(value) > MAX_SHAPE_KEYS,
        }
    return {"type": "unsupported"}


def _fingerprint(
    request: EffectRequest,
    context: CapabilityRequestContext,
    reason: str,
    argument_shape: Any,
) -> str:
    material = {
        "principal_id": request.principal_id,
        "agent_id": request.agent_id,
        "application_id": context.application_id,
        "skill_id": context.skill_id,
        "capability_revision": context.capability_revision,
        "manifest_version": context.manifest_version,
        "action": request.action,
        "resource_type": context.resource_type,
        "resource": request.resource,
        "reason": reason,
        "argument_shape": argument_shape,
    }
    return "sha256:" + hashlib.sha256(_json(material).encode("utf-8")).hexdigest()


def _validate_value(value: Any, schema: Mapping[str, Any]) -> bool:
    stype = schema.get("type")
    if stype == "object":
        if not isinstance(value, dict):
            return False
        properties = schema["properties"]
        if not set(schema["required"]).issubset(value):
            return False
        if set(value) - set(properties):
            return False
        return all(_validate_value(v, properties[k]) for k, v in value.items())
    if stype == "array":
        if not isinstance(value, list):
            return False
        if len(value) > schema["maxItems"] or len(value) < schema.get("minItems", 0):
            return False
        return all(_validate_value(v, schema["items"]) for v in value)
    if stype == "string":
        if not isinstance(value, str):
            return False
        if len(value) > schema["maxLength"] or len(value) < schema.get("minLength", 0):
            return False
        return "enum" not in schema or value in schema["enum"]
    if stype == "integer":
        if isinstance(value, bool) or not isinstance(value, int):
            return False
        if not (schema["minimum"] <= value <= schema["maximum"]):
            return False
        return "enum" not in schema or value in schema["enum"]
    if stype == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        if not (schema["minimum"] <= value <= schema["maximum"]):
            return False
        return "enum" not in schema or value in schema["enum"]
    if stype == "boolean":
        return isinstance(value, bool) and ("enum" not in schema or value in schema["enum"])
    if stype == "null":
        return value is None
    return False


class PendingPermissionRepository:
    """Internal durable P002 queue and immutable terminal capability-denial closure."""

    def __init__(self, store: SQLiteStateStore):
        if not isinstance(store, SQLiteStateStore):
            raise CapabilityRequestError("store must be a SQLiteStateStore")
        self._store = store

    def _queue(self) -> dict[str, Any]:
        raw = self._store.get_system_state(_QUEUE_KEY)
        if raw is None:
            return {
                "schema": PENDING_PERMISSION_QUEUE_SCHEMA,
                "max_records": MAX_PENDING_PERMISSION_RECORDS,
                "overflow_distinct": 0,
                "records": [],
            }
        if (
            not isinstance(raw, dict)
            or raw.get("schema") != PENDING_PERMISSION_QUEUE_SCHEMA
            or raw.get("max_records") != MAX_PENDING_PERMISSION_RECORDS
            or not isinstance(raw.get("records"), list)
            or not isinstance(raw.get("overflow_distinct"), int)
            or raw["overflow_distinct"] < 0
            or len(raw["records"]) > MAX_PENDING_PERMISSION_RECORDS
        ):
            raise CapabilityRequestIntegrityError("pending-permission queue durable state is invalid")
        return raw

    def list_pending(self) -> list[dict[str, Any]]:
        return [dict(item) for item in self._queue()["records"]]

    def get_closure(self, request_id: str) -> dict[str, Any] | None:
        raw = self._store.get_system_state(_closure_key(request_id))
        if raw is None:
            return None
        required = {
            "schema", "request_id", "canonical_request_hash", "reason",
            "pending_id", "closed_at_utc",
        }
        if (
            not isinstance(raw, dict)
            or set(raw) != required
            or raw.get("schema") != CAPABILITY_DENIAL_SCHEMA
            or raw.get("request_id") != request_id
        ):
            raise CapabilityRequestIntegrityError("capability-denial closure is invalid")
        return dict(raw)

    def record_denial(
        self,
        request: EffectRequest,
        context: CapabilityRequestContext,
        *,
        reason: str,
        observed_at_utc: str,
    ) -> dict[str, Any]:
        existing_closure = self.get_closure(request.request_id)
        if existing_closure is not None:
            if existing_closure["canonical_request_hash"] != request.canonical_hash:
                raise CapabilityRequestIntegrityError(
                    "closed request_id is bound to a different canonical request hash"
                )
            return existing_closure

        argument_shape = _shape(request.arguments)
        fingerprint = _fingerprint(request, context, reason, argument_shape)
        pending_id = "pending:" + fingerprint.split(":", 1)[1]
        queue = self._queue()
        records = list(queue["records"])
        match_index = next(
            (i for i, record in enumerate(records) if record.get("fingerprint") == fingerprint),
            None,
        )
        if match_index is None:
            if len(records) < MAX_PENDING_PERMISSION_RECORDS:
                records.append(
                    {
                        "schema": PENDING_PERMISSION_RECORD_SCHEMA,
                        "pending_id": pending_id,
                        "fingerprint": fingerprint,
                        "status": "PENDING",
                        "principal_id": request.principal_id,
                        "agent_id": request.agent_id,
                        "application_id": context.application_id,
                        "skill_id": context.skill_id,
                        "capability_revision": context.capability_revision,
                        "manifest_version": context.manifest_version,
                        "action": request.action,
                        "resource_type": context.resource_type,
                        "resource": request.resource,
                        "reason": reason,
                        "argument_shape": argument_shape,
                        "first_seen_at_utc": observed_at_utc,
                        "last_seen_at_utc": observed_at_utc,
                        "count": 1,
                    }
                )
            else:
                queue["overflow_distinct"] = min(
                    MAX_PENDING_COUNT, queue["overflow_distinct"] + 1
                )
                pending_id = "pending:overflow"
        else:
            record = dict(records[match_index])
            record["last_seen_at_utc"] = observed_at_utc
            record["count"] = min(MAX_PENDING_COUNT, int(record["count"]) + 1)
            records[match_index] = record

        queue["records"] = records
        closure = {
            "schema": CAPABILITY_DENIAL_SCHEMA,
            "request_id": request.request_id,
            "canonical_request_hash": request.canonical_hash,
            "reason": reason,
            "pending_id": pending_id,
            "closed_at_utc": observed_at_utc,
        }
        try:
            with self._store.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO system_state(key, value_json, updated_at_utc)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at_utc = excluded.updated_at_utc
                    """,
                    (_QUEUE_KEY, _json(queue), observed_at_utc),
                )
                conn.execute(
                    "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?)",
                    (_closure_key(request.request_id), _json(closure), observed_at_utc),
                )
        except Exception as exc:
            if isinstance(exc, StateStoreError):
                raise
            raise CapabilityRequestError("pending-permission denial persistence failed atomically") from exc
        return closure


class CapabilityRequestValidator:
    """Validate a request against one immutable registered capability revision."""

    def __init__(self, store: SQLiteStateStore):
        self._registry = CapabilityRegistry(store)
        self._pending = PendingPermissionRepository(store)

    def _deny(
        self,
        request: EffectRequest,
        context: CapabilityRequestContext,
        *,
        reason: str,
        observed_at_utc: str,
    ) -> None:
        closure = self._pending.record_denial(
            request, context, reason=reason, observed_at_utc=observed_at_utc
        )
        raise CapabilityRequestDenied(reason, closure["pending_id"])

    def validate_or_quarantine(
        self,
        request: EffectRequest,
        *,
        context: CapabilityRequestContext,
        observed_at_utc: str,
    ) -> CapabilityValidation:
        if not isinstance(request, EffectRequest):
            raise CapabilityRequestError("request must be a canonical EffectRequest")
        if not isinstance(context, CapabilityRequestContext):
            raise CapabilityRequestError(
                "capability-aware dispatch requires CapabilityRequestContext"
            )
        if not isinstance(observed_at_utc, str) or not observed_at_utc:
            raise CapabilityRequestError("observed_at_utc is required")

        closure = self._pending.get_closure(request.request_id)
        if closure is not None:
            if closure["canonical_request_hash"] != request.canonical_hash:
                raise CapabilityRequestIntegrityError(
                    "closed request_id is bound to a different canonical request"
                )
            raise CapabilityRequestDenied(closure["reason"], closure["pending_id"])

        try:
            registration = self._registry.get_revision(
                context.application_id, context.skill_id, context.capability_revision
            )
        except CapabilityRegistryError as exc:
            raise CapabilityRequestIntegrityError(
                "capability registry failed closed during request validation"
            ) from exc
        if registration is None:
            self._deny(
                request, context, reason="UNKNOWN_CAPABILITY_OR_REVISION",
                observed_at_utc=observed_at_utc,
            )
        manifest = registration.manifest
        if (
            context.manifest_version != CAPABILITY_MANIFEST_VERSION
            or manifest.manifest_version != context.manifest_version
        ):
            self._deny(
                request, context, reason="UNSUPPORTED_MANIFEST_VERSION",
                observed_at_utc=observed_at_utc,
            )
        action = manifest.action(request.action)
        if action is None:
            self._deny(
                request, context, reason="UNKNOWN_ACTION",
                observed_at_utc=observed_at_utc,
            )
        if context.resource_type != action["resource"]["type"]:
            self._deny(
                request, context, reason="UNKNOWN_RESOURCE_TYPE",
                observed_at_utc=observed_at_utc,
            )
        if request.resource not in action["resource"]["selectors"]:
            self._deny(
                request, context, reason="UNKNOWN_RESOURCE_SCOPE",
                observed_at_utc=observed_at_utc,
            )
        if not _validate_value(request.arguments, action["arguments"]):
            self._deny(
                request, context, reason="MATERIAL_ARGUMENT_SHAPE",
                observed_at_utc=observed_at_utc,
            )
        return CapabilityValidation(
            schema=CAPABILITY_VALIDATION_SCHEMA,
            application_id=context.application_id,
            skill_id=context.skill_id,
            capability_revision=context.capability_revision,
            manifest_version=context.manifest_version,
            security_hash=registration.security_hash,
            security_properties=tuple(action["security_properties"]),
            action=request.action,
            resource_type=context.resource_type,
            resource=request.resource,
        )
