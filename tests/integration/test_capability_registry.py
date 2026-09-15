import copy
import json
import tempfile
import unittest
from pathlib import Path

from packages.capabilities import (
    CAPABILITY_MANIFEST_SCHEMA,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilityRegistryIntegrityError,
)
from packages.state.store import SQLiteStateStore


def manifest_fixture(*, description="Synthetic fixture", extra_security=None):
    security = ["external_mutation", "external_communication", "network_egress"]
    if extra_security:
        security.extend(extra_security)
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "consumer-app",
        "skill_id": "mail-skill",
        "actions": [
            {
                "action": "mail.send",
                "resource": {"type": "mail.account", "selectors": ["mail:primary"]},
                "arguments": {
                    "type": "object",
                    "properties": {
                        "to": {"type": "string", "minLength": 3, "maxLength": 320},
                        "subject": {"type": "string", "maxLength": 998},
                        "body": {"type": "string", "maxLength": 65536},
                    },
                    "required": ["body", "subject", "to"],
                    "additionalProperties": False,
                },
                "security_properties": security,
            }
        ],
        "display": {"name": "Mail skill", "description": description},
    }


class CapabilityRegistryIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        self.registry = CapabilityRegistry(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_registration_survives_controller_restart(self):
        manifest = CapabilityManifest.create(manifest_fixture())
        registered = self.registry.register_admin(manifest)
        self.assertEqual(registered.revision, 1)
        self.assertEqual(registered.manifest_hash, manifest.canonical_hash)
        self.store.close()
        self.store = SQLiteStateStore(self.db)
        self.registry = CapabilityRegistry(self.store)
        reopened = self.registry.get_latest("consumer-app", "mail-skill")
        self.assertIsNotNone(reopened)
        self.assertEqual(reopened.revision, 1)
        self.assertEqual(reopened.manifest.canonical_json(), manifest.canonical_json())

    def test_identical_registration_is_idempotent(self):
        manifest = CapabilityManifest.create(manifest_fixture())
        first = self.registry.register_admin(manifest)
        second = self.registry.register_admin(manifest)
        self.assertEqual(first, second)
        self.assertEqual(len(self.registry.history("consumer-app", "mail-skill")), 1)
        self.assertEqual(len(self.registry.audit_events("consumer-app", "mail-skill")), 1)

    def test_security_change_is_append_only_distinct_revision(self):
        first_manifest = CapabilityManifest.create(manifest_fixture())
        first = self.registry.register_admin(first_manifest)
        changed_raw = manifest_fixture(extra_security=["credential_sensitive"])
        second_manifest = CapabilityManifest.create(changed_raw)
        second = self.registry.register_admin(second_manifest)
        self.assertEqual(first.revision, 1)
        self.assertEqual(second.revision, 2)
        self.assertNotEqual(first.security_hash, second.security_hash)
        history = self.registry.history("consumer-app", "mail-skill")
        self.assertEqual([item.revision for item in history], [1, 2])
        self.assertEqual(history[0].manifest_hash, first.manifest_hash)
        events = self.registry.audit_events("consumer-app", "mail-skill")
        self.assertEqual([event["security_changed"] for event in events], [True, True])

    def test_display_only_change_is_revisioned_but_not_security_change(self):
        first = self.registry.register_admin(CapabilityManifest.create(manifest_fixture()))
        second = self.registry.register_admin(
            CapabilityManifest.create(manifest_fixture(description="Display-only update"))
        )
        self.assertEqual(second.revision, 2)
        self.assertNotEqual(first.manifest_hash, second.manifest_hash)
        self.assertEqual(first.security_hash, second.security_hash)
        events = self.registry.audit_events("consumer-app", "mail-skill")
        self.assertFalse(events[-1]["security_changed"])

    def test_noncanonical_persisted_revision_fails_closed(self):
        registration = self.registry.register_admin(CapabilityManifest.create(manifest_fixture()))
        row = self.store._conn.execute(
            "SELECT key, value_json FROM system_state WHERE key LIKE 'capability_registry.revision.%'"
        ).fetchone()
        parsed = json.loads(row["value_json"])
        pretty = json.dumps(parsed, indent=2, sort_keys=True)
        with self.store.transaction() as conn:
            conn.execute("UPDATE system_state SET value_json=? WHERE key=?", (pretty, row["key"]))
        with self.assertRaises(CapabilityRegistryIntegrityError):
            self.registry.get_latest(registration.application_id, registration.skill_id)

    def test_manifest_hash_tamper_fails_closed(self):
        registration = self.registry.register_admin(CapabilityManifest.create(manifest_fixture()))
        row = self.store._conn.execute(
            "SELECT key, value_json FROM system_state WHERE key LIKE 'capability_registry.revision.%'"
        ).fetchone()
        parsed = json.loads(row["value_json"])
        parsed["manifest_hash"] = "sha256:" + "0" * 64
        tampered = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        with self.store.transaction() as conn:
            conn.execute("UPDATE system_state SET value_json=? WHERE key=?", (tampered, row["key"]))
        with self.assertRaises(CapabilityRegistryIntegrityError):
            self.registry.get_latest(registration.application_id, registration.skill_id)

    def test_audit_hash_tamper_fails_closed(self):
        registration = self.registry.register_admin(CapabilityManifest.create(manifest_fixture()))
        row = self.store._conn.execute(
            "SELECT key, value_json FROM system_state WHERE key LIKE 'capability_registry.audit.%'"
        ).fetchone()
        parsed = json.loads(row["value_json"])
        parsed["security_hash"] = "sha256:" + "1" * 64
        tampered = json.dumps(parsed, sort_keys=True, separators=(",", ":"))
        with self.store.transaction() as conn:
            conn.execute("UPDATE system_state SET value_json=? WHERE key=?", (tampered, row["key"]))
        with self.assertRaises(CapabilityRegistryIntegrityError):
            self.registry.get_latest(registration.application_id, registration.skill_id)

    def test_list_latest_returns_stable_identity_pairs(self):
        self.registry.register_admin(CapabilityManifest.create(manifest_fixture()))
        other = copy.deepcopy(manifest_fixture())
        other["application_id"] = "another-app"
        other["skill_id"] = "another-skill"
        self.registry.register_admin(CapabilityManifest.create(other))
        identities = [(item.application_id, item.skill_id) for item in self.registry.list_latest()]
        self.assertEqual(
            identities,
            [("another-app", "another-skill"), ("consumer-app", "mail-skill")],
        )


if __name__ == "__main__":
    unittest.main()
