from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Mapping, Sequence

from .effect_request import canonical_json


POLICY_DECISION_SCHEMA = "lac.policy-decision/v1"
_SHA256_RE = re.compile(r"^sha256:[0-9a-f]{64}$")


class PolicyDecisionError(ValueError):
    """Base error for invalid or non-canonical policy decisions."""


class UnsupportedPolicyDecisionSchema(PolicyDecisionError):
    """Raised when a policy-decision schema is not supported."""


class PolicyDecisionValue(str, Enum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


POLICY_PRECEDENCE: Mapping[PolicyDecisionValue, int] = {
    PolicyDecisionValue.ALLOW: 1,
    PolicyDecisionValue.REQUIRE_APPROVAL: 2,
    PolicyDecisionValue.DENY: 3,
}


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyDecisionError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise PolicyDecisionError(f"{field} must not have leading/trailing whitespace")
    return value


def _normalize_timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise PolicyDecisionError(f"{field} must be a non-empty RFC3339 timestamp")
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise PolicyDecisionError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PolicyDecisionError(f"{field} must include a timezone")
    return (
        parsed.astimezone(timezone.utc)
        .isoformat(timespec="microseconds")
        .replace("+00:00", "Z")
    )


def _normalize_reason_codes(reason_codes: Sequence[str]) -> tuple[str, ...]:
    if isinstance(reason_codes, (str, bytes)):
        raise PolicyDecisionError("reason_codes must be a sequence of strings")
    normalized: list[str] = []
    for code in reason_codes:
        normalized.append(_required_text(code, "reason_code"))
    if not normalized:
        raise PolicyDecisionError("at least one reason_code is required")
    return tuple(sorted(set(normalized)))


@dataclass(frozen=True)
class PolicyDecision:
    schema: str
    decision_id: str
    request_id: str
    decision: PolicyDecisionValue
    policy_revision: str
    reason_codes: tuple[str, ...]
    evaluated_at: str
    canonical_request_hash: str

    @classmethod
    def create(
        cls,
        *,
        decision_id: str,
        request_id: str,
        decision: PolicyDecisionValue | str,
        policy_revision: str,
        reason_codes: Sequence[str],
        evaluated_at: str,
        canonical_request_hash: str,
        schema: str = POLICY_DECISION_SCHEMA,
    ) -> "PolicyDecision":
        if schema != POLICY_DECISION_SCHEMA:
            raise UnsupportedPolicyDecisionSchema(
                f"unsupported policy-decision schema: {schema!r}"
            )
        try:
            decision_value = PolicyDecisionValue(decision)
        except (TypeError, ValueError) as exc:
            raise PolicyDecisionError(f"unsupported policy decision: {decision!r}") from exc

        request_hash = _required_text(canonical_request_hash, "canonical_request_hash")
        if not _SHA256_RE.fullmatch(request_hash):
            raise PolicyDecisionError(
                "canonical_request_hash must be lowercase sha256:<64 hex>"
            )

        return cls(
            schema=schema,
            decision_id=_required_text(decision_id, "decision_id"),
            request_id=_required_text(request_id, "request_id"),
            decision=decision_value,
            policy_revision=_required_text(policy_revision, "policy_revision"),
            reason_codes=_normalize_reason_codes(reason_codes),
            evaluated_at=_normalize_timestamp(evaluated_at, "evaluated_at"),
            canonical_request_hash=request_hash,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "PolicyDecision":
        required = {
            "schema",
            "decision_id",
            "request_id",
            "decision",
            "policy_revision",
            "reason_codes_json",
            "evaluated_at",
            "canonical_request_hash",
        }
        observed = set(record)
        missing = required - observed
        unknown = observed - required
        if missing or unknown:
            raise PolicyDecisionError(
                "invalid persisted policy-decision fields; "
                f"missing={sorted(missing)} unknown={sorted(unknown)}"
            )
        try:
            reason_codes = json.loads(record["reason_codes_json"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise PolicyDecisionError("persisted reason_codes_json is invalid") from exc
        if not isinstance(reason_codes, list):
            raise PolicyDecisionError("persisted reason_codes_json must be an array")

        reconstructed = cls.create(
            schema=record["schema"],
            decision_id=record["decision_id"],
            request_id=record["request_id"],
            decision=record["decision"],
            policy_revision=record["policy_revision"],
            reason_codes=reason_codes,
            evaluated_at=record["evaluated_at"],
            canonical_request_hash=record["canonical_request_hash"],
        )
        if reconstructed.reason_codes_json != record["reason_codes_json"]:
            raise PolicyDecisionError("persisted reason_codes_json is not canonical")
        return reconstructed

    @property
    def reason_codes_json(self) -> str:
        return canonical_json(list(self.reason_codes))

    def to_record(self) -> dict[str, str]:
        return {
            "schema": self.schema,
            "decision_id": self.decision_id,
            "request_id": self.request_id,
            "decision": self.decision.value,
            "policy_revision": self.policy_revision,
            "reason_codes_json": self.reason_codes_json,
            "evaluated_at": self.evaluated_at,
            "canonical_request_hash": self.canonical_request_hash,
        }
