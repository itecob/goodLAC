from __future__ import annotations

import sqlite3

from packages.core import PolicyDecision, PolicyDecisionError
from .store import SQLiteStateStore, StateStoreError


class PolicyDecisionBindingError(StateStoreError):
    """A policy decision does not bind an existing canonical effect request."""


class PolicyDecisionIdentityConflict(StateStoreError):
    """A decision_id already exists with different durable decision material."""


class PolicyDecisionRepository:
    """Durable persistence boundary for policy decisions."""

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    def _put_in_transaction(
        self, conn: sqlite3.Connection, decision: PolicyDecision
    ) -> PolicyDecision:
        if conn is not self._store._conn or not conn.in_transaction:
            raise StateStoreError("policy decision transaction helper requires the active StateStore transaction")
        if not isinstance(decision, PolicyDecision):
            raise StateStoreError("decision must be a canonical PolicyDecision")
        try:
            canonical = PolicyDecision.from_record(decision.to_record())
        except (PolicyDecisionError, TypeError, AttributeError) as exc:
            raise StateStoreError("policy decision failed canonical integrity validation") from exc
        if canonical != decision:
            raise StateStoreError("policy decision is not canonical")

        request_row = conn.execute(
            "SELECT canonical_hash FROM effect_requests WHERE request_id = ?",
            (decision.request_id,),
        ).fetchone()
        if request_row is None:
            raise PolicyDecisionBindingError(
                f"request_id {decision.request_id!r} is not durably persisted"
            )
        if request_row["canonical_hash"] != decision.canonical_request_hash:
            raise PolicyDecisionBindingError(
                "policy decision canonical_request_hash does not match the persisted effect request"
            )

        try:
            conn.execute(
                """
                INSERT INTO policy_decisions(
                    decision_id, schema, request_id, decision, policy_revision,
                    reason_codes_json, evaluated_at, canonical_request_hash
                ) VALUES (
                    :decision_id, :schema, :request_id, :decision, :policy_revision,
                    :reason_codes_json, :evaluated_at, :canonical_request_hash
                )
                """,
                decision.to_record(),
            )
        except sqlite3.IntegrityError as exc:
            existing = self.get(decision.decision_id)
            if existing is None:
                raise StateStoreError(
                    "policy decision persistence failed without a readable conflict row"
                ) from exc
            if existing != decision:
                raise PolicyDecisionIdentityConflict(
                    f"decision_id {decision.decision_id!r} already binds different material"
                ) from exc
            return existing
        return decision

    def put(self, decision: PolicyDecision) -> PolicyDecision:
        with self._store.transaction() as conn:
            return self._put_in_transaction(conn, decision)

    def get(self, decision_id: str) -> PolicyDecision | None:
        if not isinstance(decision_id, str) or not decision_id:
            raise StateStoreError("decision_id must be a non-empty string")
        row = self._store._conn.execute(
            """
            SELECT schema, decision_id, request_id, decision, policy_revision,
                   reason_codes_json, evaluated_at, canonical_request_hash
            FROM policy_decisions WHERE decision_id = ?
            """,
            (decision_id,),
        ).fetchone()
        if row is None:
            return None
        try:
            decision = PolicyDecision.from_record(dict(row))
        except PolicyDecisionError as exc:
            raise StateStoreError(
                f"persisted policy decision {decision_id!r} failed integrity validation"
            ) from exc

        request_row = self._store._conn.execute(
            "SELECT canonical_hash FROM effect_requests WHERE request_id = ?",
            (decision.request_id,),
        ).fetchone()
        if request_row is None or request_row["canonical_hash"] != decision.canonical_request_hash:
            raise PolicyDecisionBindingError(
                f"persisted policy decision {decision_id!r} lost canonical request binding"
            )
        return decision
