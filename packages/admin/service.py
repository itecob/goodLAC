from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from typing import Any, Callable, Mapping

from packages.capabilities.manifest import CapabilityManifest, CapabilityManifestError
from packages.capabilities.quarantine import PendingPermissionRepository
from packages.capabilities.registry import CapabilityRegistry
from packages.core import Approval, ApprovalDecision, ApprovalScope, PolicyDecisionValue
from packages.policy.standing import (
    StandingPolicyConfigurationError,
    StandingPolicyDefault,
    StandingPolicyRepository,
    StandingPolicyRule,
)
from packages.state.approvals import ApprovalRepository
from packages.state.effect_requests import EffectRequestRepository
from packages.state.policy_decisions import PolicyDecisionRepository
from packages.state.emergency_pause import EmergencyPauseRepository, EmergencyPauseStateError
from packages.state.store import SQLiteStateStore, StateStoreError

from .owner_permissions import (
    OwnerPermissionDecisionConflict,
    OwnerPermissionDecisionError,
    OwnerPermissionDecisionService,
)
from .pending import PendingAdminError, PendingAdminRepository
from .protocol import AdminRequest


class AdminServiceError(StateStoreError):
    """Base fail-closed administrator service error."""

    code = "ADMIN_SERVICE_ERROR"


class AdminUnauthorized(AdminServiceError):
    code = "UNAUTHORIZED_PEER_UID"


class AdminBadRequest(AdminServiceError):
    code = "INVALID_ADMIN_ARGUMENTS"


class AdminNotFound(AdminServiceError):
    code = "ADMIN_OBJECT_NOT_FOUND"


class AdminConflict(AdminServiceError):
    code = "ADMIN_STATE_CONFLICT"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _exact_arguments(
    arguments: Mapping[str, Any], *, required: set[str], optional: set[str] | None = None
) -> dict[str, Any]:
    if not isinstance(arguments, Mapping):
        raise AdminBadRequest("arguments must be an object")
    value = dict(arguments)
    optional = set() if optional is None else optional
    observed = set(value)
    if not required.issubset(observed) or observed - (required | optional):
        raise AdminBadRequest(
            f"administrator arguments invalid; required={sorted(required)} optional={sorted(optional)}"
        )
    return value


