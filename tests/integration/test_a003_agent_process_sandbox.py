import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
EXPECTED_TOOLS = ["lac_fs_read", "lac_fs_create", "lac_fs_replace", "lac_shell_exec"]


class A003PiProcessSandboxIntegrationTests(unittest.TestCase):
    def test_actual_pi_process_has_no_ambient_host_authority(self):
        with tempfile.TemporaryDirectory(prefix="lac-a003-agent-process-test-") as tmp_name:
            out = Path(tmp_name) / "agent-sandbox-evidence.json"
            env = dict(os.environ)
            env["LAC_A003_SYNTHETIC_SERVICE_CREDENTIAL"] = "HOST-LAUNCHER-SECRET-MUST-NOT-INHERIT"
            proc = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "a003_agent_sandbox.py"),
                    "conformance",
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                env=env,
                text=True,
                capture_output=True,
                timeout=60,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + "\n" + proc.stderr)
            self.assertIn("LAC_A003_AGENT_SANDBOX_CONFORMANCE=PASS", proc.stdout)
            evidence = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(evidence["schema"], "lac.a003-agent-sandbox-evidence/v1")
            self.assertEqual(evidence["result"], "PASS")
            self.assertEqual(evidence["tool_surface"], EXPECTED_TOOLS)
            probes = evidence["probes"]
            for key in (
                "host_file_readable",
                "workspace_file_readable",
                "workspace_write_effect",
                "synthetic_service_credential_inherited",
                "arbitrary_host_executable_launched",
                "loopback_connected",
                "private_network_connected",
            ):
                self.assertIs(probes[key], False, key)
            host = evidence["host_verification"]
            self.assertEqual(host["backend"], "bubblewrap")
            self.assertEqual(host["network_mode"], "none")
            self.assertEqual(host["transport"], "inherited-stdio-rpc-to-fixed-host-broker")
            self.assertIs(host["workspace_mounted_into_pi_process"], False)
            self.assertIs(host["host_loopback_connection_observed"], False)
            self.assertIs(host["arbitrary_host_process_effect_observed"], False)
            self.assertIs(host["synthetic_credential_value_observed"], False)


if __name__ == "__main__":
    unittest.main()
