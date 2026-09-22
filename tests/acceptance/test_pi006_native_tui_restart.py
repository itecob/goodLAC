from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from packages.productization import v1

ROOT = Path(__file__).resolve().parents[2]


class Pi006NativeTuiRestartStabilizationTests(unittest.TestCase):
    def test_native_extension_registers_namespaced_owner_recovery_commands(self):
        ext = (ROOT / "scripts/pi_native_tui.mjs").read_text(encoding="utf-8")
        for token in (
            'pi.registerCommand("lac-continuations"',
            'pi.registerCommand("lac-resume"',
            'rpc("continuation_list",{recoverable_only:true})',
            'rpc("continuation_resume",{continuation_id:continuationId})',
            'pi.on("session_start"',
            'No effect was dispatched on restart.',
            'Approval alone does not dispatch.',
        ):
            self.assertIn(token, ext)
        self.assertNotIn('pi.registerCommand("resume"', ext)

    def test_host_binds_only_bounded_continuation_owner_rpcs(self):
        host = (ROOT / "scripts/pi_native_tui_host.py").read_text(encoding="utf-8")
        for token in (
            'if kind == "continuation_list":',
            'legacy.bridge_continuation_list(self.state, recoverable_only=recoverable_only)',
            'if kind == "continuation_resume":',
            'response = self._resume_once(continuation_id)',
            '("lac-continuations", "lac-resume")',
        ):
            self.assertIn(token, host)
        self.assertIn('if tuple(value.get("tool_surface") or ()) != EXPECTED_TOOLS:', host)

    def test_interactive_native_host_has_no_idle_shutdown_but_probe_remains_bounded(self):
        host = (ROOT / "scripts/pi_native_tui_host.py").read_text(encoding="utf-8")
        self.assertIn('def _recv(self, timeout: float | None = 360.0)', host)
        self.assertIn('deadline = None if timeout is None else time.monotonic() + timeout', host)
        self.assertIn('remaining = None if deadline is None else deadline - time.monotonic()', host)
        self.assertIn('self.host_sock.settimeout(0.25 if remaining is None else min(0.25, remaining))', host)
        self.assertIn('receive_timeout = 45.0 if self.mode == "probe" else None', host)
        self.assertNotIn('receive_timeout = 45.0 if self.mode == "probe" else 3600.0', host)

    def test_ready_report_declares_owner_commands_without_new_model_tools(self):
        ext = (ROOT / "scripts/pi_native_tui.mjs").read_text(encoding="utf-8")
        self.assertIn('owner_commands:["lac-continuations","lac-resume"]', ext)
        self.assertEqual(ext.count("pi.registerTool(tool)"), 1)
        self.assertIn("createGovernedLacTools", ext)

    def test_rc7_candidate_version(self):
        self.assertEqual(v1.RELEASE_VERSION, "1.0.0-rc.7")

    def test_rc7_upgrade_and_rollback_restore_rc6_install_exactly(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw)
            home = root / "home"
            home.mkdir()
            paths = v1.paths(home)
            prior = paths["releases"] / "1.0.0-rc.6"
            (prior / "bin").mkdir(parents=True)
            for name in v1.BIN_NAMES:
                command = prior / "bin" / name
                command.write_text(f"#!/bin/sh\necho rc6-{name}\n", encoding="utf-8")
                command.chmod(0o755)
            paths["current"].parent.mkdir(parents=True, exist_ok=True)
            paths["current"].symlink_to(prior)
            paths["bin"].mkdir(parents=True, exist_ok=True)
            for name in v1.BIN_NAMES:
                (paths["bin"] / name).symlink_to(paths["current"] / "bin" / name)
            paths["config"].parent.mkdir(parents=True, exist_ok=True)
            config = v1.default_config(home)
            config["runtime"] = "external"
            paths["config"].write_text(json.dumps(config, sort_keys=True) + "\n", encoding="utf-8")
            paths["config"].chmod(0o600)
            paths["install_state"].parent.mkdir(parents=True, exist_ok=True)
            prior_state = b'{"schema":"lac.v1-install-state/v1","sentinel":"rc6-exact"}\n'
            paths["install_state"].write_bytes(prior_state)
            paths["install_state"].chmod(0o600)
            bashrc = home / ".bashrc"
            fragment = home / v1.SHELL_FRAGMENT_REL
            fragment.parent.mkdir(parents=True, exist_ok=True)
            prior_fragment = v1._shell_fragment_bytes("bash", paths["bin"] / "pi")
            fragment.write_bytes(prior_fragment)
            fragment.chmod(0o600)
            prior_bashrc = b"# rc6 owner shell\n" + v1._shell_rc_block(fragment)
            bashrc.write_bytes(prior_bashrc)
            archive = root / "rc7.tar.gz"
            with mock.patch.dict(
                os.environ,
                {"SHELL": "/bin/bash", "LAC_PI004_TARGET_SHELL": "bash"},
                clear=False,
            ):
                v1.build_distribution(ROOT, archive)
                state = v1.install_distribution(archive, home)
                self.assertEqual(state["version"], "1.0.0-rc.7")
                v1.rollback(home)
            self.assertEqual(paths["current"].resolve().name, "1.0.0-rc.6")
            self.assertEqual(paths["install_state"].read_bytes(), prior_state)
            self.assertEqual(bashrc.read_bytes(), prior_bashrc)
            self.assertEqual(fragment.read_bytes(), prior_fragment)


if __name__ == "__main__":
    unittest.main(verbosity=2)
