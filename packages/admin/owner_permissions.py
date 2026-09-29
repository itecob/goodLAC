from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any, Mapping

from packages.capabilities.quarantine import PendingPermissionRepository
from packages.core import canonical_json
from packages.policy.standing import (
    StandingPolicyCondition,
    StandingPolicyRepository,
    StandingPolicyRule,
)
from packages.runtime.pi_continuation import (
    PiWorkflowContinuationError,
    PiWorkflowContinuationStore,
    fresh_request_identity,
)
from packages.state.effect_requests import EffectRequestRepository
from packages.state.store import SQLiteStateStore, StateStoreError


OWNER_PERMISSION_DECISION_SCHEMA = "lac.owner-permission-decision/v1"
OWNER_PERMISSION_CHOICES = frozenset(
    {"ALLOW_ONCE", "ALWAYS_ALLOW", "ASK_EVERY_TIME", "DENY_ONCE", "ALWAYS_DENY"}
)
OWNER_PERMISSION_SCOPES = frozenset({"RESOURCE"})


class OwnerPermissionDecisionError(StateStoreError):
    """A bounded owner permission decision is invalid or cannot be applied safely."""


class OwnerPermissionDecisionConflict(OwnerPermissionDecisionError):
    """The owner decision no longer binds the current blocked workflow state."""


