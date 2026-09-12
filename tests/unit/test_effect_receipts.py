import sqlite3
import tempfile
import unittest
from pathlib import Path

import packages.state.store as store_module
from packages.core import (
    EffectExecution,
    EffectExecutionState,
    EffectOutcome,
    EffectReceiptError,
    EffectRequest,
    ExecutionLease,
)
from packages.state import (
    AuditRepository,
    EffectReceiptRepository,
    EffectReceiptStateError,
    EffectRequestRepository,
    ExecutionLeaseRepository,
    SCHEMA_VERSION,
    SQLiteStateStore,
)


def make_request():
    return EffectRequest.create(
        request_id="effect:c010-unit",
        run_id="run:c010-unit",
        principal_id="principal:owner",
        agent_id="agent:test",
        action="simulated.write",
        resource="simulated:alpha",
        arguments={"value": 11},
        idempotency_key="idem:c010-unit",
        created_at="2026-09-12T10:00:00Z",
        expires_at="2026-09-12T10:20:00Z",
    )


def create_v5_database(path: Path):
    conn = sqlite3.connect(path)
    try:
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute(
            """CREATE TABLE schema_migrations (
                version INTEGER PRIMARY KEY NOT NULL,
                name TEXT UNIQUE NOT NULL,
                checksum_sha256 TEXT NOT NULL CHECK(length(checksum_sha256) = 64)
            )"""
        )
        for migration in store_module._MIGRATIONS[:5]:
            for statement in migration.statements:
                conn.execute(statement)
            conn.execute(
                "INSERT INTO schema_migrations(version,name,checksum_sha256) VALUES (?,?,?)",
                (migration.version, migration.name, migration.checksum),
            )
            conn.execute(f"PRAGMA user_version={migration.version}")
        conn.commit()
    finally:
        conn.close()


class EffectReceiptStateTests(unittest.TestCase):
    def test_schema_v5_migrates_atomically_to_v6_and_preserves_predecessor_state(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "controller.db"
            create_v5_database(db)
            predecessor = sqlite3.connect(db)
            predecessor.execute(
                "INSERT INTO system_state(key,value_json,updated_at_utc) VALUES (?,?,?)",
                ("predecessor.marker", '"preserved"', "2026-09-12T10:00:00Z"),
            )
            predecessor.commit()
            predecessor.close()
            with SQLiteStateStore(db) as migrated:
                self.assertEqual(SCHEMA_VERSION, 6)
                self.assertEqual(migrated.schema_version, 6)
                self.assertEqual(migrated.get_system_state("predecessor.marker"), "preserved")
                for table in ("effect_executions", "effect_receipts", "audit_events"):
                    self.assertIsNotNone(
                        migrated._conn.execute(
                            "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table,)
                        ).fetchone()
                    )

    def test_failed_v6_migration_rolls_back_user_version_and_ledger(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "controller.db"
            create_v5_database(db)
            conn = sqlite3.connect(db)
            conn.execute("CREATE TABLE effect_executions(dummy TEXT)")
            conn.commit()
            conn.close()
            with self.assertRaises(sqlite3.OperationalError):
                SQLiteStateStore(db)
            check = sqlite3.connect(db)
            try:
                self.assertEqual(check.execute("PRAGMA user_version").fetchone()[0], 5)
                self.assertIsNone(
                    check.execute("SELECT 1 FROM schema_migrations WHERE version=6").fetchone()
                )
                self.assertIsNone(
                    check.execute(
                        "SELECT name FROM sqlite_master WHERE type='table' AND name='effect_receipts'"
                    ).fetchone()
                )
            finally:
                check.close()

    def test_execution_receipt_and_audit_survive_restart_and_audit_has_no_authority_api(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "controller.db"
            request = make_request()
            store = SQLiteStateStore(db)
            EffectRequestRepository(store).put(request)
            lease = ExecutionLease.create(
                lease_id="lease:c010-unit",
                request_id=request.request_id,
                executor_id="executor:c010",
                issued_at="2026-09-12T10:04:00Z",
                expires_at="2026-09-12T10:04:20Z",
            )
            ExecutionLeaseRepository(store).acquire(lease)
            with store.transaction() as conn:
                repo = EffectReceiptRepository(store)
                leased = repo._record_leased_in_transaction(
                    conn, request=request, adapter_id="simulated:v1", lease=lease,
                    approval_id=None, leased_at="2026-09-12T10:04:00Z"
                )
                AuditRepository(store)._append_in_transaction(
                    conn, request_id=request.request_id, event_type="EFFECT_LEASED",
                    occurred_at="2026-09-12T10:04:00Z", details={"source": "unit"}
                )
            with store.transaction() as conn:
                prepared = EffectReceiptRepository(store)._mark_prepared_in_transaction(
                    conn, leased, prepared_at="2026-09-12T10:04:01Z"
                )
            with store.transaction() as conn:
                terminal, receipt = EffectReceiptRepository(store)._complete_in_transaction(
                    conn, prepared, outcome=EffectOutcome.SUCCEEDED,
                    result={"ok": True}, completed_at="2026-09-12T10:04:02Z"
                )
            self.assertEqual(terminal.state, EffectExecutionState.SUCCEEDED)
            self.assertEqual(receipt.result, {"ok": True})
            store.close()
            store = SQLiteStateStore(db)
            self.assertEqual(
                EffectReceiptRepository(store).get_execution(request.request_id), terminal
            )
            self.assertEqual(
                EffectReceiptRepository(store).get_receipt_for_request(request.request_id), receipt
            )
            events = AuditRepository(store).list_for_request(request.request_id)
            self.assertEqual([e.event_type for e in events], ["EFFECT_LEASED"])
            public = {n for n in dir(AuditRepository) if not n.startswith("_")}
            self.assertEqual(public, {"list_for_request"})
            store.close()

    def test_malformed_execution_state_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            db = Path(td) / "controller.db"
            request = make_request()
            store = SQLiteStateStore(db)
            EffectRequestRepository(store).put(request)
            lease = ExecutionLease.create(
                lease_id="lease:c010-corrupt", request_id=request.request_id,
                executor_id="executor:c010", issued_at="2026-09-12T10:04:00Z",
                expires_at="2026-09-12T10:04:20Z"
            )
            ExecutionLeaseRepository(store).acquire(lease)
            with store.transaction() as conn:
                EffectReceiptRepository(store)._record_leased_in_transaction(
                    conn, request=request, adapter_id="simulated:v1", lease=lease,
                    approval_id=None, leased_at="2026-09-12T10:04:00Z"
                )
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE effect_executions SET input_hash=? WHERE request_id=?",
                    ("sha256:" + "0" * 64, request.request_id),
                )
            with self.assertRaises(EffectReceiptStateError):
                EffectReceiptRepository(store).get_execution(request.request_id)
            store.close()

    def test_unknown_effect_execution_and_receipt_schemas_fail_closed(self):
        with self.assertRaises(EffectReceiptError):
            EffectExecution.create(
                schema="lac.effect-execution/v999", request_id="e", canonical_request_hash="sha256:"+"0"*64,
                idempotency_key="i", adapter_id="a", lease_id="l", lease_hash="sha256:"+"1"*64,
                input_hash="sha256:"+"2"*64, approval_id=None, state="LEASED",
                leased_at="2026-09-12T10:00:00Z"
            )


if __name__ == "__main__":
    unittest.main()
