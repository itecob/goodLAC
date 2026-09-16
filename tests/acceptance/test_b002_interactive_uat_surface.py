import unittest
from pathlib import Path


class B002InteractiveOwnerUATSurfaceTests(unittest.TestCase):
    def test_owner_uat_requires_interactive_human_choices_and_p004_p005_boundary(self):
        text = Path("scripts/b002_owner_permission_uat.py").read_text(encoding="utf-8")
        for token in (
            "sys.stdin.isatty()",
            "FIRST-USE POLICY PROMPT",
            "ALWAYS_ALLOW",
            "ASK_EACH_TIME",
            "NOT_NOW",
            "ALWAYS_DENY",
            "EXACT EFFECT PROMPT",
            "ALLOW_ONCE",
            "DENY_ONCE",
            'self.lacctl("permissions", "set"',
            'self.lacctl("approvals", "approve"',
            'self.lacctl("approvals", "reject"',
            "UnixAdminServer",
            "GOVERNED_CONSUMER_ADMIN_SOCKET_VISIBILITY=ABSENT",
        ):
            self.assertIn(token, text)
        self.assertNotIn("--auto", text)
        self.assertNotIn("permissions.replace_admin", text)
        self.assertNotIn("self.service.execute", text)
        self.assertIn("CREDENTIAL_CANARY_IN_DURABLE_STATE=ABSENT", text)

    def test_owner_uat_is_synthetic_and_contains_no_production_calendar_transport(self):
        text = Path("scripts/b002_owner_permission_uat.py").read_text(encoding="utf-8")
        self.assertIn("SyntheticTransport", text)
        self.assertIn("synthetic Calendar transport", text)
        self.assertIn("No production Google credential", text)
        self.assertIn("consequential external Calendar effect", text)
        self.assertIn('"production_calendar_credentials":"NONE"', text.replace(" ", ""))
        self.assertNotIn("GoogleCalendarTransportFactory", text)
        self.assertNotIn("calendar.googleapis.com", text)

if __name__ == "__main__":
    unittest.main()
