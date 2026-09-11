from __future__ import annotations

from packages.core import (
    Approval,
    ApprovalDecision,
    ApprovalError,
    ApprovalScope,
    EffectRequest,
    EffectRequestError,
    PolicyDecisionValue,
)
from .approvals import ApprovalRepository
from .effect_requests import EffectRequestRepository
from .policy_decisions import PolicyDecisionRepository
from .store import SQLiteStateStore, StateStoreError


class ApprovalValidationError(StateStoreError):
    """The supplied approval does not currently qualify the exact canonical request."""


class ApprovalBindingValidator:
    """Read-only exact post-approval binding validation; never consumes or dispatches."""

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    def validate(
        self,
        *,
        approval_id: str,
        current_request: EffectRequest,
        at: str,
    ) -> Approval:
        if not isinstance(approval_id, str) or not approval_id:
            raise ApprovalValidationError("approval_id must be a non-empty string")
        if not isinstance(current_request, EffectRequest):
            raise ApprovalValidationError("current_request must be a canonical EffectRequest")

        # Do not trust a dataclass instance solely because its type matches. Rebuild it
        # from its persisted representation so a manually forged hash or non-canonical
        # field representation fails closed before any approval can qualify it.
        try:
            canonical_current = EffectRequest.from_record(current_request.to_record())
        except (EffectRequestError, TypeError, AttributeError) as exc:
            raise ApprovalValidationError(
                "current_request failed canonical integrity validation"
            ) from exc
        if canonical_current != current_request:
            raise ApprovalValidationError("current_request is not canonical")

        try:
            approval = ApprovalRepository(self._store).get(approval_id)
        except StateStoreError as exc:
            raise ApprovalValidationError(
                "durable approval or its supporting binding failed integrity validation"
            ) from exc
        if approval is None:
            raise ApprovalValidationError(f"approval_id {approval_id!r} is not durable")

        if approval.request_id != current_request.request_id:
            raise ApprovalValidationError(
                "approval request_id does not match the current request"
            )
        if approval.canonical_request_hash != current_request.canonical_hash:
            raise ApprovalValidationError(
                "approval canonical request hash does not match the current request"
            )
        if approval.decision is not ApprovalDecision.APPROVE:
            raise ApprovalValidationError("approval decision is not APPROVE")
        if approval.scope is not ApprovalScope.ONCE:
            raise ApprovalValidationError("approval scope is not ONCE")
        if approval.consumed_at is not None:
            raise ApprovalValidationError("approval has already been consumed")
        try:
            if approval.is_expired(at):
                raise ApprovalValidationError("approval is expired")
        except ApprovalError as exc:
            raise ApprovalValidationError("validation time is invalid") from exc

        try:
            durable_request = EffectRequestRepository(self._store).get(
                current_request.request_id
            )
        except StateStoreError as exc:
            raise ApprovalValidationError(
                "durable current request failed integrity validation"
            ) from exc
        if durable_request is None:
            raise ApprovalValidationError("current request is not durably persisted")
        if durable_request != current_request:
            raise ApprovalValidationError(
                "current request differs from the durable canonical effect request"
            )

        try:
            policy_decision = PolicyDecisionRepository(self._store).get(
                approval.policy_decision_id
            )
        except StateStoreError as exc:
            raise ApprovalValidationError(
                "qualifying policy decision failed integrity validation"
            ) from exc
        if policy_decision is None:
            raise ApprovalValidationError("qualifying policy decision is not durable")
        if policy_decision.decision is not PolicyDecisionValue.REQUIRE_APPROVAL:
            raise ApprovalValidationError(
                "qualifying policy decision is no longer REQUIRE_APPROVAL"
            )
        if policy_decision.request_id != current_request.request_id:
            raise ApprovalValidationError(
                "qualifying policy decision binds a different request_id"
            )
        if policy_decision.canonical_request_hash != current_request.canonical_hash:
            raise ApprovalValidationError(
                "qualifying policy decision binds a different canonical request hash"
            )
        if approval.created_at < policy_decision.evaluated_at:
            raise ApprovalValidationError(
                "approval predates its qualifying policy decision"
            )

        return approval
