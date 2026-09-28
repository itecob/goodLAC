from __future__ import annotations

import unittest
from pathlib import Path

from packages.lacctl import ADMIN_OPERATIONS

ROOT = Path(__file__).resolve().parents[2]


class PiV1SourceBoundaryTests(unittest.TestCase):
    def test_model_prompt_scopes_deny_once_to_exact_request_without_weakening_standing_deny(self):
        from scripts import pi_v1_terminal

        prompt = pi_v1_terminal.system_prompt()
        self.assertIn("current tool request", prompt)
        self.assertIn("OWNER_DENY_ONCE", prompt)
        self.assertIn("only the exact completed request was denied", prompt)
        self.assertIn("not a standing instruction or durable user preference", prompt)
        self.assertIn("later explicitly asks for the same or an equivalent operation in a new turn", prompt)
        self.assertIn("submit a new governed tool request", prompt)
        self.assertIn("controller independently evaluates that fresh request", prompt)
        self.assertIn("configured standing DENY is different", prompt)
        self.assertIn("do not retry or seek an alternate consequential route to bypass", prompt)

    def test_deny_once_tool_result_carries_non_authoritative_fresh_request_semantics(self):
        governed = (ROOT / "packages" / "adapters" / "pi" / "governed_pi.mjs").read_text()
        gate = (ROOT / "packages" / "adapters" / "pi" / "tui_owner_gate.py").read_text()
        self.assertIn('result.reason === "OWNER_DENY_ONCE"', governed)
        self.assertIn("denied only the exact completed request", governed)
        self.assertIn("not a standing deny", governed)
        self.assertIn("later explicitly asks for the same or an equivalent operation in a new turn", governed)
        self.assertIn("call the governed tool normally", governed)
        self.assertIn('"owner_decision_scope": "EXACT_REQUEST_ONLY"', gate)
        self.assertIn('"standing_policy_changed": False', gate)
        self.assertIn('"future_equivalent_requests": "REQUIRE_FRESH_CONTROLLER_EVALUATION"', gate)

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
        bridge = (ROOT / "scripts" / "pi_v1_controller_bridge.py").read_text()
        self.assertNotIn('operation="skills.register"', terminal)
        self.assertNotIn("UnixAdminServer", admin_server)
        self.assertIn('operation="skills.register"', bridge)
        self.assertIn("AdminRequest.create", bridge)
        self.assertIn("AdminService", bridge)
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
