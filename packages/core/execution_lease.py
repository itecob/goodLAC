from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping


EXECUTION_LEASE_SCHEMA = "lac.execution-lease/v1"
MAX_EXECUTION_LEASE_SECONDS = 300


class ExecutionLeaseError(ValueError):
    """Base error for invalid or non-canonical execution leases."""


class UnsupportedExecutionLeaseSchema(ExecutionLeaseError):
    """Raised when an execution-lease schema is not supported."""


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ExecutionLeaseError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise ExecutionLeaseError(f"{field} must not have leading/trailing whitespace")
    return value


def _normalize_timestamp(value: Any, field: str) -> tuple[str, datetime]:
    if not isinstance(value, str) or not value:
        raise ExecutionLeaseError(f"{field} must be a non-empty RFC3339 timestamp")
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise ExecutionLeaseError(f"{field} must be a valid RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ExecutionLeaseError(f"{field} must include a timezone")
    normalized_dt = parsed.astimezone(timezone.utc)
    normalized = (
        normalized_dt.isoformat(timespec="microseconds").replace("+00:00", "Z")
    )
    return normalized, normalized_dt


@dataclass(frozen=True)
class ExecutionLease:
    schema: str
    lease_id: str
    request_id: str
    executor_id: str
    issued_at: str
    expires_at: str

    @classmethod
    def create(
        cls,
        *,
        lease_id: str,
        request_id: str,
        executor_id: str,
        issued_at: str,
        expires_at: str,
        schema: str = EXECUTION_LEASE_SCHEMA,
    ) -> "ExecutionLease":
        if schema != EXECUTION_LEASE_SCHEMA:
            raise UnsupportedExecutionLeaseSchema(
                f"unsupported execution-lease schema: {schema!r}"
            )
        normalized_issued, issued_dt = _normalize_timestamp(issued_at, "issued_at")
        normalized_expires, expires_dt = _normalize_timestamp(expires_at, "expires_at")
        if expires_dt <= issued_dt:
            raise ExecutionLeaseError("expires_at must be later than issued_at")
        duration_seconds = (expires_dt - issued_dt).total_seconds()
        if duration_seconds > MAX_EXECUTION_LEASE_SECONDS:
            raise ExecutionLeaseError(
                f"execution lease duration must not exceed {MAX_EXECUTION_LEASE_SECONDS} seconds"
            )
        return cls(
            schema=schema,
            lease_id=_required_text(lease_id, "lease_id"),
            request_id=_required_text(request_id, "request_id"),
            executor_id=_required_text(executor_id, "executor_id"),
            issued_at=normalized_issued,
            expires_at=normalized_expires,
        )

    @classmethod
    def from_record(cls, record: Mapping[str, Any]) -> "ExecutionLease":
        required = {
            "schema",
            "lease_id",
            "request_id",
            "executor_id",
            "issued_at",
            "expires_at",
        }
        observed = set(record)
        missing = required - observed
        unknown = observed - required
        if missing or unknown:
            raise ExecutionLeaseError(
                "invalid persisted execution-lease fields; "
                f"missing={sorted(missing)} unknown={sorted(unknown)}"
            )
        return cls.create(
            schema=record["schema"],
            lease_id=record["lease_id"],
            request_id=record["request_id"],
            executor_id=record["executor_id"],
            issued_at=record["issued_at"],
            expires_at=record["expires_at"],
        )

    def is_expired(self, at: str) -> bool:
        """Deterministically test expiry; the exact expiry instant is expired."""
        normalized_at, _ = _normalize_timestamp(at, "at")
        return normalized_at >= self.expires_at

    def to_record(self) -> dict[str, str]:
        return {
            "schema": self.schema,
            "lease_id": self.lease_id,
            "request_id": self.request_id,
            "executor_id": self.executor_id,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
        }
