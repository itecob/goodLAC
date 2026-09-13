import json
import unittest
from pathlib import Path

from packages.sandbox import get_selected_backend


class H001SandboxEvidenceIntegrationTests(unittest.TestCase):
    def test_installed_qualification_evidence_selects_live_backend(self):
        root = Path(__file__).resolve().parents[2]
        evidence_path = root / "qualification" / "evidence" / "h001_sandbox.json"
        payload = json.loads(evidence_path.read_text(encoding="utf-8"))
        self.assertEqual(payload["schema"], "lac.sandbox-qualification/v1")
        self.assertEqual(payload["status"], "PASS")
        self.assertIn(payload["selected_backend"], ("bubblewrap", "rootless_podman"))
        selected = payload["candidates"][payload["selected_backend"]]
        self.assertEqual(selected["status"], "PASS")
        self.assertEqual(selected["disposition"], "SELECTED")
        for control in (
            "filesystem_visibility",
            "writable_paths",
            "process_isolation",
            "outbound_network",
            "environment_inheritance",
            "credential_exposure",
            "child_process_containment",
            "rootless_user_namespace",
            "lifecycle_cleanup",
            "failure_mode",
        ):
            self.assertIs(selected["controls"][control], True, control)
        backend = get_selected_backend()
        self.assertEqual(backend.backend_id, payload["selected_backend"])
        self.assertTrue(backend.binary.is_file())


if __name__ == "__main__":
    unittest.main()
