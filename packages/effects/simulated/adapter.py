from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any

from packages.core import (
    EffectRequest,
    EffectRequestError,
    ExecutionLease,
    ExecutionLeaseError,
    canonical_json,
)


SIMULATED_ADAPTER_ID = "simulated:v1"
SIMULATED_ACTION = "simulated.write"
SIMULATED_RESOURCE = "simulated:alpha"
SIMULATED_RESULT_SCHEMA = "lac.simulated-effect-result/v1"


class SimulatedEffectError(ValueError):
    """The simulated adapter request or lease did not satisfy its narrow contract."""


@dataclass(frozen=True)
class SimulatedEffectResult:
    """Deterministic non-external result used by Phase 1 effect/reconciliation tests."""

    schema: str
    adapter_id: str
    request_id: str
    canonical_request_hash: str
    lease_id: str
    lease_hash: str
    executor_id: str
    simulated_value: int
    result_hash: str

    def to_record(self) -> dict[str, str | int]:
        return {
            "schema": self.schema,
            "adapter_id": self.adapter_id,
            "request_id": self.request_id,
            "canonical_request_hash": self.canonical_request_hash,
            "lease_id": self.lease_id,
            "lease_hash": self.lease_hash,
            "executor_id": self.executor_id,
            "simulated_value": self.simulated_value,
            "result_hash": self.result_hash,
        }


def _canonical_request(request: EffectRequest) -> EffectRequest:
    if not isinstance(request, EffectRequest):
        raise SimulatedEffectError("request must be a canonical EffectRequest")
    try:
        canonical = EffectRequest.from_record(request.to_record())
    except (EffectRequestError, TypeError, AttributeError) as exc:
        raise SimulatedEffectError("request failed canonical integrity validation") from exc
    if canonical != request:
        raise SimulatedEffectError("request is not canonical")
    return canonical


def _canonical_lease(lease: ExecutionLease) -> ExecutionLease:
    if not isinstance(lease, ExecutionLease):
        raise SimulatedEffectError("lease must be a canonical ExecutionLease")
    try:
        canonical = ExecutionLease.from_record(lease.to_record())
    except (ExecutionLeaseError, TypeError, AttributeError) as exc:
        raise SimulatedEffectError("lease failed canonical integrity validation") from exc
    if canonical != lease:
        raise SimulatedEffectError("lease is not canonical")
    return canonical


def _supported_value(request: EffectRequest) -> int:
    canonical = _canonical_request(request)
    if canonical.action != SIMULATED_ACTION:
        raise SimulatedEffectError(f"unsupported simulated action: {canonical.action!r}")
    if canonical.resource != SIMULATED_RESOURCE:
        raise SimulatedEffectError(f"unsupported simulated resource: {canonical.resource!r}")
    arguments = canonical.arguments
    if set(arguments) != {"value"}:
        raise SimulatedEffectError("simulated arguments must contain exactly one 'value' field")
    value: Any = arguments["value"]
    if not isinstance(value, int) or isinstance(value, bool):
        raise SimulatedEffectError("simulated 'value' must be an integer")
    return value


def _deterministic_result(
    request: EffectRequest, *, lease: ExecutionLease
) -> SimulatedEffectResult:
    value = _supported_value(request)
    canonical_request = _canonical_request(request)
    canonical_lease = _canonical_lease(lease)
    if canonical_lease.request_id != canonical_request.request_id:
        raise SimulatedEffectError("execution lease binds a different request_id")

    lease_material = canonical_lease.to_record()
    lease_digest = hashlib.sha256(
        canonical_json(lease_material).encode("utf-8")
    ).hexdigest()
    lease_hash = f"sha256:{lease_digest}"

    result_material = {
        "schema": SIMULATED_RESULT_SCHEMA,
        "adapter_id": SIMULATED_ADAPTER_ID,
        "request_id": canonical_request.request_id,
        "canonical_request_hash": canonical_request.canonical_hash,
        "lease_id": canonical_lease.lease_id,
        "lease_hash": lease_hash,
        "executor_id": canonical_lease.executor_id,
        "simulated_value": value,
    }
    result_digest = hashlib.sha256(
        canonical_json(result_material).encode("utf-8")
    ).hexdigest()
    return SimulatedEffectResult(
        **result_material,
        result_hash=f"sha256:{result_digest}",
    )


class SimulatedEffectAdapter:
    """Narrow Phase 1 adapter; reconciliation never invokes a second simulated effect."""

    @property
    def adapter_id(self) -> str:
        return SIMULATED_ADAPTER_ID

    def supports(self, request: EffectRequest) -> bool:
        try:
            _supported_value(request)
        except SimulatedEffectError:
            return False
        return True

    def invoke(
        self,
        request: EffectRequest,
        *,
        lease: ExecutionLease,
    ) -> SimulatedEffectResult:
        return _deterministic_result(request, lease=lease)

    def reconcile(
        self,
        request: EffectRequest,
        *,
        lease: ExecutionLease,
    ) -> SimulatedEffectResult:
        """Safely derive the simulated outcome without calling invoke()."""
        return _deterministic_result(request, lease=lease)
