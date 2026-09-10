from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


EFFECT_REQUEST_SCHEMA = "lac.effect-request/v1"


class EffectRequestError(ValueError):
    """Base error for invalid or non-canonical effect requests."""


class UnsupportedEffectRequestSchema(EffectRequestError):
    """Raised when an effect-request schema is not supported."""


def _normalize_timestamp(value: str, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise EffectRequestError(f"{field} must be a non-empty RFC3339 timestamp")
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise EffectRequestError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EffectRequestError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise EffectRequestError(f"{path} contains a non-finite number")
        return
    if isinstance(value, list):
        for idx, item in enumerate(value):
            _validate_json_value(item, f"{path}[{idx}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise EffectRequestError(f"{path} contains a non-string object key")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise EffectRequestError(f"{path} contains a value outside the canonical JSON data model")


def canonical_json(value: Any) -> str:
    """Deterministic UTF-8 JSON representation used by LAC v0.1 hashing."""
    _validate_json_value(value)
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise EffectRequestError("value cannot be encoded as canonical JSON") from exc


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise EffectRequestError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise EffectRequestError(f"{field} must not have leading/trailing whitespace")
    return value


@dataclass(frozen=True)
class EffectRequest:
    schema: str
    request_id: str
    run_id: str
    principal_id: str
    agent_id: str
    action: str
    resource: str
    arguments_json: str
    idempotency_key: str
    created_at: str
    expires_at: str
    canonical_hash: str

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        run_id: str,
        principal_id: str,
        agent_id: str,
        action: str,
        resource: str,
        arguments: Mapping[str, Any],
        idempotency_key: str,
        created_at: str,
        expires_at: str,
        schema: str = EFFECT_REQUEST_SCHEMA,
    ) -> "EffectRequest":
        if schema != EFFECT_REQUEST_SCHEMA:
            raise UnsupportedEffectRequestSchema(f"unsupported effect-request schema: {schema!r}")

        normalized = {
            "schema": schema,
            "request_id": _required_text(request_id, "request_id"),
            "run_id": _required_text(run_id, "run_id"),
            "principal_id": _required_text(principal_id, "principal_id"),
            "agent_id": _required_text(agent_id, "agent_id"),
            "action": _required_text(action, "action"),
            "resource": _required_text(resource, "resource"),
            "idempotency_key": _required_text(idempotency_key, "idempotency_key"),
            "created_at": _normalize_timestamp(created_at, "created_at"),
            "expires_at": _normalize_timestamp(expires_at, "expires_at"),
        }
        if not isinstance(arguments, Mapping):
            raise EffectRequestError("arguments must be a JSON object")
        arguments_json = canonical_json(dict(arguments))
        if normalized["expires_at"] <= normalized["created_at"]:
            raise EffectRequestError("expires_at must be later than created_at")

        material = {**normalized, "arguments": json.loads(arguments_json)}
        digest = hashlib.sha256(canonical_json(material).encode("utf-8")).hexdigest()
        return cls(
            schema=schema,
            request_id=normalized["request_id"],
            run_id=normalized["run_id"],
            principal_id=normalized["principal_id"],
            agent_id=normalized["agent_id"],
            action=normalized["action"],
            resource=normalized["resource"],
            arguments_json=arguments_json,
            idempotency_key=normalized["idempotency_key"],
            created_at=normalized["created_at"],
            expires_at=normalized["expires_at"],
            canonical_hash=f"sha256:{digest}",
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "EffectRequest":
        required = {
            "schema", "request_id", "run_id", "principal_id", "agent_id",
            "action", "resource", "arguments_json", "idempotency_key",
            "created_at", "expires_at", "canonical_hash",
        }
        observed = set(record)
        missing = required - observed
        unknown = observed - required
        if missing or unknown:
            raise EffectRequestError(
                f"invalid persisted effect-request fields; missing={sorted(missing)} unknown={sorted(unknown)}"
            )
        try:
            arguments = json.loads(record["arguments_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise EffectRequestError("persisted arguments_json is invalid") from exc
        reconstructed = cls.create(
            schema=record["schema"], request_id=record["request_id"], run_id=record["run_id"],
            principal_id=record["principal_id"], agent_id=record["agent_id"], action=record["action"],
            resource=record["resource"], arguments=arguments, idempotency_key=record["idempotency_key"],
            created_at=record["created_at"], expires_at=record["expires_at"],
        )
        if reconstructed.arguments_json != record["arguments_json"]:
            raise EffectRequestError("persisted arguments_json is not canonical")
        if reconstructed.canonical_hash != record["canonical_hash"]:
            raise EffectRequestError("persisted canonical_hash does not match request")
        return reconstructed

    @property
    def arguments(self) -> dict[str, Any]:
        return json.loads(self.arguments_json)

    def canonical_material(self) -> dict[str, Any]:
        return {
            "schema": self.schema, "request_id": self.request_id, "run_id": self.run_id,
            "principal_id": self.principal_id, "agent_id": self.agent_id, "action": self.action,
            "resource": self.resource, "arguments": self.arguments, "idempotency_key": self.idempotency_key,
            "created_at": self.created_at, "expires_at": self.expires_at,
        }

    def canonical_json(self) -> str:
        return canonical_json(self.canonical_material())

    def to_record(self) -> dict[str, str]:
        return {
            "schema": self.schema, "request_id": self.request_id, "run_id": self.run_id,
            "principal_id": self.principal_id, "agent_id": self.agent_id, "action": self.action,
            "resource": self.resource, "arguments_json": self.arguments_json,
            "idempotency_key": self.idempotency_key, "created_at": self.created_at,
            "expires_at": self.expires_at, "canonical_hash": self.canonical_hash,
        }
