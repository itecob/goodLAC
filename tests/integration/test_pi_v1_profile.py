from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class PiV1ProductionProfileIntegrationTests(unittest.TestCase):
    def test_real_pinned_pi_uses_permission_continuation_and_sandbox(self):
        with tempfile.TemporaryDirectory(prefix="lac-pi-d001-profile-") as t:
            root = Path(t)
            runtime = root / "runtime"
            runtime.mkdir(mode=0o700)
            workspace = root / "workspace"
            workspace.mkdir()
            state = root / "controller.db"
            trace = root / "trace.jsonl"
            env = dict(os.environ)
            env["XDG_RUNTIME_DIR"] = str(runtime)
            env["LAC_A004_SYNTHETIC_SERVICE_CREDENTIAL"] = (
                "PI-D001-HOST-SECRET-MUST-NOT-INHERIT"
            )
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "pi_v1_terminal.py"),
                    "--profile-probe",
                    "--workspace",
                    str(workspace),
                    "--state",
                    str(state),
                    "--trace",
                    str(trace),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                timeout=120,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout)
            for marker in (
                "LAC_PI001_PROFILE_PROBE=PASS",
                "LAC_PI002_D001_REAL_PI_SUSPENSION_BEFORE_MODEL_CONTINUATION=PASS",
                "LAC_PI002_D001_ORIGINAL_REQUEST_TERMINAL=PASS",
                "LAC_PI002_D001_ONE_FRESH_REQUEST=PASS",
                "pi_agent_core=0.85.1",
                "sandbox=bubblewrap network=none",
                "standalone_pi=separate_and_not_claimed_as_lac_governed",
            ):
                self.assertIn(marker, proc.stdout)
            self.assertEqual(
                (workspace / "pi-d001-continued.txt").read_text(),
                "pi-d001-fresh-continuation",
            )
            canary = "PI-D001-HOST-SECRET-MUST-NOT-INHERIT"
            self.assertNotIn(canary, trace.read_text())
            self.assertNotIn(canary.encode(), state.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
