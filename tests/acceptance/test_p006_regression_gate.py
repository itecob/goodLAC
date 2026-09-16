import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class P006RegressionGateDeterminismTests(unittest.TestCase):
    def test_current_accepted_a003_a004_live_evidence_is_valid(self):
        proc = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "verify_accepted_live_evidence.py"), "--scope", "all"],
            cwd=ROOT,
            text=True,
            capture_output=True,
            timeout=20,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
        self.assertIn("LAC_A003_ACCEPTED_LIVE_EVIDENCE=PASS", proc.stdout)
        self.assertIn("LAC_A004_ACCEPTED_LIVE_EVIDENCE=PASS", proc.stdout)
        self.assertIn("LAC_ACCEPTED_LIVE_EVIDENCE_VERIFY=PASS", proc.stdout)

    def test_p006_selects_deterministic_prior_live_evidence_regression_mode(self):
        source = (ROOT / "scripts" / "test-p006").read_text(encoding="utf-8")
        self.assertIn("LAC_A003_REGRESSION_MODE=accepted-evidence", source)
        self.assertIn("LAC_A004_REGRESSION_MODE=accepted-evidence", source)
        self.assertNotIn("retrying", source.lower())

    def test_direct_a003_a004_gates_preserve_live_as_default(self):
        a003 = (ROOT / "scripts" / "test-a003").read_text(encoding="utf-8")
        a004 = (ROOT / "scripts" / "test-a004").read_text(encoding="utf-8")
        self.assertIn('${LAC_A003_REGRESSION_MODE:=live}', a003)
        self.assertIn('${LAC_A004_REGRESSION_MODE:=live}', a004)
        self.assertIn('if [[ "$LAC_A003_REGRESSION_MODE" == "live" ]]', a003)
        self.assertIn('if [[ "$LAC_A004_REGRESSION_MODE" == "live" ]]', a004)
        self.assertIn("a003_agent_sandbox.py qualification", a003)
        self.assertIn("a004_freetoken_launcher.py run -- scripts/a004-live-gate", a004)


if __name__ == "__main__":
    unittest.main()