def _required_text(value: Any, field: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise AdminBadRequest(f"{field} must be a bounded non-empty trimmed string")
    return value


def _registration_material(registration: Any) -> dict[str, Any]:
    return {
        "application_id": registration.application_id,
        "skill_id": registration.skill_id,
        "revision": registration.revision,
        "manifest_hash": registration.manifest_hash,
        "security_hash": registration.security_hash,
        "registered_at_utc": registration.registered_at_utc,
        "manifest": registration.manifest.canonical_material(),
    }


def _snapshot_material(snapshot: Any | None) -> dict[str, Any]:
    if snapshot is None:
        return {
            "revision": 0,
            "revision_id": "standing-policy:none",
            "policy_hash": None,
            "rules": [],
            "defaults": [],
        }
    return {
        "revision": snapshot.revision,
        "revision_id": snapshot.revision_id,
        "policy_hash": snapshot.policy_hash,
        "rules": [item.to_material() for item in snapshot.rules],
        "defaults": [item.to_material() for item in snapshot.defaults],
    }


def _request_material(request: Any) -> dict[str, Any]:
    record = request.to_record()
    return {
        "schema": record["schema"],
        "request_id": record["request_id"],
        "run_id": record["run_id"],
        "principal_id": record["principal_id"],
        "agent_id": record["agent_id"],
        "action": record["action"],
        "resource": record["resource"],
        "arguments": json.loads(record["arguments_json"]),
        "idempotency_key": record["idempotency_key"],
        "created_at": record["created_at"],
        "expires_at": record["expires_at"],
        "canonical_hash": record["canonical_hash"],
    }


def _decision_material(decision: Any) -> dict[str, Any]:
    record = decision.to_record()
    return {
        "schema": record["schema"],
        "decision_id": record["decision_id"],
        "request_id": record["request_id"],
        "decision": record["decision"],
        "policy_revision": record["policy_revision"],
        "reason_codes": json.loads(record["reason_codes_json"]),
        "evaluated_at": record["evaluated_at"],
        "canonical_request_hash": record["canonical_request_hash"],
    }


class AdminService:
    """Owner-authenticated administration facade over canonical LAC state.

    The caller UID is supplied only by the controller-side Unix peer-credential check.
    Runtime consumers never receive an object reference to this service.
    """

    def __init__(self, store: SQLiteStateStore, *, owner_uid: int | None = None):
        if not isinstance(store, SQLiteStateStore):
            raise AdminServiceError("store must be a SQLiteStateStore")
        if owner_uid is None:
            owner_uid = os.getuid()
        if isinstance(owner_uid, bool) or not isinstance(owner_uid, int) or owner_uid < 0:
            raise AdminServiceError("owner_uid must be a non-negative integer")
        self._store = store
        self.owner_uid = owner_uid
        self._registry = CapabilityRegistry(store)
        self._pending = PendingPermissionRepository(store)
        self._pending_admin = PendingAdminRepository(store)
        self._policy = StandingPolicyRepository(store)
        self._approvals = ApprovalRepository(store)
        self._policy_decisions = PolicyDecisionRepository(store)
        self._effect_requests = EffectRequestRepository(store)
        self._emergency = EmergencyPauseRepository(store)
        self._owner_permissions = OwnerPermissionDecisionService(
            store, owner_uid=self.owner_uid
        )

        self._operations: dict[str, Callable[[dict[str, Any]], Any]] = {
            "skills.list": self._skills_list,
            "skills.show": self._skills_show,
            "skills.register": self._skills_register,
            "permissions.list": self._permissions_list,
            "permissions.show": self._permissions_show,
            "permissions.replace": self._permissions_replace,
            "permissions.revoke": self._permissions_revoke,
            "permissions.decide": self._permissions_decide,
            "pending.list": self._pending_list,
            "pending.show": self._pending_show,
            "pending.resolve": self._pending_resolve,
            "pending.dismiss": self._pending_dismiss,
            "emergency.status": self._emergency_status,
            "emergency.pause": self._emergency_pause,
            "emergency.resume": self._emergency_resume,
            "approvals.list": self._approvals_list,
            "approvals.show": self._approvals_show,
            "approvals.approve": self._approvals_approve,
            "approvals.reject": self._approvals_reject,
        }

    def execute(self, request: AdminRequest, *, peer_uid: int) -> Any:
        # This check intentionally precedes operation lookup or argument parsing.
        if isinstance(peer_uid, bool) or not isinstance(peer_uid, int) or peer_uid != self.owner_uid:
            raise AdminUnauthorized("administrator peer UID does not match controller owner UID")
        if not isinstance(request, AdminRequest):
            raise AdminBadRequest("request must be a validated AdminRequest")
        operation = self._operations.get(request.operation)
        if operation is None:
            raise AdminBadRequest("unsupported administrator operation")
        return operation(dict(request.arguments))

    def _skills_list(self, arguments: dict[str, Any]) -> Any:
        _exact_arguments(arguments, required=set())
        return {"skills": [_registration_material(item) for item in self._registry.list_latest()]}

    def _skills_show(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required={"application_id", "skill_id"}, optional={"revision"})
        application_id = _required_text(args["application_id"], "application_id")
        skill_id = _required_text(args["skill_id"], "skill_id")
        if "revision" in args:
            revision = args["revision"]
            if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
                raise AdminBadRequest("revision must be a positive integer")
            registration = self._registry.get_revision(application_id, skill_id, revision)
        else:
            registration = self._registry.get_latest(application_id, skill_id)
        if registration is None:
            raise AdminNotFound("capability registration was not found")
        return _registration_material(registration)

    def _skills_register(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required={"manifest"})
        if not isinstance(args["manifest"], Mapping):
            raise AdminBadRequest("manifest must be an object")
        try:
            manifest = CapabilityManifest.create(dict(args["manifest"]))
        except CapabilityManifestError as exc:
            raise AdminBadRequest(str(exc)) from exc
        return _registration_material(self._registry.register_admin(manifest))

    def _permissions_list(self, arguments: dict[str, Any]) -> Any:
        _exact_arguments(arguments, required=set())
        current = self._policy.current()
        return _snapshot_material(current)

    def _permissions_show(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required=set(), optional={"revision"})
        history = self._policy.history()
        if "revision" not in args:
            return _snapshot_material(history[-1] if history else None)
        revision = args["revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise AdminBadRequest("revision must be a positive integer")
        if revision > len(history):
            raise AdminNotFound("standing-policy revision was not found")
        return _snapshot_material(history[revision - 1])

    def _permissions_replace(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required={"rules", "defaults"})
        if not isinstance(args["rules"], list) or not isinstance(args["defaults"], list):
            raise AdminBadRequest("rules/defaults must be arrays")
        try:
            rules = [StandingPolicyRule.from_material(item) for item in args["rules"]]
            defaults = [StandingPolicyDefault.from_material(item) for item in args["defaults"]]
            snapshot = self._policy.replace_admin(rules=rules, defaults=defaults)
        except (StandingPolicyConfigurationError, TypeError) as exc:
            raise AdminBadRequest(str(exc)) from exc
        return _snapshot_material(snapshot)

    def _permissions_revoke(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required={"kind", "id"})
        kind = _required_text(args["kind"], "kind", maximum=16).upper()
        identity = _required_text(args["id"], "id", maximum=256)
        current = self._policy.current()
        if current is None:
            raise AdminNotFound("no standing policy exists")
        rules = list(current.rules)
        defaults = list(current.defaults)
        if kind == "RULE":
            narrowed = [item for item in rules if item.rule_id != identity]
            if len(narrowed) == len(rules):
                raise AdminNotFound("standing-policy rule was not found")
            rules = narrowed
        elif kind == "DEFAULT":
            narrowed_defaults = [item for item in defaults if item.default_id != identity]
            if len(narrowed_defaults) == len(defaults):
                raise AdminNotFound("standing-policy default was not found")
            defaults = narrowed_defaults
        else:
            raise AdminBadRequest("kind must be RULE or DEFAULT")
        return _snapshot_material(self._policy.replace_admin(rules=rules, defaults=defaults))

    def _permissions_decide(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(
            arguments,
            required={"continuation_id", "pending_id", "choice", "scope"},
        )
        try:
            return self._owner_permissions.decide(
                continuation_id=_required_text(args["continuation_id"], "continuation_id"),
                pending_id=_required_text(args["pending_id"], "pending_id"),
                choice=_required_text(args["choice"], "choice", maximum=32),
                scope=_required_text(args["scope"], "scope", maximum=32),
            )
        except OwnerPermissionDecisionConflict as exc:
            raise AdminConflict(str(exc)) from exc
        except OwnerPermissionDecisionError as exc:
            raise AdminBadRequest(str(exc)) from exc

    def _pending_records(self) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for record in self._pending.list_pending():
            pending_id = str(record.get("pending_id", ""))
            resolution = self._pending_admin.current(pending_id)
            item = dict(record)
            item["administrative_status"] = "PENDING" if resolution is None else resolution.status
            item["administrative_resolution"] = None if resolution is None else resolution.to_material()
            result.append(item)
        return result

    def _find_pending(self, pending_id: str) -> dict[str, Any]:
        for record in self._pending_records():
            if record.get("pending_id") == pending_id:
                return record
        raise AdminNotFound("pending-permission item was not found")

    def _pending_list(self, arguments: dict[str, Any]) -> Any:
        _exact_arguments(arguments, required=set())
        return {"pending": self._pending_records()}

    def _pending_show(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required={"pending_id"})
        return self._find_pending(_required_text(args["pending_id"], "pending_id"))

    def _pending_resolve(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required={"pending_id", "resolution"})
        pending_id = _required_text(args["pending_id"], "pending_id")
        self._find_pending(pending_id)
        resolution = _required_text(args["resolution"], "resolution", maximum=64).upper()
        try:
            record = self._pending_admin.record(
                pending_id=pending_id,
                status="RESOLVED",
                resolution=resolution,
                resolved_by=f"uid:{self.owner_uid}",
                resolved_at_utc=_utc_now(),
            )
        except PendingAdminError as exc:
            raise AdminBadRequest(str(exc)) from exc
        return {"pending_id": pending_id, "resolution": record.to_material()}

    def _pending_dismiss(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required={"pending_id"})
        pending_id = _required_text(args["pending_id"], "pending_id")
        self._find_pending(pending_id)
        record = self._pending_admin.record(
            pending_id=pending_id,
            status="DISMISSED",
            resolution="DISMISSED",
            resolved_by=f"uid:{self.owner_uid}",
            resolved_at_utc=_utc_now(),
        )
        return {"pending_id": pending_id, "resolution": record.to_material()}

    def _emergency_status(self, arguments: dict[str, Any]) -> Any:
        _exact_arguments(arguments, required=set())
        try:
            return self._emergency.get().to_record()
        except EmergencyPauseStateError as exc:
            raise AdminConflict(str(exc)) from exc

    def _emergency_pause(self, arguments: dict[str, Any]) -> Any:
        _exact_arguments(arguments, required=set())
        try:
            return self._emergency.pause().to_record()
        except EmergencyPauseStateError as exc:
            raise AdminConflict(str(exc)) from exc

    def _emergency_resume(self, arguments: dict[str, Any]) -> Any:
        _exact_arguments(arguments, required=set())
        try:
            return self._emergency.resume().to_record()
        except EmergencyPauseStateError as exc:
            raise AdminConflict(str(exc)) from exc

    @staticmethod
    def _admin_approval_id(decision_id: str) -> str:
        digest = hashlib.sha256(decision_id.encode("utf-8")).hexdigest()
        return f"approval:admin:{digest}"

    def _approval_ids_for_decision(self, decision_id: str) -> list[str]:
        rows = self._store._conn.execute(
            "SELECT approval_id FROM approvals WHERE policy_decision_id = ? ORDER BY approval_id",
            (decision_id,),
        ).fetchall()
        return [str(row["approval_id"]) for row in rows]

    def _approval_view(self, decision_id: str) -> dict[str, Any]:
        decision = self._policy_decisions.get(decision_id)
        if decision is None or decision.decision is not PolicyDecisionValue.REQUIRE_APPROVAL:
            raise AdminNotFound("REQUIRE_APPROVAL policy decision was not found")
        request = self._effect_requests.get(decision.request_id)
        if request is None:
            raise AdminConflict("approval candidate lost durable effect request")
        approval_ids = self._approval_ids_for_decision(decision_id)
        if len(approval_ids) > 1:
            raise AdminConflict("multiple approvals bind one policy decision; fail closed")
        approval = None if not approval_ids else self._approvals.get(approval_ids[0])
        execution = self._store._conn.execute(
            "SELECT state FROM effect_executions WHERE request_id = ?",
            (request.request_id,),
        ).fetchone()
        return {
            "decision": _decision_material(decision),
            "request": _request_material(request),
            "approval": None if approval is None else approval.to_record(),
            "execution_state": None if execution is None else str(execution["state"]),
        }

    def _approvals_list(self, arguments: dict[str, Any]) -> Any:
        _exact_arguments(arguments, required=set())
        rows = self._store._conn.execute(
            "SELECT decision_id FROM policy_decisions WHERE decision = 'REQUIRE_APPROVAL' ORDER BY evaluated_at, decision_id"
        ).fetchall()
        return {"approvals": [self._approval_view(str(row["decision_id"])) for row in rows]}

    def _approvals_show(self, arguments: dict[str, Any]) -> Any:
        args = _exact_arguments(arguments, required={"decision_id"})
        return self._approval_view(_required_text(args["decision_id"], "decision_id"))

    def _decide_approval(self, arguments: dict[str, Any], *, decision_value: ApprovalDecision) -> Any:
        args = _exact_arguments(arguments, required={"decision_id"})
        decision_id = _required_text(args["decision_id"], "decision_id")
        view = self._approval_view(decision_id)
        existing = view["approval"]
        if existing is not None:
            if existing["decision"] == decision_value.value:
                return view
            raise AdminConflict("approval candidate already has the opposite immutable decision")
        if view["execution_state"] is not None:
            raise AdminConflict("request already entered execution state")
        decision = self._policy_decisions.get(decision_id)
        if decision is None:
            raise AdminNotFound("policy decision was not found")
        request = self._effect_requests.get(decision.request_id)
        if request is None:
            raise AdminConflict("approval candidate lost durable request")
        now = _utc_now()
        if now >= request.expires_at:
            raise AdminConflict("effect request has expired; no new exact approval may be created")
        approval = Approval.create(
            approval_id=self._admin_approval_id(decision_id),
            request_id=request.request_id,
            policy_decision_id=decision_id,
            canonical_request_hash=request.canonical_hash,
            approver=f"uid:{self.owner_uid}",
            decision=decision_value,
            scope=ApprovalScope.ONCE,
            created_at=now,
            expires_at=request.expires_at,
        )
        self._approvals.put(approval)
        return self._approval_view(decision_id)

    def _approvals_approve(self, arguments: dict[str, Any]) -> Any:
        return self._decide_approval(arguments, decision_value=ApprovalDecision.APPROVE)

    def _approvals_reject(self, arguments: dict[str, Any]) -> Any:
        return self._decide_approval(arguments, decision_value=ApprovalDecision.REJECT)
