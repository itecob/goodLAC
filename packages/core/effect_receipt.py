from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping

from .effect_request import canonical_json


EFFECT_EXECUTION_SCHEMA = "lac.effect-execution/v1"
EFFECT_RECEIPT_SCHEMA = "lac.effect-receipt/v1"


class EffectReceiptError(ValueError):
    """Base error for invalid effect execution/receipt state."""


class UnsupportedEffectReceiptSchema(EffectReceiptError):
    """Raised when an execution/receipt schema is not supported."""


class EffectExecutionState(str, Enum):
    LEASED = "LEASED"
    PREPARED = "PREPARED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class EffectOutcome(str, Enum):
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise EffectReceiptError(f"{field} must be a non-empty trimmed string")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field)


def _hash_text(value: Any, field: str) -> str:
    value = _required_text(value, field)
    if not value.startswith("sha256:") or len(value) != 71:
        raise EffectReceiptError(f"{field} must be a sha256: hash")
    try:
        int(value[7:], 16)
    except ValueError as exc:
        raise EffectReceiptError(f"{field} must contain hexadecimal SHA-256 material") from exc
    return value.lower()


def _normalize_timestamp(value: Any, field: str) -> str:
    value = _required_text(value, field)
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise EffectReceiptError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise EffectReceiptError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def canonical_result_json(value: Any) -> str:
    try:
        if hasattr(value, "to_record") and callable(value.to_record):
            value = value.to_record()
        encoded = canonical_json(value)
    except Exception as exc:
        raise EffectReceiptError("effect result must be canonical JSON or expose to_record()") from exc
    return encoded


def result_hash_for_json(result_json: str) -> str:
    if not isinstance(result_json, str):
        raise EffectReceiptError("result_json must be text")
    try:
        parsed = json.loads(result_json)
    except json.JSONDecodeError as exc:
        raise EffectReceiptError("result_json is invalid JSON") from exc
    if canonical_json(parsed) != result_json:
        raise EffectReceiptError("result_json is not canonical")
    return "sha256:" + hashlib.sha256(result_json.encode("utf-8")).hexdigest()


def deterministic_receipt_id(*, request_id: str, adapter_id: str, input_hash: str) -> str:
    material = canonical_json(
        {
            "request_id": _required_text(request_id, "request_id"),
            "adapter_id": _required_text(adapter_id, "adapter_id"),
            "input_hash": _hash_text(input_hash, "input_hash"),
        }
    )
    digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
    return f"receipt:{digest}"


@dataclass(frozen=True)
class EffectExecution:
    schema: str
    request_id: str
    canonical_request_hash: str
    idempotency_key: str
    adapter_id: str
    lease_id: str
    lease_hash: str
    input_hash: str
    approval_id: str | None
    state: EffectExecutionState
    leased_at: str
    prepared_at: str | None
    completed_at: str | None
    receipt_id: str | None

    @classmethod
    def create(
        cls,
        *,
        request_id: str,
        canonical_request_hash: str,
        idempotency_key: str,
        adapter_id: str,
        lease_id: str,
        lease_hash: str,
        input_hash: str,
        approval_id: str | None,
        state: EffectExecutionState | str,
        leased_at: str,
        prepared_at: str | None = None,
        completed_at: str | None = None,
        receipt_id: str | None = None,
        schema: str = EFFECT_EXECUTION_SCHEMA,
    ) -> "EffectExecution":
        if schema != EFFECT_EXECUTION_SCHEMA:
            raise UnsupportedEffectReceiptSchema(f"unsupported effect-execution schema: {schema!r}")
        try:
            normalized_state = state if isinstance(state, EffectExecutionState) else EffectExecutionState(state)
        except (TypeError, ValueError) as exc:
            raise EffectReceiptError("unknown effect execution state") from exc
        leased = _normalize_timestamp(leased_at, "leased_at")
        prepared = None if prepared_at is None else _normalize_timestamp(prepared_at, "prepared_at")
        completed = None if completed_at is None else _normalize_timestamp(completed_at, "completed_at")
        normalized_receipt = _optional_text(receipt_id, "receipt_id")
        if normalized_state is EffectExecutionState.LEASED:
            if prepared is not None or completed is not None or normalized_receipt is not None:
                raise EffectReceiptError("LEASED execution cannot have prepared/completed/receipt state")
        elif normalized_state is EffectExecutionState.PREPARED:
            if prepared is None or completed is not None or normalized_receipt is not None:
                raise EffectReceiptError("PREPARED execution requires prepared_at only")
            if prepared < leased:
                raise EffectReceiptError("prepared_at cannot precede leased_at")
        else:
            if prepared is None or completed is None or normalized_receipt is None:
                raise EffectReceiptError("terminal execution requires prepared_at, completed_at, and receipt_id")
            if prepared < leased or completed < prepared:
                raise EffectReceiptError("terminal execution timestamps are not monotonic")
        return cls(
            schema=schema,
            request_id=_required_text(request_id, "request_id"),
            canonical_request_hash=_hash_text(canonical_request_hash, "canonical_request_hash"),
            idempotency_key=_required_text(idempotency_key, "idempotency_key"),
            adapter_id=_required_text(adapter_id, "adapter_id"),
            lease_id=_required_text(lease_id, "lease_id"),
            lease_hash=_hash_text(lease_hash, "lease_hash"),
            input_hash=_hash_text(input_hash, "input_hash"),
            approval_id=_optional_text(approval_id, "approval_id"),
            state=normalized_state,
            leased_at=leased,
            prepared_at=prepared,
            completed_at=completed,
            receipt_id=normalized_receipt,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "EffectExecution":
        required = {
            "schema", "request_id", "canonical_request_hash", "idempotency_key",
            "adapter_id", "lease_id", "lease_hash", "input_hash", "approval_id",
            "state", "leased_at", "prepared_at", "completed_at", "receipt_id",
        }
        if set(record) != required:
            raise EffectReceiptError("invalid persisted effect-execution fields")
        return cls.create(**dict(record))

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "request_id": self.request_id,
            "canonical_request_hash": self.canonical_request_hash,
            "idempotency_key": self.idempotency_key,
            "adapter_id": self.adapter_id,
            "lease_id": self.lease_id,
            "lease_hash": self.lease_hash,
            "input_hash": self.input_hash,
            "approval_id": self.approval_id,
            "state": self.state.value,
            "leased_at": self.leased_at,
            "prepared_at": self.prepared_at,
            "completed_at": self.completed_at,
            "receipt_id": self.receipt_id,
        }


