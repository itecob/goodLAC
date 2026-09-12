import sqlite3
import tempfile
import unittest
from pathlib import Path

import packages.state.store as state_store_module
from packages.core import (
    APPROVAL_SCHEMA,
    Approval,
    ApprovalDecision,
    ApprovalError,
    ApprovalScope,
    EffectRequest,
    PolicyDecision,
    UnsupportedApprovalSchema,
)
from packages.state import (
    ApprovalBindingError,
    ApprovalIdentityConflict,
    ApprovalRepository,
    EffectRequestRepository,
    PolicyDecisionRepository,
    SCHEMA_VERSION,
    SQLiteStateStore,
    StateStoreError,
)


REQUEST_VALUES = {
    "request_id": "effect:approval-001",
    "run_id": "run:approval-001",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": "simulated.write",
    "resource": "simulated:alpha",
    "arguments": {"value": 7},
    "idempotency_key": "idem:approval-001",
    "created_at": "2026-09-11T12:00:00Z",
    "expires_at": "2026-09-11T12:10:00Z",
}


def make_request(**overrides):
    return EffectRequest.create(**{**REQUEST_VALUES, **overrides})


def make_policy_decision(request=None, *, decision="REQUIRE_APPROVAL", decision_id="decision:approval-001", evaluated_at="2026-09-11T12:00:01Z"):
    request = request or make_request()
    return PolicyDecision.create(
        decision_id=decision_id,
        request_id=request.request_id,
        decision=decision,
        policy_revision="policy:test:v1",
        reason_codes=(f"DECISION:{decision}", "MATCHED_RULE:approval"),
        evaluated_at=evaluated_at,
        canonical_request_hash=request.canonical_hash,
    )


def make_approval(request=None, policy_decision=None, **overrides):
    request = request or make_request()
    policy_decision = policy_decision or make_policy_decision(request)
    values = {
        "approval_id": "approval:001",
        "request_id": request.request_id,
        "policy_decision_id": policy_decision.decision_id,
        "canonical_request_hash": request.canonical_hash,
        "approver": "principal:owner",
        "decision": "APPROVE",
        "scope": "ONCE",
        "created_at": "2026-09-11T12:00:02Z",
        "expires_at": "2026-09-11T12:05:00Z",
        "consumed_at": None,
    }
    values.update(overrides)
    return Approval.create(**values)


def persist_foundation(store, request, policy_decision):
    EffectRequestRepository(store).put(request)
    PolicyDecisionRepository(store).put(policy_decision)


class ApprovalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_schema_decision_and_scope_are_strictly_versioned(self) -> None:
        approval = make_approval()
        self.assertEqual(approval.schema, APPROVAL_SCHEMA)
        self.assertIs(approval.decision, ApprovalDecision.APPROVE)
        self.assertIs(approval.scope, ApprovalScope.ONCE)
        with self.assertRaises(UnsupportedApprovalSchema):
            make_approval(schema="lac.approval/v999")
        with self.assertRaises(ApprovalError):
            make_approval(decision="MAYBE")
        with self.assertRaises(ApprovalError):
            make_approval(scope="FOREVER")

    def test_approval_binds_request_hash_policy_decision_and_approver(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
        approval = make_approval(request, policy_decision)
        self.assertEqual(approval.request_id, request.request_id)
        self.assertEqual(approval.canonical_request_hash, request.canonical_hash)
        self.assertEqual(approval.policy_decision_id, policy_decision.decision_id)
        self.assertEqual(approval.approver, "principal:owner")

    def test_expiry_is_normalized_and_boundary_is_expired(self) -> None:
        approval = make_approval(
            created_at="2026-09-11T08:00:02-04:00",
            expires_at="2026-09-11T08:05:00-04:00",
        )
        self.assertEqual(approval.created_at, "2026-09-11T12:00:02.000000Z")
        self.assertFalse(approval.is_expired("2026-09-11T12:04:59.999999Z"))
        self.assertTrue(approval.is_expired("2026-09-11T12:05:00Z"))
        self.assertTrue(approval.is_expired("2026-09-11T12:05:01Z"))
        with self.assertRaises(ApprovalError):
            approval.is_expired("not-a-timestamp")

    def test_invalid_expiry_fails_closed(self) -> None:
        with self.assertRaises(ApprovalError):
            make_approval(expires_at="2026-09-11T12:00:02Z")
        with self.assertRaises(ApprovalError):
            make_approval(created_at="2026-09-11T12:00:02")

    def test_consumed_at_is_passive_durable_timestamp_state(self) -> None:
        approval = make_approval(consumed_at="2026-09-11T08:00:03-04:00")
        self.assertEqual(approval.consumed_at, "2026-09-11T12:00:03.000000Z")
        with self.assertRaises(ApprovalError):
            make_approval(consumed_at="2026-09-11T12:00:01Z")
        with self.assertRaises(ApprovalError):
            make_approval(consumed_at="2026-09-11T12:05:00Z")
        with self.assertRaises(ApprovalError):
            make_approval(decision="REJECT", consumed_at="2026-09-11T12:00:03Z")

    def test_approve_and_reject_records_survive_restart(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
        approve = make_approval(request, policy_decision)
        reject = make_approval(
            request,
            policy_decision,
            approval_id="approval:reject",
            decision="REJECT",
        )
        with SQLiteStateStore(self.db) as store:
            persist_foundation(store, request, policy_decision)
            repo = ApprovalRepository(store)
            repo.put(approve)
            repo.put(reject)
        with SQLiteStateStore(self.db) as reopened:
            repo = ApprovalRepository(reopened)
            self.assertEqual(repo.get(approve.approval_id), approve)
            self.assertEqual(repo.get(reject.approval_id), reject)

    def test_approval_requires_durable_request(self) -> None:
        approval = make_approval()
        with SQLiteStateStore(self.db) as store:
            with self.assertRaises(ApprovalBindingError):
                ApprovalRepository(store).put(approval)

    def test_approval_requires_durable_policy_decision(self) -> None:
        request = make_request()
        approval = make_approval(request)
        with SQLiteStateStore(self.db) as store:
            EffectRequestRepository(store).put(request)
            with self.assertRaises(ApprovalBindingError):
                ApprovalRepository(store).put(approval)

    def test_only_require_approval_policy_decision_qualifies(self) -> None:
        for decision in ("ALLOW", "DENY"):
            with self.subTest(decision=decision):
                db = Path(self.tmp.name) / f"{decision.lower()}.db"
                request = make_request(request_id=f"effect:{decision.lower()}", idempotency_key=f"idem:{decision.lower()}")
                policy_decision = make_policy_decision(
                    request,
                    decision=decision,
                    decision_id=f"decision:{decision.lower()}",
                )
                approval = make_approval(
                    request,
                    policy_decision,
                    approval_id=f"approval:{decision.lower()}",
                )
                with SQLiteStateStore(db) as store:
                    persist_foundation(store, request, policy_decision)
                    with self.assertRaises(ApprovalBindingError):
                        ApprovalRepository(store).put(approval)

    def test_policy_decision_must_bind_same_request_and_hash(self) -> None:
        request_a = make_request()
        request_b = make_request(
            request_id="effect:approval-002",
            idempotency_key="idem:approval-002",
            arguments={"value": 8},
        )
        decision_b = make_policy_decision(request_b, decision_id="decision:approval-002")
        approval = make_approval(
            request_a,
            decision_b,
            policy_decision_id=decision_b.decision_id,
        )
        with SQLiteStateStore(self.db) as store:
            EffectRequestRepository(store).put(request_a)
            EffectRequestRepository(store).put(request_b)
            PolicyDecisionRepository(store).put(decision_b)
            with self.assertRaises(ApprovalBindingError):
                ApprovalRepository(store).put(approval)

    def test_wrong_canonical_hash_fails_binding(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
        approval = make_approval(
            request,
            policy_decision,
            canonical_request_hash="sha256:" + ("0" * 64),
        )
        with SQLiteStateStore(self.db) as store:
            persist_foundation(store, request, policy_decision)
            with self.assertRaises(ApprovalBindingError):
                ApprovalRepository(store).put(approval)

    def test_approval_cannot_predate_supporting_policy_decision(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request, evaluated_at="2026-09-11T12:00:03Z")
        approval = make_approval(
            request,
            policy_decision,
            created_at="2026-09-11T12:00:02Z",
        )
        with SQLiteStateStore(self.db) as store:
            persist_foundation(store, request, policy_decision)
            with self.assertRaises(ApprovalBindingError):
                ApprovalRepository(store).put(approval)

    def test_duplicate_identity_is_idempotent_but_cannot_overwrite_material(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
        approve = make_approval(request, policy_decision)
        reject = make_approval(request, policy_decision, decision="REJECT")
        with SQLiteStateStore(self.db) as store:
            persist_foundation(store, request, policy_decision)
            repo = ApprovalRepository(store)
            first = repo.put(approve)
            second = repo.put(make_approval(request, policy_decision))
            self.assertEqual(first, second)
            with self.assertRaises(ApprovalIdentityConflict):
                repo.put(reject)
            self.assertEqual(repo.get(approve.approval_id), approve)

    def test_corrupted_persisted_approval_fails_closed(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
        approval = make_approval(request, policy_decision)
        with SQLiteStateStore(self.db) as store:
            persist_foundation(store, request, policy_decision)
            repo = ApprovalRepository(store)
            repo.put(approval)
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE approvals SET schema = ? WHERE approval_id = ?",
                    ("lac.approval/v999", approval.approval_id),
                )
            with self.assertRaises(StateStoreError):
                repo.get(approval.approval_id)

    def test_corrupted_supporting_policy_decision_cannot_support_new_approval(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
        approval = make_approval(request, policy_decision)
        with SQLiteStateStore(self.db) as store:
            persist_foundation(store, request, policy_decision)
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE policy_decisions SET reason_codes_json = ? WHERE decision_id = ?",
                    ('["z","a"]', policy_decision.decision_id),
                )
            with self.assertRaises(StateStoreError):
                ApprovalRepository(store).put(approval)

    def test_corrupted_supporting_policy_decision_fails_closed_on_reload(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
        approval = make_approval(request, policy_decision)
        with SQLiteStateStore(self.db) as store:
            persist_foundation(store, request, policy_decision)
            repo = ApprovalRepository(store)
            repo.put(approval)
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE policy_decisions SET reason_codes_json = ? WHERE decision_id = ?",
                    ('["z","a"]', policy_decision.decision_id),
                )
            with self.assertRaises(StateStoreError):
                repo.get(approval.approval_id)

    def test_schema_v3_database_migrates_forward_without_losing_predecessor_state(self) -> None:
        request = make_request()
        policy_decision = make_policy_decision(request)
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
        for migration in state_store_module._MIGRATIONS[:3]:
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
        conn.commit()
        conn.close()

        with SQLiteStateStore(self.db) as migrated:
            self.assertEqual(migrated.schema_version, SCHEMA_VERSION)
            self.assertEqual(SCHEMA_VERSION, 6)
            self.assertEqual(EffectRequestRepository(migrated).get(request.request_id), request)
            self.assertEqual(
                PolicyDecisionRepository(migrated).get(policy_decision.decision_id),
                policy_decision,
            )
            table = migrated._conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='approvals'"
            ).fetchone()
            self.assertIsNotNone(table)

    def test_approval_record_has_no_dispatch_or_execution_surface(self) -> None:
        approval = make_approval()
        repo_public = {
            name for name in dir(ApprovalRepository) if not name.startswith("_")
        }
        approval_public = {name for name in dir(approval) if not name.startswith("_")}
        self.assertEqual(repo_public, {"get", "put"})
        self.assertFalse({"execute", "dispatch", "authorize"} & approval_public)


if __name__ == "__main__":
    unittest.main()
