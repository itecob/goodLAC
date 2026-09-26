from __future__ import annotations

import os
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Mapping

from packages.admin import AdminRequest, AdminService
from packages.adapters.pi.production import canonical_project_root, pi_v1_project_application_id
from packages.capabilities import PendingPermissionRepository
from packages.state import SQLiteStateStore


OWNER_GATE_SCHEMA = "lac.pi-tui-owner-gate/v1"
OWNER_GATE_TTL_SECONDS = 300
_PERMISSION_CHOICES = frozenset(
    {"ALLOW_ONCE", "ALWAYS_ALLOW", "ASK_EVERY_TIME", "DENY_ONCE", "ALWAYS_DENY"}
)


class PiTuiOwnerGateError(RuntimeError):
    """A trusted Pi owner gate could not be completed safely."""


class PiTuiOwnerGateConflict(PiTuiOwnerGateError):
    """The opaque owner challenge no longer binds current controller state."""


def _required_text(value: Any, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise PiTuiOwnerGateError(f"{field} must be bounded non-empty trimmed text")
    return value


class PiTuiOwnerGate:
    """Host-side owner-input bridge for the trusted pinned Pi extension.

    The extension receives only opaque one-use challenges plus trusted display material.
    Canonical permission/policy/approval truth remains in AdminService/controller state.
    No administrator socket is exposed to the governed Pi sandbox.
    """

    def __init__(
        self,
        *,
        state: Path,
        workspace: Path,
        session_id: str,
        owner_uid: int | None = None,
        continuation_status: Callable[[str], Mapping[str, Any]],
        continuation_resume: Callable[[str, Mapping[str, Any] | None], Mapping[str, Any]],
        retry_effect: Callable[[Mapping[str, Any]], Mapping[str, Any]],
        trace_result: Callable[[Mapping[str, Any], Mapping[str, Any]], None],
        ttl_seconds: int = OWNER_GATE_TTL_SECONDS,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self.workspace = canonical_project_root(workspace)
        self.application_id = pi_v1_project_application_id(self.workspace)
        self.session_id = _required_text(session_id, "session_id")
        if owner_uid is None:
            owner_uid = os.getuid()
        if isinstance(owner_uid, bool) or not isinstance(owner_uid, int) or owner_uid < 0:
            raise PiTuiOwnerGateError("owner_uid must be a non-negative integer")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int) or ttl_seconds < 1 or ttl_seconds > 3600:
            raise PiTuiOwnerGateError("owner gate ttl must be between 1 and 3600 seconds")
        for name, callback in (
            ("continuation_status", continuation_status),
            ("continuation_resume", continuation_resume),
            ("retry_effect", retry_effect),
            ("trace_result", trace_result),
        ):
            if not callable(callback):
                raise PiTuiOwnerGateError(f"{name} callback is required")
        self._clock = clock
        self._ttl_seconds = ttl_seconds
        self._continuation_status = continuation_status
        self._continuation_resume = continuation_resume
        self._retry_effect = retry_effect
        self._trace_result = trace_result
        self._store = SQLiteStateStore(Path(state).expanduser().resolve())
        self._admin = AdminService(self._store, owner_uid=owner_uid)
        self._pending = PendingPermissionRepository(self._store)
        self._permission_challenges: dict[str, dict[str, Any]] = {}
        self._approval_challenges: dict[str, dict[str, Any]] = {}

    def close(self) -> None:
        self._permission_challenges.clear()
        self._approval_challenges.clear()
        self._store.close()

    def _admin_call(self, operation: str, arguments: Mapping[str, Any]) -> Any:
        return self._admin.execute(
            AdminRequest.create(
                request_id=f"admin:pi-tui:{uuid.uuid4().hex}",
                operation=operation,
                arguments=dict(arguments),
            ),
            peer_uid=self._admin.owner_uid,
        )

    def _pending_record(self, pending_id: str) -> dict[str, Any]:
        pending_id = _required_text(pending_id, "pending_id")
        matches = [
            dict(item)
            for item in self._pending.list_pending()
            if item.get("pending_id") == pending_id
        ]
        if len(matches) != 1:
            raise PiTuiOwnerGateConflict("pending permission item is unavailable or non-unique")
        record = matches[0]
        if record.get("reason") != "NO_CONFIGURED_STANDING_PERMISSION":
            raise PiTuiOwnerGateConflict("pending item is not an ordinary standing-permission decision")
        if record.get("application_id") != self.application_id:
            raise PiTuiOwnerGateConflict("pending permission belongs to a different governed project")
        return record

    def _status(self, continuation_id: str) -> dict[str, Any]:
        response = self._continuation_status(_required_text(continuation_id, "continuation_id"))
        if not isinstance(response, Mapping) or response.get("ok") is not True:
            raise PiTuiOwnerGateConflict("continuation status failed closed")
        status = response.get("continuation")
        if not isinstance(status, Mapping):
            raise PiTuiOwnerGateConflict("continuation status is malformed")
        return dict(status)

    def _project_display(self) -> dict[str, str]:
        return {
            "path": str(self.workspace),
            "application_id": self.application_id,
        }

    def _new_challenge(
        self,
        table: dict[str, dict[str, Any]],
        *,
        kind: str,
        record: Mapping[str, Any],
    ) -> dict[str, Any]:
        challenge_id = f"pi-owner:{kind.lower()}:{uuid.uuid4().hex}"
        deadline = self._clock() + self._ttl_seconds
        stored = dict(record)
        stored.update(
            {
                "challenge_id": challenge_id,
                "kind": kind,
                "session_id": self.session_id,
                "project_application_id": self.application_id,
                "deadline": deadline,
            }
        )
        table[challenge_id] = stored
        return stored

    def _consume(
        self,
        table: dict[str, dict[str, Any]],
        challenge_id: str,
        *,
        permit_expired_non_authorizing: bool = False,
    ) -> dict[str, Any]:
        challenge_id = _required_text(challenge_id, "challenge_id", maximum=256)
        record = table.pop(challenge_id, None)
        if record is None:
            raise PiTuiOwnerGateConflict("owner challenge is unavailable, stale, restarted, or already consumed")
        if record.get("session_id") != self.session_id:
            raise PiTuiOwnerGateConflict("owner challenge session binding failed")
        if record.get("project_application_id") != self.application_id:
            raise PiTuiOwnerGateConflict("owner challenge project binding failed")
        expired = self._clock() >= float(record["deadline"])
        if expired and not permit_expired_non_authorizing:
            raise PiTuiOwnerGateConflict("owner challenge expired")
        return record

    def _permission_subject(
        self,
        continuation_id: str,
        *,
        expected_pending_id: str | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        status = self._status(continuation_id)
        if status.get("state") != "WAITING_PERMISSION":
            raise PiTuiOwnerGateConflict("continuation is no longer waiting for owner permission")
        pending_id = status.get("pending_id")
        if not isinstance(pending_id, str) or not pending_id:
            raise PiTuiOwnerGateConflict("continuation lost pending permission identity")
        if expected_pending_id is not None and pending_id != expected_pending_id:
            raise PiTuiOwnerGateConflict("pending identity no longer binds continuation")
        pending = self._pending_record(pending_id)
        return status, pending

    def permission_challenge(
        self,
        continuation_id: str,
        *,
        pending_id: str | None = None,
        expected_message: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        status, pending = self._permission_subject(
            continuation_id,
            expected_pending_id=pending_id,
        )
        if expected_message is not None and not isinstance(expected_message, Mapping):
            raise PiTuiOwnerGateError("captured expected message must be an object")
        challenge = self._new_challenge(
            self._permission_challenges,
            kind="PERMISSION_DECISION",
            record={
                "continuation_id": status["continuation_id"],
                "pending_id": status["pending_id"],
                "original_request_id": status.get("original_request_id"),
                "continuation_run_id": status.get("run_id"),
                "expected_message": None if expected_message is None else dict(expected_message),
                "action": pending.get("action"),
                "resource": pending.get("resource"),
            },
        )
        return {
            "ok": True,
            "owner_gate": {
                "schema": OWNER_GATE_SCHEMA,
                "kind": "PERMISSION_DECISION",
                "challenge_id": challenge["challenge_id"],
                "timeout_ms": self._ttl_seconds * 1000,
                "project": self._project_display(),
                "action": pending.get("action"),
                "resource": pending.get("resource"),
            },
        }

    def _synthetic_denial(
        self,
        record: Mapping[str, Any],
        *,
        reason: str,
        status: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        continuation = dict(status) if isinstance(status, Mapping) else None
        result = {
            "authority_outcome": "DENY",
            "execution_state": "DENIED",
            "reason": reason,
            "request_id": record.get("original_request_id"),
            "receipt": None,
            "workflow_continuation": continuation,
        }
        expected = record.get("expected_message")
        if isinstance(expected, Mapping):
            self._trace_result(expected, result)
        return {"ok": True, "result": result}

    def permission_cancel(self, challenge_id: str) -> dict[str, Any]:
        record = self._consume(
            self._permission_challenges,
            challenge_id,
            permit_expired_non_authorizing=True,
        )
        status, _pending = self._permission_subject(
            record["continuation_id"],
            expected_pending_id=record["pending_id"],
        )
        decision = self._admin_call(
            "permissions.decide",
            {
                "continuation_id": record["continuation_id"],
                "pending_id": record["pending_id"],
                "choice": "DENY_ONCE",
                "scope": "RESOURCE",
            },
        )
        closed = decision.get("continuation") if isinstance(decision, Mapping) else None
        return self._synthetic_denial(
            record,
            reason="OWNER_GATE_CANCELLED",
            status=closed if isinstance(closed, Mapping) else status,
        )

    @staticmethod
    def _is_exact_approval(result: Mapping[str, Any]) -> bool:
        return (
            result.get("authority_outcome") == "REQUIRE_APPROVAL"
            and result.get("execution_state") == "PENDING_APPROVAL"
            and isinstance(result.get("decision_id"), str)
            and bool(result.get("decision_id"))
        )

    def _approval_view(self, result: Mapping[str, Any]) -> dict[str, Any]:
        if not self._is_exact_approval(result):
            raise PiTuiOwnerGateConflict("effect is not waiting for exact owner approval")
        view = self._admin_call("approvals.show", {"decision_id": result["decision_id"]})
        if not isinstance(view, Mapping):
            raise PiTuiOwnerGateConflict("approval candidate is malformed")
        request = view.get("request")
        decision = view.get("decision")
        if not isinstance(request, Mapping) or not isinstance(decision, Mapping):
            raise PiTuiOwnerGateConflict("approval candidate lost exact request binding")
        if (
            request.get("request_id") != result.get("request_id")
            or decision.get("decision_id") != result.get("decision_id")
            or decision.get("request_id") != result.get("request_id")
        ):
            raise PiTuiOwnerGateConflict("approval candidate no longer binds the exact request")
        return dict(view)

    def _approval_challenge(
        self,
        *,
        result: Mapping[str, Any],
        origin: str,
        payload: Mapping[str, Any] | None = None,
        continuation_id: str | None = None,
        pending_id: str | None = None,
    ) -> dict[str, Any]:
        view = self._approval_view(result)
        request = view["request"]
        if origin == "continuation":
            if continuation_id is None or pending_id is None:
                raise PiTuiOwnerGateError("continuation approval challenge lacks exact workflow binding")
            self._pending_record(pending_id)
        challenge = self._new_challenge(
            self._approval_challenges,
            kind="EXACT_APPROVAL",
            record={
                "origin": origin,
                "decision_id": result["decision_id"],
                "request_id": result["request_id"],
                "canonical_request_hash": request.get("canonical_hash"),
                "payload": None if origin != "effect" or payload is None else dict(payload),
                "expected_message": None if origin != "continuation" or payload is None else dict(payload),
                "continuation_id": continuation_id,
                "pending_id": pending_id,
                "action": request.get("action"),
                "resource": request.get("resource"),
            },
        )
        return {
            "ok": True,
            "owner_gate": {
                "schema": OWNER_GATE_SCHEMA,
                "kind": "EXACT_APPROVAL",
                "challenge_id": challenge["challenge_id"],
                "timeout_ms": self._ttl_seconds * 1000,
                "project": self._project_display(),
                "action": request.get("action"),
                "resource": request.get("resource"),
            },
        }

    def exact_approval_for_effect(
        self,
        result: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise PiTuiOwnerGateError("captured effect payload must be an object")
        return self._approval_challenge(
            result=result,
            origin="effect",
            payload=payload,
        )

    def _resume_result(self, record: Mapping[str, Any]) -> dict[str, Any]:
        response = self._continuation_resume(
            record["continuation_id"],
            record.get("expected_message"),
        )
        if not isinstance(response, Mapping) or response.get("ok") is not True:
            raise PiTuiOwnerGateConflict("continuation resume failed closed")
        resume = response.get("resume")
        if not isinstance(resume, Mapping):
            raise PiTuiOwnerGateConflict("continuation resume response is malformed")
        if resume.get("kind") == "WAITING_PERMISSION":
            raise PiTuiOwnerGateConflict("continuation remains blocked after owner decision")
        result = resume.get("result")
        if isinstance(result, Mapping):
            return dict(result)
        status = resume.get("workflow_continuation")
        if resume.get("kind") in {"CLOSED_NONAUTH", "EXPIRED"}:
            return {
                "authority_outcome": "DENY",
                "execution_state": "DENIED",
                "reason": str(resume.get("kind")),
                "request_id": record.get("original_request_id"),
                "receipt": None,
                "workflow_continuation": dict(status) if isinstance(status, Mapping) else None,
            }
        raise PiTuiOwnerGateConflict("resolved continuation lacks explicit effect result")

    def _trace_and_return(
        self,
        record: Mapping[str, Any],
        result: Mapping[str, Any],
    ) -> dict[str, Any]:
        expected = record.get("expected_message")
        payload = record.get("payload")
        source = expected if isinstance(expected, Mapping) else payload
        if isinstance(source, Mapping):
            self._trace_result(source, result)
        return {"ok": True, "result": dict(result)}

    def permission_decide(self, challenge_id: str, choice: str) -> dict[str, Any]:
        choice = _required_text(choice, "choice", maximum=32).upper()
        if choice not in _PERMISSION_CHOICES:
            raise PiTuiOwnerGateError("unsupported owner permission choice")
        record = self._consume(self._permission_challenges, challenge_id)
        self._permission_subject(
            record["continuation_id"],
            expected_pending_id=record["pending_id"],
        )
        decision = self._admin_call(
            "permissions.decide",
            {
                "continuation_id": record["continuation_id"],
                "pending_id": record["pending_id"],
                "choice": choice,
                "scope": "RESOURCE",
            },
        )
        if choice == "DENY_ONCE":
            closed = decision.get("continuation") if isinstance(decision, Mapping) else None
            return self._synthetic_denial(
                record,
                reason="OWNER_DENY_ONCE",
                status=closed if isinstance(closed, Mapping) else None,
            )

        result = self._resume_result(record)
        if choice == "ALLOW_ONCE" and self._is_exact_approval(result):
            # Exact approval creation is canonical admin state only. Dispatch still requires
            # a separate continuation resume, which performs normal pre-dispatch re-evaluation.
            self._approval_view(result)
            self._admin_call("approvals.approve", {"decision_id": result["decision_id"]})
            result = self._resume_result(record)
            return self._trace_and_return(record, result)

        if choice == "ASK_EVERY_TIME" and self._is_exact_approval(result):
            return self._approval_challenge(
                result=result,
                origin="continuation",
                continuation_id=record["continuation_id"],
                pending_id=record["pending_id"],
                payload=record.get("expected_message"),
            )

        return self._trace_and_return(record, result)

    def continuation_approval_challenge(self, continuation_id: str) -> dict[str, Any]:
        status = self._status(continuation_id)
        pending_id = status.get("pending_id")
        if not isinstance(pending_id, str) or not pending_id:
            raise PiTuiOwnerGateConflict("continuation lacks pending project binding")
        self._pending_record(pending_id)
        record = {
            "continuation_id": continuation_id,
            "pending_id": pending_id,
            "original_request_id": status.get("original_request_id"),
            "expected_message": None,
        }
        result = self._resume_result(record)
        if not self._is_exact_approval(result):
            return self._trace_and_return(record, result)
        return self._approval_challenge(
            result=result,
            origin="continuation",
            continuation_id=continuation_id,
            pending_id=pending_id,
        )

    def approval_decide(self, challenge_id: str, approve: bool) -> dict[str, Any]:
        if not isinstance(approve, bool):
            raise PiTuiOwnerGateError("approval choice must be boolean")
        record = self._consume(
            self._approval_challenges,
            challenge_id,
            permit_expired_non_authorizing=not approve,
        )
        view = self._admin_call("approvals.show", {"decision_id": record["decision_id"]})
        if not isinstance(view, Mapping):
            raise PiTuiOwnerGateConflict("approval candidate is malformed")
        request = view.get("request")
        decision = view.get("decision")
        if (
            not isinstance(request, Mapping)
            or not isinstance(decision, Mapping)
            or request.get("request_id") != record["request_id"]
            or request.get("canonical_hash") != record["canonical_request_hash"]
            or decision.get("decision_id") != record["decision_id"]
        ):
            raise PiTuiOwnerGateConflict("exact approval challenge became stale")
        self._admin_call(
            "approvals.approve" if approve else "approvals.reject",
            {"decision_id": record["decision_id"]},
        )

        if record["origin"] == "continuation":
            self._pending_record(record["pending_id"])
            result = self._resume_result(record)
        elif record["origin"] == "effect":
            payload = record.get("payload")
            if not isinstance(payload, Mapping):
                raise PiTuiOwnerGateConflict("exact effect approval lost captured request")
            response = self._retry_effect(payload)
            if not isinstance(response, Mapping) or response.get("ok") is not True:
                raise PiTuiOwnerGateConflict("exact approved effect retry failed closed")
            result = response.get("result")
            if not isinstance(result, Mapping):
                raise PiTuiOwnerGateConflict("exact approved effect retry result is malformed")
            result = dict(result)
        else:
            raise PiTuiOwnerGateConflict("unknown exact approval challenge origin")

        return self._trace_and_return(record, result)
