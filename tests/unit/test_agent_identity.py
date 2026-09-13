import tempfile
import unittest
from pathlib import Path

from packages.state import (
    AgentIdentityConflict,
    AgentIdentityRepository,
    AgentIdentityStateError,
    AgentStatus,
    SCHEMA_VERSION,
    SQLiteStateStore,
)


class AgentIdentityRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        self.identities = AgentIdentityRepository(self.store)

    def tearDown(self):
        try:
            self.store.close()
        finally:
            self.tmp.cleanup()

    def test_active_identity_and_revocation_are_durable_without_schema_migration(self):
        active = self.identities.register_active("agent:test", "principal:owner")
        self.assertEqual(active.status, AgentStatus.ACTIVE)
        revoked = self.identities.revoke("agent:test")
        self.assertEqual(revoked.status, AgentStatus.REVOKED)
        self.assertEqual(SCHEMA_VERSION, 6)
        self.assertEqual(self.store.schema_version, 6)

        self.store.close()
        self.store = SQLiteStateStore(self.db)
        self.identities = AgentIdentityRepository(self.store)
        self.assertEqual(self.identities.get("agent:test"), revoked)

    def test_registration_is_idempotent_but_cannot_rebind_or_silently_reactivate(self):
        first = self.identities.register_active("agent:test", "principal:owner")
        self.assertEqual(
            self.identities.register_active("agent:test", "principal:owner"), first
        )
        with self.assertRaises(AgentIdentityConflict):
            self.identities.register_active("agent:test", "principal:other")

        self.identities.revoke("agent:test")
        with self.assertRaises(AgentIdentityConflict):
            self.identities.register_active("agent:test", "principal:owner")
        self.assertEqual(
            self.identities.activate("agent:test").status,
            AgentStatus.ACTIVE,
        )

    def test_unknown_and_corrupted_identity_fail_closed(self):
        self.assertIsNone(self.identities.get("agent:missing"))
        self.identities.register_active("agent:test", "principal:owner")
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE system_state SET value_json = ? WHERE key = ?",
                ('{"schema":"lac.agent-identity/v1","agent_id":"agent:other","principal_id":"principal:owner","status":"ACTIVE"}',
                 "controller.agent_identity:agent:test"),
            )
        with self.assertRaises(AgentIdentityStateError):
            self.identities.get("agent:test")


if __name__ == "__main__":
    unittest.main()
