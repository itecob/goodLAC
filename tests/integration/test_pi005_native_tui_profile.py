from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


class Pi005NativeTuiProfileIntegrationTests(unittest.TestCase):
    def test_native_pi_cli_profile_preserves_governed_boundary(self):
        with tempfile.TemporaryDirectory(prefix="lac-pi005-profile-") as raw:
            root = Path(raw)
            workspace = root / "workspace"
            workspace.mkdir()
            (workspace / ".pi" / "extensions").mkdir(parents=True)
            (workspace / ".pi" / "extensions" / "must-not-load.mjs").write_text(
                'throw new Error("PI005_PROJECT_EXTENSION_MUST_NOT_LOAD");\n', encoding="utf-8"
            )
            (workspace / "AGENTS.md").write_text("PI005_PROJECT_CONTEXT_MUST_NOT_LOAD\n", encoding="utf-8")
            state = root / "controller.db"
            trace = root / "effect-trace.jsonl"
            runtime_dir = root / "runtime"
            runtime_dir.mkdir(mode=0o700)
            runtime_dir.chmod(0o700)
            env = dict(os.environ)
            env["PYTHONDONTWRITEBYTECODE"] = "1"
            env["LAC_PI_CHECKOUT"] = str(Path.home() / ".cache/local-agent-controller/phase0/upstream/pi")
            env["XDG_RUNTIME_DIR"] = str(runtime_dir)
            command = [
                sys.executable,
                str(ROOT / "scripts/pi_native_tui_host.py"),
                "--profile-probe",
                "--workspace", str(workspace),
                "--state", str(state),
                "--trace", str(trace),
            ]
            try:
                proc = subprocess.run(
                    command,
                    cwd=ROOT,
                    env=env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    timeout=90,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                partial = exc.stdout or ""
                if isinstance(partial, bytes):
                    partial = partial.decode("utf-8", errors="replace")
                self.fail(
                    "PI005 profile probe exceeded 90 seconds; partial output follows:\n"
                    + partial[-12000:]
                )
            self.assertEqual(proc.returncode, 0, proc.stdout)
            for marker in (
                "LAC_PI005_NATIVE_TUI_CLI=PASS",
                "LAC_PI005_RESOURCE_LOADING_CLOSED=PASS",
                "LAC_PI005_AMBIENT_BOUNDARY=PASS",
                "LAC_PI005_GOVERNED_TOOL_PATH=PASS",
                "LAC_PI005_PERMISSION_WORKFLOW_UNIQUE=PASS",
                "LAC_PI005_DUPLICATE_RECEIPT_REPLAY=PASS",
                "LAC_PI005_PROFILE_PROBE=PASS",
                "native_tui=PiSourceCLI",
                "entrypoint=/pi/packages/coding-agent/src/cli.ts",
                "sandbox=bubblewrap network=none",
                "resources=extension_discovery:off,skills:off,prompts:off,themes:off,context_files:off,sessions:off",
            ):
                self.assertIn(marker, proc.stdout)
            self.assertEqual((workspace / "pi005-native-probe.txt").read_text(encoding="utf-8"), "pi005-native-governed-tui")
            canary = "HOST-SECRET-MUST-NOT-INHERIT"
            self.assertNotIn(canary, trace.read_text(encoding="utf-8"))
            self.assertNotIn(canary.encode(), state.read_bytes())


if __name__ == "__main__":
    unittest.main(verbosity=2)
