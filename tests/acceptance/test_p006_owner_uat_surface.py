import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class P006OwnerUATSurfaceTests(unittest.TestCase):
    def test_owner_tour_exposes_required_operator_commands(self):
        text = (ROOT / "scripts" / "lac-owner-tour").read_text(encoding="utf-8")
        for command in ("overview", "evidence", "agent", "agent-results", "permissions", "security", "regression"):
            self.assertIn(command, text)
        self.assertIn("a004_terminal.py", text)
        self.assertIn("p006_owner_permission_demo.py", text)
        self.assertNotIn("calendar", text.lower())
        self.assertNotIn("gmail.google", text.lower())

    def test_permission_demo_is_synthetic_and_tests_clarified_gap(self):
        text = (ROOT / "scripts" / "p006_owner_permission_demo.py").read_text(encoding="utf-8")
        for token in (
            "SafeAdapter",
            "DispatchCapabilityDenied",
            "DispatchApprovalRequired",
            "DispatchDuplicateEffect",
            "KNOWN_UNCONFIGURED_DISCOVERY_REQUIREMENT",
            "pending",
            "permissions",
            "approvals",
        ):
            self.assertIn(token, text)
        for forbidden in ("googleapis", "calendar.google", "gmail.googleapis", "requests.", "urllib.request"):
            self.assertNotIn(forbidden, text.lower())


if __name__ == "__main__":
    unittest.main()
