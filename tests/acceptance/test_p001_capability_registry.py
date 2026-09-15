import tempfile
import unittest
from pathlib import Path

import packages.adapters
from packages.capabilities import (
    CAPABILITY_MANIFEST_SCHEMA,
    CapabilityManifest,
    CapabilityManifestError,
    CapabilityRegistry,
)
from packages.state.store import SCHEMA_VERSION, SQLiteStateStore


def manifest_fixture():
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "acceptance-app",
        "skill_id": "reader",
        "actions": [
            {
                "action": "document.read",
                "resource": {"type": "document.local", "selectors": ["document:workspace"]},
                "arguments": {
                    "type": "object",
                    "properties": {
                        "document_id": {"type": "string", "minLength": 1, "maxLength": 128}
                    },
                    "required": ["document_id"],
                    "additionalProperties": False,
                },
                "security_properties": ["read_only"],
            }
        ],
    }


class P001AcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        self.registry = CapabilityRegistry(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def _count(self, table):
        return int(self.store._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])

    def test_registration_grants_zero_authority_or_effect_state(self):
        self.assertEqual(SCHEMA_VERSION, 6, "P001 must not broaden the accepted DB schema unnecessarily")
        self.registry.register_admin(CapabilityManifest.create(manifest_fixture()))
        for table in (
            "policy_decisions",
            "approvals",
            "execution_leases",
            "effect_executions",
            "effect_receipts",
        ):
            self.assertEqual(self._count(table), 0, table)
        self.assertEqual(self._count("effect_requests"), 0)

    def test_rejected_secret_value_is_never_persisted(self):
        canary = "P001_CANARY_SERVICE_CREDENTIAL_DO_NOT_PERSIST"
        invalid = manifest_fixture()
        invalid["actions"][0]["arguments"]["properties"]["document_id"]["default"] = canary
        with self.assertRaises(CapabilityManifestError):
            CapabilityManifest.create(invalid)
        rows = self.store._conn.execute("SELECT value_json FROM system_state").fetchall()
        self.assertNotIn(canary, "\n".join(str(row[0]) for row in rows))

    def test_runtime_adapter_namespace_has_no_registry_mutation_surface(self):
        self.assertFalse(hasattr(packages.adapters, "CapabilityRegistry"))
        self.assertFalse(hasattr(packages.adapters, "register_admin"))
        adapters_root = Path(packages.adapters.__file__).parent
        for path in adapters_root.rglob("*"):
            if path.is_file() and path.suffix in {".py", ".mjs", ".js"}:
                text = path.read_text(encoding="utf-8")
                self.assertNotIn("register_admin", text, str(path))
                self.assertNotIn("capability_registry.latest", text, str(path))


if __name__ == "__main__":
    unittest.main()
