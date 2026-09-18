from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from packages.admin import AdminRequest, AdminService
from packages.adapters.pi.production import (
    PI_V1_AGENT_ID,
    PI_V1_APPLICATION_ID,
    PI_V1_CAPABILITY_MANIFEST,
    PI_V1_PRINCIPAL_ID,
    PI_V1_SKILL_ID,
    PiPermissionRuntime,
)
from packages.capabilities import CapabilityManifest
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.policy import StandingPolicyRule
from packages.runtime import (
    NATIVE_LOCAL_CONSUMER_CONTINUATION_STATUS_SCHEMA,
    NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA,
    normalize_continuation_status,
    normalize_native_result,
)
from packages.state import AgentIdentityRepository, EmergencyPauseRepository, SQLiteStateStore

ROOT = Path(__file__).resolve().parents[2]


class Pi003PiConformanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lac-pi003-pi-")
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.store = SQLiteStateStore(self.root / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active(PI_V1_AGENT_ID, PI_V1_PRINCIPAL_ID)
        self.admin = AdminService(self.store, owner_uid=os.getuid())
        self.runtime = PiPermissionRuntime(
            store=self.store,
            filesystem_adapter=FilesystemEffectAdapter(self.workspace),
            shell_adapter=ShellEffectAdapter(
                self.workspace, allowed_executables=(Path("/usr/bin/printf"),)
            ),
            run_id="run:pi003:pi-conformance",
        )
        manifest = CapabilityManifest.create(PI_V1_CAPABILITY_MANIFEST)
        self.admin_call("skills.register", {"manifest": json.loads(manifest.canonical_json())})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def admin_call(self, operation, arguments):
        req = AdminRequest.create(
            request_id=f"admin:pi003-pi:{operation}:{os.urandom(6).hex()}",
            operation=operation,
            arguments=arguments,
        )
        return self.admin.execute(req, peer_uid=os.getuid())

    def set_allow_create(self):
        rule = StandingPolicyRule.create(
            rule_id="pi003-pi-allow-create",
            application_id=PI_V1_APPLICATION_ID,
            skill_id=PI_V1_SKILL_ID,
            action="filesystem.create",
            resource_selector="filesystem:workspace",
            decision="ALLOW",
        )
        self.admin_call(
            "permissions.replace", {"rules": [rule.to_material()], "defaults": []}
        )

    @staticmethod
    def message(call_id):
        return {
            "toolCallId": call_id,
            "toolName": "lac_fs_create",
            "arguments": {"path": f"{call_id}.txt", "content": call_id},
        }

    def test_governed_pi_emits_exact_native_result_contract(self):
        self.set_allow_create()
        result = self.runtime.submit_message(self.message("native-allow"))
        self.assertEqual(result["schema"], NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA)
        self.assertEqual(normalize_native_result(result), result)
        self.assertEqual((result["authority_outcome"], result["execution_state"]), ("ALLOW", "SUCCEEDED"))
        self.assertEqual((self.workspace / "native-allow.txt").read_text(), "native-allow")

    def test_governed_pi_permission_wait_emits_exact_native_continuation_status(self):
        result = self.runtime.submit_message(self.message("native-wait"))
        self.assertEqual(result["schema"], NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA)
        status = result["workflow_continuation"]
        self.assertEqual(status["schema"], NATIVE_LOCAL_CONSUMER_CONTINUATION_STATUS_SCHEMA)
        self.assertEqual(normalize_continuation_status(status), status)
        self.assertEqual(status["state"], "WAITING_PERMISSION")
        self.assertFalse((self.workspace / "native-wait.txt").exists())

    def test_pi_edge_is_translation_only_for_contract_workflow(self):
        source = (ROOT / "packages" / "adapters" / "pi" / "production.py").read_text()
        self.assertIn("NativeLocalConsumerRuntime", source)
        self.assertIn("return self.consumer.submit(material)", source)
        self.assertIn("return self.consumer.resume(", source)
        self.assertNotIn("PendingPermissionRepository", source)
        self.assertNotIn("DispatchPaused", source)
        self.assertNotIn("PiWorkflowContinuationStore", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
