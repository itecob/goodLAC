import sqlite3
import tempfile
import unittest
from pathlib import Path

import packages.state.store as state_store_module
from packages.core import (
    EXECUTION_LEASE_SCHEMA,
    MAX_EXECUTION_LEASE_SECONDS,
    Approval,
    EffectRequest,
    ExecutionLease,
    ExecutionLeaseError,
    PolicyDecision,
    UnsupportedExecutionLeaseSchema,
)
from packages.state import (
    ApprovalRepository,
    EffectRequestRepository,
    ExecutionLeaseAcquisitionError,
    ExecutionLeaseBindingError,
    ExecutionLeaseIdentityConflict,
    ExecutionLeaseRepository,
    ExecutionLeaseStateError,
    ExecutionLeaseUnavailable,
    PolicyDecisionRepository,
    SCHEMA_VERSION,
    SQLiteStateStore,
)


REQUEST_VALUES = {
    "request_id": "effect:lease-001",
    "run_id": "run:lease-001",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": "simulated.write",
    "resource": "simulated:alpha",
    "arguments": {"value": 1},
    "idempotency_key": "idem:lease-001",
    "created_at": "2026-09-11T20:00:00Z",
    "expires_at": "2026-09-11T20:10:00Z",
}


def make_request(**overrides):
    return EffectRequest.create(**{**REQUEST_VALUES, **overrides})


def make_lease(**overrides):
    values = {
        "lease_id": "lease:001",
        "request_id": "effect:lease-001",
        "executor_id": "executor:one",
        "issued_at": "2026-09-11T20:00:10Z",
        "expires_at": "2026-09-11T20:00:40Z",
    }
    values.update(overrides)
    return ExecutionLease.create(**values)


def make_policy_decision(request):
    return PolicyDecision.create(
        decision_id="decision:lease-001",
        request_id=request.request_id,
        decision="REQUIRE_APPROVAL",
        policy_revision="policy:test:v1",
        reason_codes=("DECISION:REQUIRE_APPROVAL",),
        evaluated_at="2026-09-11T20:00:01Z",
        canonical_request_hash=request.canonical_hash,
    )


def make_approval(request, policy_decision):
    return Approval.create(
        approval_id="approval:lease-001",
        request_id=request.request_id,
        policy_decision_id=policy_decision.decision_id,
        canonical_request_hash=request.canonical_hash,
        approver="principal:owner",
        decision="APPROVE",
        scope="ONCE",
        created_at="2026-09-11T20:00:02Z",
        expires_at="2026-09-11T20:05:00Z",
    )


class ExecutionLeaseTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def persist_request(self, store, request=None):
        request = request or make_request()
        EffectRequestRepository(store).put(request)
        return request

    def test_schema_identity_timestamps_and_short_lived_bound_are_strict(self) -> None:
        lease = make_lease(
            issued_at="2026-09-11T16:00:10-04:00",
            expires_at="2026-09-11T16:00:40-04:00",
        )
        self.assertEqual(lease.schema, EXECUTION_LEASE_SCHEMA)
        self.assertEqual(lease.issued_at, "2026-09-11T20:00:10.000000Z")
        self.assertEqual(lease.expires_at, "2026-09-11T20:00:40.000000Z")
        self.assertEqual(MAX_EXECUTION_LEASE_SECONDS, 300)
        with self.assertRaises(UnsupportedExecutionLeaseSchema):
            make_lease(schema="lac.execution-lease/v999")
        with self.assertRaises(ExecutionLeaseError):
            make_lease(executor_id="")
        with self.assertRaises(ExecutionLeaseError):
            make_lease(expires_at="2026-09-11T20:00:10Z")
        with self.assertRaises(ExecutionLeaseError):
            make_lease(expires_at="2026-09-11T20:05:11Z")

    def test_expiry_boundary_is_deterministic(self) -> None:
        lease = make_lease()
        self.assertFalse(lease.is_expired("2026-09-11T20:00:39.999999Z"))
        self.assertTrue(lease.is_expired("2026-09-11T20:00:40Z"))
        with self.assertRaises(ExecutionLeaseError):
            lease.is_expired("not-a-timestamp")

    def test_durable_request_acquires_one_lease_and_survives_restart(self) -> None:
        lease = make_lease()
        with SQLiteStateStore(self.db) as store:
            self.persist_request(store)
            acquired = ExecutionLeaseRepository(store).acquire(lease)
            self.assertEqual(acquired, lease)
        with SQLiteStateStore(self.db) as reopened:
            self.assertEqual(ExecutionLeaseRepository(reopened).get(lease.lease_id), lease)

    def test_competing_unexpired_executor_is_rejected(self) -> None:
        first = make_lease()
        second = make_lease(
            lease_id="lease:002",
            executor_id="executor:two",
            issued_at="2026-09-11T20:00:20Z",
            expires_at="2026-09-11T20:00:50Z",
        )
        with SQLiteStateStore(self.db) as store:
            self.persist_request(store)
            repo = ExecutionLeaseRepository(store)
            repo.acquire(first)
            with self.assertRaises(ExecutionLeaseUnavailable):
                repo.acquire(second)
            self.assertIsNone(repo.get(second.lease_id))

    def test_exact_expiry_permits_new_bounded_lease(self) -> None:
        first = make_lease()
        second = make_lease(
            lease_id="lease:002",
            executor_id="executor:two",
            issued_at=first.expires_at,
            expires_at="2026-09-11T20:01:10Z",
        )
        with SQLiteStateStore(self.db) as store:
            self.persist_request(store)
            repo = ExecutionLeaseRepository(store)
            repo.acquire(first)
            self.assertEqual(repo.acquire(second), second)
            count = store._conn.execute(
                "SELECT COUNT(*) FROM execution_leases WHERE request_id = ?",
                (first.request_id,),
            ).fetchone()[0]
            self.assertEqual(count, 2)

    def test_identity_retry_is_idempotent_but_material_change_conflicts(self) -> None:
        lease = make_lease()
        with SQLiteStateStore(self.db) as store:
            self.persist_request(store)
            repo = ExecutionLeaseRepository(store)
            self.assertEqual(repo.acquire(lease), lease)
            self.assertEqual(repo.acquire(make_lease()), lease)
            with self.assertRaises(ExecutionLeaseIdentityConflict):
                repo.acquire(make_lease(executor_id="executor:other"))

    def test_unknown_or_corrupted_request_fails_closed(self) -> None:
        with SQLiteStateStore(self.db) as store:
            repo = ExecutionLeaseRepository(store)
            with self.assertRaises(ExecutionLeaseBindingError):
                repo.acquire(make_lease())

            request = self.persist_request(store)
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE effect_requests SET canonical_hash = ? WHERE request_id = ?",
                    ("sha256:" + ("0" * 64), request.request_id),
                )
            with self.assertRaises(ExecutionLeaseBindingError):
                repo.acquire(make_lease())

    def test_malformed_persisted_lease_state_fails_closed(self) -> None:
        lease = make_lease()
        later = make_lease(
            lease_id="lease:002",
            executor_id="executor:two",
            issued_at="2026-09-11T20:00:40Z",
            expires_at="2026-09-11T20:01:00Z",
        )
        with SQLiteStateStore(self.db) as store:
            self.persist_request(store)
            repo = ExecutionLeaseRepository(store)
            repo.acquire(lease)
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE execution_leases SET schema = ? WHERE lease_id = ?",
                    ("lac.execution-lease/v999", lease.lease_id),
                )
            with self.assertRaises(ExecutionLeaseStateError):
                repo.get(lease.lease_id)
            with self.assertRaises(ExecutionLeaseStateError):
                repo.acquire(later)

    def test_overlapping_persisted_lease_state_fails_closed(self) -> None:
        first = make_lease()
        overlapping = make_lease(
            lease_id="lease:overlap",
            executor_id="executor:other",
            issued_at="2026-09-11T20:00:20Z",
            expires_at="2026-09-11T20:00:50Z",
        )
        with SQLiteStateStore(self.db) as store:
            self.persist_request(store)
            repo = ExecutionLeaseRepository(store)
            repo.acquire(first)
            with store.transaction() as conn:
                conn.execute(
                    """
                    INSERT INTO execution_leases(
                        lease_id, schema, request_id, executor_id, issued_at, expires_at
                    ) VALUES (
                        :lease_id, :schema, :request_id, :executor_id, :issued_at, :expires_at
                    )
                    """,
                    overlapping.to_record(),
                )
            with self.assertRaises(ExecutionLeaseStateError):
                repo.get(first.lease_id)
            with self.assertRaises(ExecutionLeaseStateError):
                repo.acquire(make_lease())

    def test_noncanonical_lease_object_fails_closed(self) -> None:
        with SQLiteStateStore(self.db) as store:
            self.persist_request(store)
            with self.assertRaises(ExecutionLeaseAcquisitionError):
                ExecutionLeaseRepository(store).acquire(object())

    def test_two_connections_observe_single_current_owner(self) -> None:
        first = make_lease()
        second = make_lease(
            lease_id="lease:002",
            executor_id="executor:two",
            issued_at="2026-09-11T20:00:11Z",
            expires_at="2026-09-11T20:00:41Z",
        )
        with SQLiteStateStore(self.db) as creator:
            self.persist_request(creator)
        with SQLiteStateStore(self.db) as one, SQLiteStateStore(self.db) as two:
            ExecutionLeaseRepository(one).acquire(first)
            with self.assertRaises(ExecutionLeaseUnavailable):
                ExecutionLeaseRepository(two).acquire(second)

    def test_schema_v4_database_migrates_to_v5_without_losing_c005_state(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
        approval = make_approval(request, policy_decision)
        conn = sqlite3.connect(self.db)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """
            CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY NOT NULL,
                name TEXT UNIQUE NOT NULL,
                checksum_sha256 TEXT NOT NULL CHECK(length(checksum_sha256) = 64)
            )
            """
        )
        for migration in state_store_module._MIGRATIONS[:4]:
            for statement in migration.statements:
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations(version, name, checksum_sha256) VALUES (?, ?, ?)",
                (migration.version, migration.name, migration.checksum),
            )
            conn.execute(f"PRAGMA user_version={migration.version}")
        conn.execute(
            """
            INSERT INTO effect_requests(
                request_id, schema, run_id, principal_id, agent_id, action,
                resource, arguments_json, idempotency_key, created_at, expires_at,
                canonical_hash
            ) VALUES (
                :request_id, :schema, :run_id, :principal_id, :agent_id, :action,
                :resource, :arguments_json, :idempotency_key, :created_at, :expires_at,
                :canonical_hash
            )
            """,
            request.to_record(),
        )
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
            policy_decision.to_record(),
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
            approval.to_record(),
        )
        conn.commit()
        conn.close()

        with SQLiteStateStore(self.db) as migrated:
            self.assertEqual(SCHEMA_VERSION, 5)
            self.assertEqual(migrated.schema_version, 5)
            self.assertEqual(EffectRequestRepository(migrated).get(request.request_id), request)
            self.assertEqual(
                PolicyDecisionRepository(migrated).get(policy_decision.decision_id),
                policy_decision,
            )
            self.assertEqual(ApprovalRepository(migrated).get(approval.approval_id), approval)
            table = migrated._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='execution_leases'"
            ).fetchone()
            self.assertIsNotNone(table)

    def test_acquisition_is_not_authorization_dispatch_or_execution(self) -> None:
        with SQLiteStateStore(self.db) as store:
            self.persist_request(store)
            repo = ExecutionLeaseRepository(store)
            before_decisions = store._conn.execute("SELECT COUNT(*) FROM policy_decisions").fetchone()[0]
            before_approvals = store._conn.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]
            repo.acquire(make_lease())
            self.assertEqual(
                store._conn.execute("SELECT COUNT(*) FROM policy_decisions").fetchone()[0],
                before_decisions,
            )
            self.assertEqual(
                store._conn.execute("SELECT COUNT(*) FROM approvals").fetchone()[0],
                before_approvals,
            )
        public = {name for name in dir(ExecutionLeaseRepository) if not name.startswith("_")}
        self.assertEqual(public, {"acquire", "get"})
        self.assertFalse({"authorize", "dispatch", "execute"} & public)


if __name__ == "__main__":
    unittest.main()