@dataclass(frozen=True)
class EffectReceipt:
    schema: str
    receipt_id: str
    request_id: str
    canonical_request_hash: str
    idempotency_key: str
    approval_id: str | None
    adapter_id: str
    lease_id: str
    input_hash: str
    started_at: str
    completed_at: str
    outcome: EffectOutcome
    result_json: str
    result_hash: str
    upstream_reference: str | None

    @classmethod
    def create(
        cls,
        *,
        receipt_id: str,
        request_id: str,
        canonical_request_hash: str,
        idempotency_key: str,
        approval_id: str | None,
        adapter_id: str,
        lease_id: str,
        input_hash: str,
        started_at: str,
        completed_at: str,
        outcome: EffectOutcome | str,
        result_json: str,
        result_hash: str,
        upstream_reference: str | None = None,
        schema: str = EFFECT_RECEIPT_SCHEMA,
    ) -> "EffectReceipt":
        if schema != EFFECT_RECEIPT_SCHEMA:
            raise UnsupportedEffectReceiptSchema(f"unsupported effect-receipt schema: {schema!r}")
        try:
            normalized_outcome = outcome if isinstance(outcome, EffectOutcome) else EffectOutcome(outcome)
        except (TypeError, ValueError) as exc:
            raise EffectReceiptError("unknown effect receipt outcome") from exc
        started = _normalize_timestamp(started_at, "started_at")
        completed = _normalize_timestamp(completed_at, "completed_at")
        if completed < started:
            raise EffectReceiptError("completed_at cannot precede started_at")
        computed_result_hash = result_hash_for_json(result_json)
        if _hash_text(result_hash, "result_hash") != computed_result_hash:
            raise EffectReceiptError("result_hash does not match canonical result_json")
        canonical_hash = _hash_text(canonical_request_hash, "canonical_request_hash")
        normalized_input_hash = _hash_text(input_hash, "input_hash")
        expected_receipt_id = deterministic_receipt_id(
            request_id=request_id, adapter_id=adapter_id, input_hash=normalized_input_hash
        )
        if _required_text(receipt_id, "receipt_id") != expected_receipt_id:
            raise EffectReceiptError("receipt_id does not match canonical receipt identity")
        return cls(
            schema=schema,
            receipt_id=expected_receipt_id,
            request_id=_required_text(request_id, "request_id"),
            canonical_request_hash=canonical_hash,
            idempotency_key=_required_text(idempotency_key, "idempotency_key"),
            approval_id=_optional_text(approval_id, "approval_id"),
            adapter_id=_required_text(adapter_id, "adapter_id"),
            lease_id=_required_text(lease_id, "lease_id"),
            input_hash=normalized_input_hash,
            started_at=started,
            completed_at=completed,
            outcome=normalized_outcome,
            result_json=result_json,
            result_hash=computed_result_hash,
            upstream_reference=_optional_text(upstream_reference, "upstream_reference"),
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "EffectReceipt":
        required = {
            "schema", "receipt_id", "request_id", "canonical_request_hash",
            "idempotency_key", "approval_id", "adapter_id", "lease_id",
            "input_hash", "started_at", "completed_at", "outcome", "result_json",
            "result_hash", "upstream_reference",
        }
        if set(record) != required:
            raise EffectReceiptError("invalid persisted effect-receipt fields")
        return cls.create(**dict(record))

    @property
    def result(self) -> Any:
        return json.loads(self.result_json)

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "receipt_id": self.receipt_id,
            "request_id": self.request_id,
            "canonical_request_hash": self.canonical_request_hash,
            "idempotency_key": self.idempotency_key,
            "approval_id": self.approval_id,
            "adapter_id": self.adapter_id,
            "lease_id": self.lease_id,
            "input_hash": self.input_hash,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "outcome": self.outcome.value,
            "result_json": self.result_json,
            "result_hash": self.result_hash,
            "upstream_reference": self.upstream_reference,
        }
