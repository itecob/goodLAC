from __future__ import annotations

import sqlite3

from packages.core import Approval, ApprovalError, PolicyDecisionValue
from .effect_requests import EffectRequestRepository
from .policy_decisions import PolicyDecisionRepository
from .store import SQLiteStateStore, StateStoreError


class ApprovalBindingError(StateStoreError):
    """An approval does not bind a durable request and REQUIRE_APPROVAL decision."""


class ApprovalIdentityConflict(StateStoreError):
    """An approval_id already exists with different immutable approval material."""


class _ApprovalConsumptionError(StateStoreError):
    """Internal atomic approval-consumption failure used by the dispatcher."""


class ApprovalRepository:
    """Durable persistence boundary for approval decisions; never dispatches effects."""

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    def put(self, approval: Approval) -> Approval:
        if not isinstance(approval, Approval):
            raise StateStoreError("approval must be a canonical Approval")
        record = approval.to_record()
        try:
            with self._store.transaction() as conn:
                request = EffectRequestRepository(self._store).get(approval.request_id)
                if request is None:
                    raise ApprovalBindingError(
                        f"request_id {approval.request_id!r} is not durably persisted"
                    )
                if request.canonical_hash != approval.canonical_request_hash:
                    raise ApprovalBindingError(
                        "approval canonical_request_hash does not match the persisted effect request"
                    )

                policy_decision = PolicyDecisionRepository(self._store).get(
                    approval.policy_decision_id
                )
                if policy_decision is None:
                    raise ApprovalBindingError(
                        f"policy_decision_id {approval.policy_decision_id!r} is not durably persisted"
                    )
                if policy_decision.decision is not PolicyDecisionValue.REQUIRE_APPROVAL:
                    raise ApprovalBindingError(
                        "approval requires a durable REQUIRE_APPROVAL policy decision"
                    )
                if policy_decision.request_id != approval.request_id:
                    raise ApprovalBindingError(
                        "approval policy decision binds a different request_id"
                    )
                if policy_decision.canonical_request_hash != approval.canonical_request_hash:
                    raise ApprovalBindingError(
                        "approval policy decision binds a different canonical request hash"
                    )
                if approval.created_at < policy_decision.evaluated_at:
                    raise ApprovalBindingError(
                        "approval created_at cannot precede the supporting policy decision"
                    )

                conn.execute(
                    """
                    INSERT INTO approvals(
                        approval_id, schema, request_id, policy_decision_id,
                        canonical_request_hash, approver, decision, scope,
                        created_at, expires_at, consumed_at
                    ) VALUES (
                        :approval_id, :schema, :request_id, :policy_decision_id,
                        :canonical_request_hash, :approver, :decision, :scope,
                        :created_at, :expires_at, :consumed_at
                    )
                    """,
                    record,
                )
        except sqlite3.IntegrityError as exc:
            existing = self.get(approval.approval_id)
            if existing is None:
                raise StateStoreError(
                    "approval persistence failed without a readable conflict row"
                ) from exc
            if existing != approval:
                raise ApprovalIdentityConflict(
                    f"approval_id {approval.approval_id!r} already binds different material"
                ) from exc
            return existing
        return approval

    def _consume_once_in_transaction(
        self,
        conn: sqlite3.Connection,
        approval: Approval,
        *,
        consumed_at: str,
    ) -> Approval:
        if conn is not self._store._conn or not conn.in_transaction:
            raise _ApprovalConsumptionError(
                "approval consumption requires the active StateStore transaction"
            )
        if not isinstance(approval, Approval):
            raise _ApprovalConsumptionError("approval must be a canonical Approval")
        if approval.consumed_at is not None:
            raise _ApprovalConsumptionError("approval has already been consumed")
        try:
            consumed = Approval.create(
                schema=approval.schema,
                approval_id=approval.approval_id,
                request_id=approval.request_id,
                policy_decision_id=approval.policy_decision_id,
                canonical_request_hash=approval.canonical_request_hash,
                approver=approval.approver,
                decision=approval.decision,
                scope=approval.scope,
                created_at=approval.created_at,
                expires_at=approval.expires_at,
                consumed_at=consumed_at,
            )
        except ApprovalError as exc:
            raise _ApprovalConsumptionError(
                "approval cannot be consumed at the requested dispatch time"
            ) from exc

        cursor = conn.execute(
            """
            UPDATE approvals
            SET consumed_at = ?
            WHERE approval_id = ? AND consumed_at IS NULL
            """,
            (consumed.consumed_at, approval.approval_id),
        )
        if cursor.rowcount != 1:
            raise _ApprovalConsumptionError(
                "approval was not atomically available for one-time consumption"
            )
        loaded = self.get(approval.approval_id)
        if loaded != consumed:
            raise _ApprovalConsumptionError(
                "durable approval consumption did not match the canonical transition"
            )
        return consumed

    def get(self, approval_id: str) -> Approval | None:
        if not isinstance(approval_id, str) or not approval_id:
            raise StateStoreError("approval_id must be a non-empty string")
        row = self._store._conn.execute(
            """
            SELECT schema, approval_id, request_id, policy_decision_id,
                   canonical_request_hash, approver, decision, scope,
                   created_at, expires_at, consumed_at
            FROM approvals WHERE approval_id = ?
            """,
            (approval_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            approval = Approval.from_record(dict(row))
        except ApprovalError as exc:
            raise StateStoreError(
                f"persisted approval {approval_id!r} failed integrity validation"
            ) from exc

        request = EffectRequestRepository(self._store).get(approval.request_id)
        if request is None or request.canonical_hash != approval.canonical_request_hash:
            raise ApprovalBindingError(
                f"persisted approval {approval_id!r} lost canonical request binding"
            )
        policy_decision = PolicyDecisionRepository(self._store).get(
            approval.policy_decision_id
        )
        if policy_decision is None:
            raise ApprovalBindingError(
                f"persisted approval {approval_id!r} lost policy-decision binding"
            )
        if (
            policy_decision.decision is not PolicyDecisionValue.REQUIRE_APPROVAL
            or policy_decision.request_id != approval.request_id
            or policy_decision.canonical_request_hash != approval.canonical_request_hash
            or approval.created_at < policy_decision.evaluated_at
        ):
            raise ApprovalBindingError(
                f"persisted approval {approval_id!r} no longer has a qualifying policy decision"
            )
        return approval