def _required_text(value: Any, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise OwnerPermissionDecisionError(f"{field} must be bounded non-empty trimmed text")
    return value


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _scope_material(record: Mapping[str, Any]) -> dict[str, str]:
    fields = (
        "principal_id",
        "application_id",
        "agent_id",
        "skill_id",
        "action",
        "resource_type",
        "resource",
    )
    result: dict[str, str] = {}
    for field in fields:
        result[field] = _required_text(record.get(field), f"pending.{field}")
    return result


def _rule_id(scope: Mapping[str, str]) -> str:
    digest = hashlib.sha256(canonical_json(dict(scope)).encode("utf-8")).hexdigest()
    return f"owner-permission:resource:{digest}"


class OwnerPermissionDecisionService:
    """Controller-owned orchestration for ordinary first-use permission choices.

    This service is only reachable through the owner-authenticated administration surface.
    It does not dispatch effects. It changes standing policy when the selected choice requires
    it, records a fresh owner administrative disposition for the pending permission item, or
    closes exactly one workflow continuation non-authoritatively for DENY_ONCE.
    """

    def __init__(self, store: SQLiteStateStore, *, owner_uid: int):
        if not isinstance(store, SQLiteStateStore):
            raise OwnerPermissionDecisionError("store must be SQLiteStateStore")
        if isinstance(owner_uid, bool) or not isinstance(owner_uid, int) or owner_uid < 0:
            raise OwnerPermissionDecisionError("owner_uid must be a non-negative integer")
        self._store = store
        self._owner_uid = owner_uid
        self._pending = PendingPermissionRepository(store)
        self._policy = StandingPolicyRepository(store)
        self._requests = EffectRequestRepository(store)
        self._continuations = PiWorkflowContinuationStore(store)
        # Local import avoids making the non-authoritative continuation store depend on admin.
        from packages.admin.pending import PendingAdminRepository

        self._pending_admin = PendingAdminRepository(store)

    def _pending_record(self, pending_id: str) -> dict[str, Any]:
        pending_id = _required_text(pending_id, "pending_id")
        matches = [
            item for item in self._pending.list_pending() if item.get("pending_id") == pending_id
        ]
        if len(matches) != 1:
            raise OwnerPermissionDecisionConflict(
                "pending permission item is unavailable or non-unique"
            )
        record = dict(matches[0])
        if record.get("reason") != "NO_CONFIGURED_STANDING_PERMISSION":
            raise OwnerPermissionDecisionError(
                "owner permission choices apply only to known capabilities lacking standing permission"
            )
        return record

    def _subject(self, continuation_id: str, pending_id: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, str]]:
        try:
            binding = self._continuations.owner_decision_binding(continuation_id)
        except PiWorkflowContinuationError as exc:
            raise OwnerPermissionDecisionConflict(str(exc)) from exc
        if binding["state"] != "WAITING_PERMISSION":
            raise OwnerPermissionDecisionConflict(
                "workflow continuation is no longer waiting for owner permission configuration"
            )
        if binding["pending_id"] != pending_id:
            raise OwnerPermissionDecisionConflict(
                "owner decision pending identity does not bind the workflow continuation"
            )
        pending = self._pending_record(pending_id)
        request = self._requests.get(binding["original_request_id"])
        if request is None:
            raise OwnerPermissionDecisionConflict(
                "blocked workflow lost its durable original request"
            )
        if (
            request.action != binding["action"]
            or request.resource != binding["resource"]
            or request.action != pending.get("action")
            or request.resource != pending.get("resource")
            or request.principal_id != pending.get("principal_id")
            or request.agent_id != pending.get("agent_id")
        ):
            raise OwnerPermissionDecisionConflict(
                "pending permission metadata does not bind the blocked canonical request"
            )
        scope = _scope_material(pending)
        current_resolution = self._pending_admin.current(pending_id)
        current_revision = 0 if current_resolution is None else current_resolution.revision
        if current_revision != binding["resolution_baseline_revision"]:
            raise OwnerPermissionDecisionConflict(
                "a newer owner disposition exists; stale permission choice rejected"
            )
        return binding, pending, scope

    def decide(
        self,
        *,
        continuation_id: str,
        pending_id: str,
        choice: str,
        scope: str,
    ) -> dict[str, Any]:
        continuation_id = _required_text(continuation_id, "continuation_id")
        pending_id = _required_text(pending_id, "pending_id")
        choice = _required_text(choice, "choice", maximum=32).upper()
        scope = _required_text(scope, "scope", maximum=32).upper()
        if choice not in OWNER_PERMISSION_CHOICES:
            raise OwnerPermissionDecisionError("unsupported owner permission choice")
        if scope not in OWNER_PERMISSION_SCOPES:
            raise OwnerPermissionDecisionError(
                "R1 supports only the exact trusted resource scope"
            )

        binding, _pending, scope_values = self._subject(continuation_id, pending_id)
        if choice == "DENY_ONCE":
            try:
                closed = self._continuations.owner_deny_once(
                    continuation_id,
                    expected_pending_id=pending_id,
                    expected_resolution_baseline_revision=binding[
                        "resolution_baseline_revision"
                    ],
                )
            except PiWorkflowContinuationError as exc:
                raise OwnerPermissionDecisionConflict(str(exc)) from exc
            return {
                "schema": OWNER_PERMISSION_DECISION_SCHEMA,
                "choice": choice,
                "scope": scope,
                "subject": dict(scope_values),
                "policy": None,
                "pending_resolution": None,
                "continuation": closed,
                "next_action": "COMPLETE_NONAUTHORIZING_DENIAL",
            }

        transient_exact_request = choice == "ALLOW_ONCE"
        if transient_exact_request:
            fresh_request_id, _fresh_idempotency_key = fresh_request_identity(continuation_id)
            transient_material = {
                "scope": scope_values,
                "continuation_id": continuation_id,
                "fresh_request_id": fresh_request_id,
            }
            transient_digest = hashlib.sha256(
                canonical_json(transient_material).encode("utf-8")
            ).hexdigest()
            rule_id = f"owner-permission:allow-once:{transient_digest}"
            policy_value = "REQUIRE_APPROVAL"
            conditions = (
                StandingPolicyCondition.create(
                    source="REQUEST", key="request_id", equals=fresh_request_id
                ),
            )
        else:
            policy_value = {
                "ALWAYS_ALLOW": "ALLOW",
                "ASK_EVERY_TIME": "REQUIRE_APPROVAL",
                "ALWAYS_DENY": "DENY",
            }[choice]
            rule_id = _rule_id(scope_values)
            conditions = ()
        rule = StandingPolicyRule.create(
            rule_id=rule_id,
            principal_id=scope_values["principal_id"],
            application_id=scope_values["application_id"],
            agent_id=scope_values["agent_id"],
            skill_id=scope_values["skill_id"],
            action=scope_values["action"],
            resource_type=scope_values["resource_type"],
            resource_selector=scope_values["resource"],
            decision=policy_value,
            conditions=conditions,
        )
        current = self._policy.current()
        rules = [] if current is None else [item for item in current.rules if item.rule_id != rule_id]
        defaults = [] if current is None else list(current.defaults)
        snapshot = self._policy.replace_admin(rules=rules + [rule], defaults=defaults)

        # A fresh revision is required even if an older equivalent POLICY_UPDATED disposition
        # exists. New continuations capture the latest revision as their baseline; deduplicating
        # the owner's new event would strand them in WAITING_PERMISSION.
        resolution = self._pending_admin.record(
            pending_id=pending_id,
            status="RESOLVED",
            resolution="POLICY_UPDATED",
            resolved_by=f"uid:{self._owner_uid}",
            resolved_at_utc=_utc_now(),
            force_new_revision=True,
        )
        if resolution.revision <= binding["resolution_baseline_revision"]:
            raise OwnerPermissionDecisionConflict(
                "owner permission disposition did not advance beyond continuation baseline"
            )

        next_action = {
            "ALLOW_ONCE": "RESUME_THEN_APPROVE_EXACT",
            "ALWAYS_ALLOW": "RESUME",
            "ASK_EVERY_TIME": "RESUME_THEN_REQUEST_EXACT_OWNER_DECISION",
            "ALWAYS_DENY": "RESUME_EXPECT_DENY",
        }[choice]
        return {
            "schema": OWNER_PERMISSION_DECISION_SCHEMA,
            "choice": choice,
            "scope": scope,
            "subject": dict(scope_values),
            "policy": {
                "revision": snapshot.revision,
                "revision_id": snapshot.revision_id,
                "policy_hash": snapshot.policy_hash,
                "rule_id": rule.rule_id,
                "decision": rule.decision.value,
                "transient_exact_request": transient_exact_request,
            },
            "pending_resolution": resolution.to_material(),
            "continuation": self._continuations.status(continuation_id),
            "next_action": next_action,
        }
