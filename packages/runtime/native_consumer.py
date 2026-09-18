from __future__ import annotations

from datetime import datetime
from typing import Any, Callable, Mapping

from packages.capabilities import PendingPermissionRepository
from packages.dispatcher import DispatchPaused
from packages.state import SQLiteStateStore

from .external_consumer import (
    ExternalConsumerRuntime,
    ExternalConsumerRuntimeError,
)
from .native_contract import (
    NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA,
    normalize_native_result,
    normalize_resume_result,
    validate_native_request,
)
from .workflow_continuation import (
    NATIVE_CONTINUATION_TTL_SECONDS,
    NativeWorkflowContinuationStore,
    PiWorkflowContinuationError,
)


class NativeLocalConsumerRuntimeError(RuntimeError):
    """Fail-closed host/runtime error at the stabilized native consumer boundary."""


class NativeLocalConsumerRuntime:
    """Consumer-neutral host facade over the accepted B003 authoritative runtime.

    This class owns no policy, approval, identity, lease, credential, adapter, or administrator
    authority. It adds the PI003 public result/status/resume contract and the accepted D001
    non-authoritative workflow-continuation behavior around an already controller-bound
    ExternalConsumerRuntime.
    """

    def __init__(
        self,
        *,
        store: SQLiteStateStore,
        authority_runtime: ExternalConsumerRuntime,
        clock: Callable[[], datetime] | None = None,
        continuation_ttl_seconds: int = NATIVE_CONTINUATION_TTL_SECONDS,
    ) -> None:
        if not isinstance(store, SQLiteStateStore):
            raise NativeLocalConsumerRuntimeError("store must be SQLiteStateStore")
        if not isinstance(authority_runtime, ExternalConsumerRuntime):
            raise NativeLocalConsumerRuntimeError(
                "authority_runtime must be ExternalConsumerRuntime"
            )
        self.store = store
        self.authority_runtime = authority_runtime
        self.continuations = NativeWorkflowContinuationStore(
            store,
            clock=clock,
            ttl_seconds=continuation_ttl_seconds,
        )

    @property
    def application_id(self) -> str:
        return self.authority_runtime.application_id

    @property
    def skill_id(self) -> str:
        return self.authority_runtime.skill_id

    def decorate(self, response: Mapping[str, Any]) -> dict[str, Any]:
        """Add non-authoritative permission-discovery metadata to an authority result."""

        if not isinstance(response, Mapping):
            raise NativeLocalConsumerRuntimeError("authority response must be an object")
        material = dict(response)
        request_id = material.get("request_id")
        closure = (
            PendingPermissionRepository(self.store).get_closure(request_id)
            if isinstance(request_id, str) and request_id
            else None
        )
        material["permission_configuration"] = (
            {
                "required": True,
                "pending_id": closure["pending_id"],
                "reason": closure["reason"],
            }
            if closure is not None
            else {"required": False}
        )
        material.setdefault("workflow_continuation", None)
        return normalize_native_result(material)

    def submit_authoritative(self, material: Mapping[str, Any]) -> dict[str, Any]:
        """Submit one exact request through the accepted authoritative B003 runtime."""

        request = validate_native_request(material)
        try:
            return self.decorate(self.authority_runtime.submit(request))
        except ExternalConsumerRuntimeError as exc:
            # Querying status here does not grant authority. It only distinguishes the accepted
            # durable FAILED receipt case and the controller's emergency-pause fail-closed path.
            status = self.authority_runtime.status(request["request_id"])
            if isinstance(exc.__cause__, DispatchPaused):
                if (
                    status.get("execution_state") != "NOT_EXECUTED"
                    or status.get("receipt") is not None
                ):
                    raise NativeLocalConsumerRuntimeError(
                        "emergency-paused request unexpectedly entered execution state"
                    ) from exc
                paused = dict(status)
                paused["authority_outcome"] = "DENY"
                paused["execution_state"] = "DENIED"
                paused["reason"] = "EMERGENCY_PAUSED"
                return self.decorate(paused)
            if status.get("execution_state") != "FAILED":
                raise
            return self.decorate(status)

    def submit(self, material: Mapping[str, Any]) -> dict[str, Any]:
        """Submit and, when required, capture non-authoritative continuation state."""

        request = validate_native_request(material)
        result = self.submit_authoritative(request)
        permission = result.get("permission_configuration")
        if isinstance(permission, Mapping) and permission.get("required") is True:
            pending_id = permission.get("pending_id")
            canonical_hash = result.get("canonical_request_hash")
            if not isinstance(pending_id, str) or not isinstance(canonical_hash, str):
                raise PiWorkflowContinuationError(
                    "permission-required denial lacks continuation binding material"
                )
            status = self.continuations.capture(
                material=request,
                canonical_request_hash=canonical_hash,
                pending_id=pending_id,
            )
            material_result = dict(result)
            material_result["workflow_continuation"] = status
            result = normalize_native_result(material_result)
        return result

    def status(self, request_id: str) -> dict[str, Any]:
        return self.decorate(self.authority_runtime.status(request_id))

    def continuation_status(self, continuation_id: str) -> dict[str, Any]:
        return self.continuations.status(continuation_id)

    def list_continuations(
        self, *, recoverable_only: bool = False
    ) -> list[dict[str, Any]]:
        return self.continuations.list_status(recoverable_only=recoverable_only)

    def resume(
        self,
        continuation_id: str,
        *,
        expected_material: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Explicitly process one continuation event; restart alone never calls this."""

        if expected_material is not None:
            expected = validate_native_request(expected_material)
            self.continuations.assert_expected_intent(continuation_id, expected)

        prepared = self.continuations.prepare_resume(continuation_id)
        if prepared.state == "WAITING_PERMISSION":
            return normalize_resume_result(
                {
                    "schema": NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA,
                    "ok": True,
                    "kind": "WAITING_PERMISSION",
                    "workflow_continuation": prepared.status,
                    "result": None,
                }
            )
        if prepared.state in {"CLOSED_NONAUTH", "EXPIRED"}:
            return normalize_resume_result(
                {
                    "schema": NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA,
                    "ok": True,
                    "kind": prepared.state,
                    "workflow_continuation": prepared.status,
                    "result": self.continuations.workflow_outcome(continuation_id),
                }
            )
        if prepared.state == "COMPLETED":
            fresh_request_id = prepared.status.get("fresh_request_id")
            if not isinstance(fresh_request_id, str) or not fresh_request_id:
                raise PiWorkflowContinuationError(
                    "completed continuation lost fresh request identity"
                )
            result = self.status(fresh_request_id)
            stored_outcome = prepared.status.get("outcome")
            if result.get("execution_state") == "NOT_EXECUTED" and stored_outcome in {
                "EMERGENCY_PAUSED",
                "POLICY_DENY",
                "CAPABILITY_DENY",
            }:
                replay = dict(result)
                replay["authority_outcome"] = "DENY"
                replay["execution_state"] = "DENIED"
                replay["reason"] = stored_outcome
                permission = replay.get("permission_configuration")
                if isinstance(permission, Mapping) and permission.get("required") is True:
                    replay["permission_configuration"] = {
                        "required": False,
                        "reason": "CONTINUATION_BUDGET_EXHAUSTED",
                    }
                result = normalize_native_result(replay)
            result_with_status = dict(result)
            result_with_status["workflow_continuation"] = prepared.status
            return normalize_resume_result(
                {
                    "schema": NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA,
                    "ok": True,
                    "kind": "COMPLETED",
                    "workflow_continuation": prepared.status,
                    "result": normalize_native_result(result_with_status),
                }
            )
        if prepared.fresh_material is None:
            raise PiWorkflowContinuationError(
                "resumable continuation did not provide fresh request material"
            )

        result = self.submit_authoritative(prepared.fresh_material)
        status = self.continuations.record_fresh_result(continuation_id, result)
        permission = result.get("permission_configuration")
        if isinstance(permission, Mapping) and permission.get("required") is True:
            exhausted = dict(result)
            exhausted["permission_configuration"] = {
                "required": False,
                "reason": "CONTINUATION_BUDGET_EXHAUSTED",
            }
            result = normalize_native_result(exhausted)
        result_with_status = dict(result)
        result_with_status["workflow_continuation"] = status
        result = normalize_native_result(result_with_status)
        return normalize_resume_result(
            {
                "schema": NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA,
                "ok": True,
                "kind": status["state"],
                "workflow_continuation": status,
                "result": result,
            }
        )


__all__ = ["NativeLocalConsumerRuntime", "NativeLocalConsumerRuntimeError"]
