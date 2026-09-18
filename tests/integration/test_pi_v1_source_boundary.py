from __future__ import annotations

import unittest
from pathlib import Path

from packages.lacctl import ADMIN_OPERATIONS

ROOT = Path(__file__).resolve().parents[2]


class PiV1SourceBoundaryTests(unittest.TestCase):
    def test_profile_reuses_accepted_pi_sandbox_and_native_controller_runtime(self):
        terminal = (ROOT / "scripts" / "pi_v1_terminal.py").read_text()
        production = (ROOT / "packages" / "adapters" / "pi" / "production.py").read_text()
        native = (ROOT / "packages" / "runtime" / "native_consumer.py").read_text()
        continuation = (ROOT / "packages" / "runtime" / "workflow_continuation.py").read_text()
        worker = (ROOT / "scripts" / "a004_agent_worker.mjs").read_text()
        self.assertIn("scripts.a004_terminal", terminal)
        self.assertIn("ExternalConsumerRuntime", production)
        self.assertIn("NativeLocalConsumerRuntime", production)
        self.assertNotIn("PendingPermissionRepository", production)
        self.assertNotIn("DispatchPaused", production)
        self.assertNotIn("PiWorkflowContinuationStore", production)
        self.assertIn("NetworkMode.NONE", (ROOT / "scripts" / "a004_terminal.py").read_text())
        self.assertIn('type === "tool_probe"', worker)
        self.assertNotIn("admin-v1.sock", worker)
        for source in (production, native, continuation):
            self.assertNotIn("packages.admin", source)
            self.assertNotIn("admin-v1.sock", source)
            self.assertNotIn("LacctlClient", source)

    def test_permission_configuration_blocks_host_rpc_before_model_receives_result(self):
        terminal = (ROOT / "scripts" / "pi_v1_terminal.py").read_text()
        worker = (ROOT / "scripts" / "a004_agent_worker.mjs").read_text()
        self.assertIn("return self._permission_wait(payload, result)", terminal)
        self.assertIn("workflow suspended before model continuation", terminal)
        self.assertIn('await rpc("effect_request"', worker)
        self.assertIn("const result = await tool.execute", worker)

    def test_restart_recovery_surface_requires_explicit_resume(self):
        terminal = (ROOT / "scripts" / "pi_v1_terminal.py").read_text()
        self.assertIn("/continuations", terminal)
        self.assertIn("/resume <continuation_id>", terminal)
        self.assertIn("No effect was dispatched on restart", terminal)
        self.assertNotIn("auto-resume-on-startup", terminal)

    def test_builtin_registration_is_controller_owned_and_lacctl_stays_narrow(self):
        terminal = (ROOT / "scripts" / "pi_v1_terminal.py").read_text()
        admin_server = (ROOT / "scripts" / "pi_v1_admin_server.py").read_text()
        self.assertNotIn('operation="skills.register"', terminal)
        self.assertIn('operation="skills.register"', admin_server)
        self.assertIn("AdminRequest.create", admin_server)
        self.assertIn("service.execute", admin_server)
        self.assertNotIn("skills.register", ADMIN_OPERATIONS)

    def test_model_tool_surface_stays_four_and_rejects_authority_material(self):
        governed = (ROOT / "packages" / "adapters" / "pi" / "governed_pi.mjs").read_text()
        for tool in (
            "lac_fs_read",
            "lac_fs_create",
            "lac_fs_replace",
            "lac_shell_exec",
        ):
            self.assertIn(tool, governed)
        self.assertIn("cannot supply controller authority identifiers", governed)


if __name__ == "__main__":
    unittest.main(verbosity=2)
