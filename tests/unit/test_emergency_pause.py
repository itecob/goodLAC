import tempfile
import unittest
from pathlib import Path

from packages.state import (
    EMERGENCY_PAUSE_SCHEMA,
    EMERGENCY_PAUSE_STATE_KEY,
    EmergencyPauseRepository,
    EmergencyPauseStateError,
    SCHEMA_VERSION,
    SQLiteStateStore,
)


class EmergencyPauseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        self.repo = EmergencyPauseRepository(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_missing_authority_fails_closed_until_explicit_transition(self):
        with self.assertRaises(EmergencyPauseStateError):
            self.repo.get()
        state = self.repo.resume()
        self.assertEqual(state.schema, EMERGENCY_PAUSE_SCHEMA)
        self.assertFalse(state.paused)
        self.assertEqual(self.store.schema_version, 6)
        self.assertEqual(SCHEMA_VERSION, 6)

    def test_pause_resume_are_durable_across_restart(self):
        self.repo.resume()
        paused = self.repo.pause()
        self.assertTrue(paused.paused)
        self.store.close()
        self.store = SQLiteStateStore(self.db)
        self.repo = EmergencyPauseRepository(self.store)
        self.assertTrue(self.repo.get().paused)
        self.assertFalse(self.repo.resume().paused)
        self.store.close()
        self.store = SQLiteStateStore(self.db)
        self.repo = EmergencyPauseRepository(self.store)
        self.assertFalse(self.repo.get().paused)

    def test_transitions_are_idempotent_and_api_cannot_authorize_effects(self):
        self.assertFalse(self.repo.resume().paused)
        self.assertFalse(self.repo.resume().paused)
        self.assertTrue(self.repo.pause().paused)
        self.assertTrue(self.repo.pause().paused)
        public = {name for name in dir(EmergencyPauseRepository) if not name.startswith("_")}
        self.assertEqual(public, {"get", "pause", "resume"})
        self.assertFalse({"authorize", "dispatch", "execute", "approve"} & public)

    def test_malformed_authority_cannot_be_read_or_silently_repaired(self):
        corruptions = (
            "not-json",
            '{"schema":"lac.emergency-pause/v999","paused":false}',
            '{"schema":"lac.emergency-pause/v1","paused":0}',
            '{"schema":"lac.emergency-pause/v1","paused":false,"extra":1}',
            '{"schema":"lac.emergency-pause/v1"}',
        )
        for idx, encoded in enumerate(corruptions):
            with self.subTest(case=idx):
                db = Path(self.tmp.name) / f"corrupt-{idx}.db"
                with SQLiteStateStore(db) as store:
                    repo = EmergencyPauseRepository(store)
                    repo.resume()
                    with store.transaction() as conn:
                        conn.execute(
                            "UPDATE system_state SET value_json = ? WHERE key = ?",
                            (encoded, EMERGENCY_PAUSE_STATE_KEY),
                        )
                    with self.assertRaises(EmergencyPauseStateError):
                        repo.get()
                    with self.assertRaises(EmergencyPauseStateError):
                        repo.resume()
                    with self.assertRaises(EmergencyPauseStateError):
                        repo.pause()
                    persisted = store._conn.execute(
                        "SELECT value_json FROM system_state WHERE key = ?",
                        (EMERGENCY_PAUSE_STATE_KEY,),
                    ).fetchone()[0]
                    self.assertEqual(persisted, encoded)

    def test_pause_state_uses_existing_system_state_without_schema_migration(self):
        self.repo.pause()
        self.assertEqual(SCHEMA_VERSION, 6)
        self.assertEqual(self.store.schema_version, 6)
        row = self.store._conn.execute(
            "SELECT value_json FROM system_state WHERE key = ?",
            (EMERGENCY_PAUSE_STATE_KEY,),
        ).fetchone()
        self.assertIsNotNone(row)
        self.assertEqual(
            row[0],
            '{"paused":true,"schema":"lac.emergency-pause/v1"}',
        )


if __name__ == "__main__":
    unittest.main()
