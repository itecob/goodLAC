from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

from packages.state import SQLiteStateStore

from .native_contract import (
    NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA,
    normalize_continuation_status,
    normalize_native_result,
)
from .pi_continuation import (
    PI_V1_CONTINUATION_MAX_QUEUE_BYTES,
    PI_V1_CONTINUATION_MAX_RECORDS,
    PI_V1_CONTINUATION_TTL_SECONDS,
    PiWorkflowContinuationError,
    PiWorkflowContinuationIntegrityError,
    PiWorkflowContinuationStore,
)

NATIVE_CONTINUATION_TTL_SECONDS = PI_V1_CONTINUATION_TTL_SECONDS
NATIVE_CONTINUATION_MAX_RECORDS = PI_V1_CONTINUATION_MAX_RECORDS
NATIVE_CONTINUATION_MAX_QUEUE_BYTES = PI_V1_CONTINUATION_MAX_QUEUE_BYTES


@dataclass(frozen=True)
class NativeContinuationPreparation:
    state: str
    status: dict[str, Any]
    fresh_material: dict[str, Any] | None = None


class NativeWorkflowContinuationStore:
    """Consumer-neutral PI003 facade over the accepted D001 durable continuation state.

    The legacy D001 store remains the persistence implementation in v1 so PI003 does not
    migrate or reinterpret accepted durable state. This facade removes Pi-specific schemas
    from the public local-consumer contract and exposes no authority or administration method.
    """

    def __init__(
        self,
        store: SQLiteStateStore,
        *,
        clock: Callable[[], datetime] | None = None,
        ttl_seconds: int = NATIVE_CONTINUATION_TTL_SECONDS,
    ) -> None:
        self._delegate = PiWorkflowContinuationStore(
            store,
            clock=clock,
            ttl_seconds=ttl_seconds,
        )

    def capture(
        self,
        *,
        material: Mapping[str, Any],
        canonical_request_hash: str,
        pending_id: str,
    ) -> dict[str, Any]:
        return normalize_continuation_status(
            self._delegate.capture(
                material=material,
                canonical_request_hash=canonical_request_hash,
                pending_id=pending_id,
            )
        )

    def status(self, continuation_id: str) -> dict[str, Any]:
        return normalize_continuation_status(self._delegate.status(continuation_id))

    def list_status(self, *, recoverable_only: bool = False) -> list[dict[str, Any]]:
        return [
            normalize_continuation_status(item)
            for item in self._delegate.list_status(recoverable_only=recoverable_only)
        ]

    def assert_expected_intent(
        self, continuation_id: str, expected_material: Mapping[str, Any]
    ) -> None:
        self._delegate.assert_expected_intent(continuation_id, expected_material)

    def prepare_resume(self, continuation_id: str) -> NativeContinuationPreparation:
        prepared = self._delegate.prepare_resume(continuation_id)
        return NativeContinuationPreparation(
            state=prepared.state,
            status=normalize_continuation_status(prepared.status),
            fresh_material=prepared.fresh_material,
        )

    def record_fresh_result(
        self, continuation_id: str, response: Mapping[str, Any]
    ) -> dict[str, Any]:
        return normalize_continuation_status(
            self._delegate.record_fresh_result(continuation_id, response)
        )

    def workflow_outcome(self, continuation_id: str) -> dict[str, Any]:
        material = dict(self._delegate.workflow_outcome(continuation_id))
        material["schema"] = NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA
        material["workflow_continuation"] = normalize_continuation_status(
            material["workflow_continuation"]
        )
        return normalize_native_result(material)


__all__ = [
    "NATIVE_CONTINUATION_TTL_SECONDS",
    "NATIVE_CONTINUATION_MAX_RECORDS",
    "NATIVE_CONTINUATION_MAX_QUEUE_BYTES",
    "NativeContinuationPreparation",
    "NativeWorkflowContinuationStore",
    "PiWorkflowContinuationError",
    "PiWorkflowContinuationIntegrityError",
]
