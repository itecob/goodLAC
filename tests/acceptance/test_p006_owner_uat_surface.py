import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class P006OwnerUATSurfaceTests(unittest.TestCase):
    def test_owner_tour_exposes_required_operator_commands(self):
        text = (ROOT / "scripts" / "lac-owner-tour").read_text(encoding="utf-8")
        for command in (
            "overview",
            "evidence",
            "agent",
            "agent-results",
            "permissions",
            "security",
            "stress",
            "regression",
        ):
            self.assertIn(command, text)
        self.assertIn("a004_terminal.py", text)
        self.assertIn("p006_owner_permission_demo.py", text)
        self.assertIn("tests.adversarial.test_h004_phase2_bypass", text)
        self.assertIn("tests.integration.test_a003_agent_process_sandbox", text)
        self.assertNotIn("calendar.google", text.lower())
        self.assertNotIn("gmail.google", text.lower())

    def test_permission_demo_is_synthetic_persists_requests_and_exercises_policy_modes(self):
        text = (ROOT / "scripts" / "p006_owner_permission_demo.py").read_text(encoding="utf-8")
        for token in (
            "SafeAdapter",
            "EffectRequestRepository(self.store).put(effect)",
            "DispatchCapabilityDenied",
            "DispatchApprovalRequired",
            "DispatchDuplicateEffect",
            "StandingPolicyCondition",
            "KNOWN_UNCONFIGURED_DISCOVERY_REQUIREMENT",
            "P003_CONFIGURED_DENY=PASS",
            "P003_CONDITIONAL_ALLOW_IF=PASS",
            "pending",
            "permissions",
            "approvals",
        ):
            self.assertIn(token, text)
        for forbidden in ("googleapis", "calendar.google", "gmail.googleapis", "requests.", "urllib.request"):
            self.assertNotIn(forbidden, text.lower())

    def test_completed_uat_retains_deterministic_adversarial_gate_not_model_refusal(self):
        guide = (ROOT / "docs" / "P006_OWNER_UAT_OPERATOR_GUIDE.md").read_text(encoding="utf-8")
        evidence = json.loads(
            (ROOT / "qualification" / "evidence" / "p006_uat_owner_execution.json").read_text(
                encoding="utf-8"
            )
        )
        lowered = guide.lower()
        self.assertIn("deterministic hostile-request matrix", lowered)
        self.assertIn("a refusal from a language model is not counted as security evidence", lowered)
        self.assertIn("explicit denial", lowered)
        self.assertIn("conditional", lowered)
        self.assertEqual(evidence["completed_task"], "LAC-P006-UAT")
        self.assertEqual(evidence["owner_visible_adversarial_stress"], "PASS")
        self.assertEqual(evidence["accepted_deterministic_regression"], "PASS")
        self.assertEqual(evidence["result"], "PASS")

    def test_owner_regression_command_supplies_required_run_root(self):
        text = (ROOT / "scripts" / "lac-owner-tour").read_text(encoding="utf-8")
        self.assertIn('export LAC_P006_RUN_ROOT="$UAT_ROOT/regression"', text)
        self.assertIn("tests.acceptance.test_p006_first_use_permission_discovery", text)


if __name__ == "__main__":
    unittest.main()
