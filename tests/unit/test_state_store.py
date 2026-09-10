import os
import sqlite3
import stat
import tempfile
import unittest
from pathlib import Path

from packages.state import (
    MigrationIntegrityError,
    SCHEMA_VERSION,
    SQLiteStateStore,
    StateStoreError,
    UnsupportedSchemaVersion,
)


class SQLiteStateStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "state" / "controller.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_new_database_uses_required_sqlite_configuration(self) -> None:
        with SQLiteStateStore(self.db) as store:
            self.assertEqual(store.schema_version, SCHEMA_VERSION)
            self.assertEqual(store.journal_mode, "wal")
            self.assertTrue(store.foreign_keys_enabled)
            rows = store._conn.execute(
                "SELECT version, name, checksum_sha256 FROM schema_migrations ORDER BY version"
            ).fetchall()
            self.assertEqual(len(rows), SCHEMA_VERSION)
            self.assertEqual([row["version"] for row in rows], list(range(1, SCHEMA_VERSION + 1)))
            for row in rows:
                self.assertEqual(len(row["checksum_sha256"]), 64)

    def test_system_state_survives_close_and_reopen(self) -> None:
        payload = {"paused": False, "generation": 7, "labels": ["local", "durable"]}
        with SQLiteStateStore(self.db) as store:
            store.set_system_state("controller.test", payload)
        with SQLiteStateStore(self.db) as reopened:
            self.assertEqual(reopened.get_system_state("controller.test"), payload)

    def test_failed_transaction_rolls_back(self) -> None:
        with SQLiteStateStore(self.db) as store:
            with self.assertRaises(RuntimeError):
                with store.transaction() as conn:
                    conn.execute(
                        "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?)",
                        ("rollback.test", '{"should":"not persist"}', "test"),
                    )
                    raise RuntimeError("force rollback")
            self.assertIsNone(store.get_system_state("rollback.test"))

    def test_nested_transaction_fails_closed(self) -> None:
        with SQLiteStateStore(self.db) as store:
            with store.transaction():
                with self.assertRaises(StateStoreError):
                    with store.transaction():
                        pass

    def test_future_schema_version_fails_closed(self) -> None:
        self.db.parent.mkdir(parents=True)
        conn = sqlite3.connect(self.db)
        conn.execute("PRAGMA user_version=99")
        conn.commit()
        conn.close()
        with self.assertRaises(UnsupportedSchemaVersion):
            SQLiteStateStore(self.db)

    def test_migration_checksum_mismatch_fails_closed(self) -> None:
        with SQLiteStateStore(self.db):
            pass
        conn = sqlite3.connect(self.db)
        conn.execute("UPDATE schema_migrations SET checksum_sha256 = ? WHERE version = 1", ("0" * 64,))
        conn.commit()
        conn.close()
        with self.assertRaises(MigrationIntegrityError):
            SQLiteStateStore(self.db)

    def test_non_json_value_is_rejected_without_partial_write(self) -> None:
        with SQLiteStateStore(self.db) as store:
            with self.assertRaises(StateStoreError):
                store.set_system_state("bad.value", {1, 2, 3})
            self.assertIsNone(store.get_system_state("bad.value"))

    @unittest.skipUnless(os.name == "posix", "POSIX permission check")
    def test_database_file_is_owner_only(self) -> None:
        with SQLiteStateStore(self.db):
            self.assertEqual(stat.S_IMODE(self.db.stat().st_mode), 0o600)

    def test_in_memory_database_is_rejected(self) -> None:
        with self.assertRaises(StateStoreError):
            SQLiteStateStore(":memory:")


if __name__ == "__main__":
    unittest.main()
