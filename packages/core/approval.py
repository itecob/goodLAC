from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping


APPROVAL_SCHEMA = "lac.approval/v1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class ApprovalError(ValueError):
    """Base error for invalid or non-canonical approval records."""


class UnsupportedApprovalSchema(ApprovalError):
    """Raised when an approval schema is not supported."""


class ApprovalDecision(str, Enum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class ApprovalScope(str, Enum):
    ONCE = "ONCE"


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ApprovalError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ApprovalError(f"{field} must not have leading/trailing whitespace")
    return value


def _normalize_timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ApprovalError(f"{field} must be a non-empty RFC3339 timestamp")
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ApprovalError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ApprovalError(f"{field} must include a timezone")
    return (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


@dataclass(frozen=True)
class Approval:
    schema: str
    approval_id: str
    request_id: str
    policy_decision_id: str
    canonical_request_hash: str
    approver: str
    decision: ApprovalDecision
    scope: ApprovalScope
    created_at: str
    expires_at: str
    consumed_at: str | None

    @classmethod
    def create(
        cls,
        *,
        approval_id: str,
        request_id: str,
        policy_decision_id: str,
        canonical_request_hash: str,
        approver: str,
        decision: ApprovalDecision | str,
        scope: ApprovalScope | str,
        created_at: str,
        expires_at: str,
        consumed_at: str | None = None,
        schema: str = APPROVAL_SCHEMA,
    ) -> "Approval":
        if schema != APPROVAL_SCHEMA:
            raise UnsupportedApprovalSchema(f"unsupported approval schema: {schema!r}")
        try:
            decision_value = ApprovalDecision(decision)
        except (TypeError, ValueError) as exc:
            raise ApprovalError(f"unsupported approval decision: {decision!r}") from exc
        try:
            scope_value = ApprovalScope(scope)
        except (TypeError, ValueError) as exc:
            raise ApprovalError(f"unsupported approval scope: {scope!r}") from exc

        request_hash = _required_text(canonical_request_hash, "canonical_request_hash")
        if not _SHA256_RE.fullmatch(request_hash):
            raise ApprovalError(
                "canonical_request_hash must be lowercase sha256:<64 hex>"
            )
        normalized_created = _normalize_timestamp(created_at, "created_at")
        normalized_expires = _normalize_timestamp(expires_at, "expires_at")
        if normalized_expires <= normalized_created:
            raise ApprovalError("expires_at must be later than created_at")
        normalized_consumed = None
        if consumed_at is not None:
            normalized_consumed = _normalize_timestamp(consumed_at, "consumed_at")
            if decision_value is not ApprovalDecision.APPROVE:
                raise ApprovalError("only APPROVE records may have consumed_at")
            if normalized_consumed < normalized_created:
                raise ApprovalError("consumed_at cannot precede created_at")
            if normalized_consumed >= normalized_expires:
                raise ApprovalError("consumed_at must precede expires_at")

        return cls(
            schema=schema,
            approval_id=_required_text(approval_id, "approval_id"),
            request_id=_required_text(request_id, "request_id"),
            policy_decision_id=_required_text(policy_decision_id, "policy_decision_id"),
            canonical_request_hash=request_hash,
            approver=_required_text(approver, "approver"),
            decision=decision_value,
            scope=scope_value,
            created_at=normalized_created,
            expires_at=normalized_expires,
            consumed_at=normalized_consumed,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "Approval":
        required = {
            "schema",
            "approval_id",
            "request_id",
            "policy_decision_id",
            "canonical_request_hash",
            "approver",
            "decision",
            "scope",
            "created_at",
            "expires_at",
            "consumed_at",
        }
        observed = set(record)
        missing = required - observed
        unknown = observed - required
        if missing or unknown:
            raise ApprovalError(
                "invalid persisted approval fields; "
                f"missing={sorted(missing)} unknown={sorted(unknown)}"
            )
        return cls.create(
            schema=record["schema"],
            approval_id=record["approval_id"],
            request_id=record["request_id"],
            policy_decision_id=record["policy_decision_id"],
            canonical_request_hash=record["canonical_request_hash"],
            approver=record["approver"],
            decision=record["decision"],
            scope=record["scope"],
            created_at=record["created_at"],
            expires_at=record["expires_at"],
            consumed_at=record["consumed_at"],
        )

    def is_expired(self, at: str) -> bool:
        """Deterministically test expiry; the exact expiry instant is expired."""
        normalized_at = _normalize_timestamp(at, "at")
        return normalized_at >= self.expires_at

    def to_record(self) -> dict[str, str | None]:
        return {
            "schema": self.schema,
            "approval_id": self.approval_id,
            "request_id": self.request_id,
            "policy_decision_id": self.policy_decision_id,
            "canonical_request_hash": self.canonical_request_hash,
            "approver": self.approver,
            "decision": self.decision.value,
            "scope": self.scope.value,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "consumed_at": self.consumed_at,
        }
