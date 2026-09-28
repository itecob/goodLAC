from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from packages.admin import (
    AdminRequest,
    AdminService,
    ensure_admin_control_plane,
    probe_admin_control_plane,
    stop_owned_admin_control_plane,
)
from packages.adapters.pi.production import (
    PI_V1_SKILL_ID,
    PiPermissionRuntime,
    pi_v1_project_application_id,
)
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.policy import StandingPolicyRule
from packages.state import SQLiteStateStore
from scripts.pi_v1_controller_bridge import canonical_binary, initialize_state

ROOT = Path(__file__).resolve().parents[2]
HOST = ROOT / "scripts" / "pi_native_tui_host.py"
HARNESS = ROOT / "scripts" / "post-v1-r5-admin-harness"


class R5R001MultiPiControlPlaneTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="goodlac-r5-r001-")
        self.root = Path(self.tmp.name)
        self.runtime = self.root / "runtime"
        self.runtime.mkdir(mode=0o700)
        self.state = self.root / "controller.db"
        self.trace = self.root / "trace.jsonl"
        self.a = self.root / "project-a"
        self.b = self.root / "project-b"
        self.a.mkdir()
        self.b.mkdir()
        self.env = dict(os.environ)
        self.env["XDG_RUNTIME_DIR"] = str(self.runtime)
        self.patch = mock.patch.dict(os.environ, {"XDG_RUNTIME_DIR": str(self.runtime)})
        self.patch.start()
        initialize_state(self.state, self.a)
        initialize_state(self.state, self.b)
        self.lease = ensure_admin_control_plane(self.state, repo_root=ROOT)

    def tearDown(self):
        try:
            stop_owned_admin_control_plane(self.lease)
        finally:
            self.patch.stop()
            self.tmp.cleanup()

    def _runtime(self, workspace: Path, run_id: str):
        store = SQLiteStateStore(self.state)
        runtime = PiPermissionRuntime(
            store=store,
            filesystem_adapter=FilesystemEffectAdapter(workspace),
            shell_adapter=ShellEffectAdapter(
                workspace,
                allowed_executables=(
                    canonical_binary("ls"),
                    canonical_binary("cat"),
                    canonical_binary("printf"),
                ),
            ),
            run_id=run_id,
            application_id=pi_v1_project_application_id(workspace),
        )
        return store, runtime

    def _replace_allow_rules(self, workspaces: list[Path]) -> None:
        with SQLiteStateStore(self.state) as store:
            service = AdminService(store, owner_uid=os.getuid())
            rules = [
                StandingPolicyRule.create(
                    rule_id=f"r5-r001-allow-{index}",
                    application_id=pi_v1_project_application_id(workspace),
                    skill_id=PI_V1_SKILL_ID,
                    action="filesystem.create",
                    resource_selector="filesystem:workspace",
                    decision="ALLOW",
                ).to_material()
                for index, workspace in enumerate(workspaces)
            ]
            service.execute(
                AdminRequest.create(
                    request_id="admin:r5-r001:replace-rules",
                    operation="permissions.replace",
                    arguments={"rules": rules, "defaults": []},
                ),
                peer_uid=os.getuid(),
            )

    def test_two_native_hosts_attach_to_one_plane_and_one_exit_leaves_other_operational(self):
        procs: list[subprocess.Popen[str]] = []
        try:
            for workspace in (self.a, self.b):
                proc = subprocess.Popen(
                    [
                        sys.executable,
                        str(HOST),
                        "--workspace",
                        str(workspace),
                        "--state",
                        str(self.state),
                        "--trace",
                        str(self.trace),
                        "--runtime",
                        "external",
                        "--control-plane-attach-probe-seconds",
                        "8",
                    ],
                    cwd=ROOT,
                    env=self.env,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                )
                procs.append(proc)

            rows = []
            for proc in procs:
                assert proc.stdout is not None and proc.stderr is not None
                line = proc.stdout.readline()
                if not line:
                    self.fail(proc.stderr.read())
                rows.append(json.loads(line))

            self.assertNotEqual(rows[0]["application_id"], rows[1]["application_id"])
            self.assertEqual(rows[0]["control_plane_pid"], rows[1]["control_plane_pid"])
            self.assertEqual(rows[0]["control_plane_pid"], probe_admin_control_plane(self.state)["pid"])

            procs[0].terminate()
            procs[0].communicate(timeout=5)
            self.assertIsNone(procs[1].poll())
            self.assertEqual(probe_admin_control_plane(self.state)["pid"], rows[1]["control_plane_pid"])
        finally:
            for proc in procs:
                if proc.poll() is None:
                    proc.terminate()
                try:
                    proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.communicate(timeout=5)

    def test_both_projects_can_independently_execute_and_a_policy_cannot_authorize_b(self):
        self._replace_allow_rules([self.a])
        store_a, runtime_a = self._runtime(self.a, "run:r5:a")
        store_b, runtime_b = self._runtime(self.b, "run:r5:b")
        try:
            allowed = runtime_a.submit_message(
                {
                    "toolCallId": "r5-a",
                    "toolName": "lac_fs_create",
                    "arguments": {"path": "a.txt", "content": "A"},
                }
            )
            denied = runtime_b.submit_message(
                {
                    "toolCallId": "r5-b-denied",
                    "toolName": "lac_fs_create",
                    "arguments": {"path": "b.txt", "content": "B"},
                }
            )
            self.assertEqual(allowed.get("execution_state"), "SUCCEEDED")
            self.assertTrue((self.a / "a.txt").is_file())
            self.assertFalse((self.b / "b.txt").exists())
            self.assertNotEqual(denied.get("authority_outcome"), "ALLOW")
        finally:
            store_a.close()
            store_b.close()

        self._replace_allow_rules([self.a, self.b])
        store_b, runtime_b = self._runtime(self.b, "run:r5:b-allowed")
        try:
            allowed_b = runtime_b.submit_message(
                {
                    "toolCallId": "r5-b-allowed",
                    "toolName": "lac_fs_create",
                    "arguments": {"path": "b.txt", "content": "B"},
                }
            )
            self.assertEqual(allowed_b.get("execution_state"), "SUCCEEDED")
            self.assertEqual((self.b / "b.txt").read_text(), "B")
        finally:
            store_b.close()

    def test_shared_emergency_pause_blocks_both_and_resume_dispatches_neither(self):
        self._replace_allow_rules([self.a, self.b])
        with SQLiteStateStore(self.state) as store:
            AdminService(store, owner_uid=os.getuid()).execute(
                AdminRequest.create(
                    request_id="admin:r5-r001:pause",
                    operation="emergency.pause",
                    arguments={},
                ),
                peer_uid=os.getuid(),
            )

        for workspace, call_id in ((self.a, "paused-a"), (self.b, "paused-b")):
            store, runtime = self._runtime(workspace, f"run:{call_id}")
            try:
                result = runtime.submit_message(
                    {
                        "toolCallId": call_id,
                        "toolName": "lac_fs_create",
                        "arguments": {"path": f"{call_id}.txt", "content": call_id},
                    }
                )
                self.assertNotEqual(result.get("execution_state"), "SUCCEEDED")
                self.assertFalse((workspace / f"{call_id}.txt").exists())
            finally:
                store.close()

        with SQLiteStateStore(self.state) as store:
            AdminService(store, owner_uid=os.getuid()).execute(
                AdminRequest.create(
                    request_id="admin:r5-r001:resume",
                    operation="emergency.resume",
                    arguments={},
                ),
                peer_uid=os.getuid(),
            )
        self.assertFalse((self.a / "paused-a.txt").exists())
        self.assertFalse((self.b / "paused-b.txt").exists())

    def test_shared_service_restart_preserves_state_and_auto_dispatches_nothing(self):
        original_pid = probe_admin_control_plane(self.state)["pid"]
        self._replace_allow_rules([self.a])
        self.assertTrue(stop_owned_admin_control_plane(self.lease))
        self.assertFalse((self.a / "restart-must-not-exist.txt").exists())

        replacement = ensure_admin_control_plane(self.state, repo_root=ROOT)
        self.lease = replacement
        status = probe_admin_control_plane(self.state)
        self.assertNotEqual(status["pid"], original_pid)
        self.assertEqual(status["state_path"], str(self.state.resolve()))
        self.assertFalse((self.a / "restart-must-not-exist.txt").exists())

        store_a, runtime_a = self._runtime(self.a, "run:r5:after-restart")
        try:
            result = runtime_a.submit_message(
                {
                    "toolCallId": "after-restart",
                    "toolName": "lac_fs_create",
                    "arguments": {"path": "after.txt", "content": "after"},
                }
            )
            self.assertEqual(result.get("execution_state"), "SUCCEEDED")
        finally:
            store_a.close()

    def test_missing_shared_plane_is_checked_before_effect_and_resume_paths(self):
        terminal = (ROOT / "scripts" / "pi_v1_terminal.py").read_text()
        native = (ROOT / "scripts" / "pi_native_tui_host.py").read_text()
        self.assertIn("def _effect(self, payload):\n        probe_admin_control_plane(self.state)", terminal)
        self.assertIn("def _resume_once(self, continuation_id, *, expected_message=None):\n        probe_admin_control_plane(self.state)", terminal)
        self.assertIn("def _effect(self, payload):\n        legacy.probe_admin_control_plane(self.state)", native)

    def test_r5_harness_separates_start_from_json_capture_and_never_unlinks(self):
        source = HARNESS.read_text()
        self.assertIn("ADMIN_PID=$!", source)
        self.assertIn("admin_start()", source)
        self.assertIn("admin_json()", source)
        self.assertNotIn("admin_start\n", source[source.index("admin_json()"):])
        self.assertNotIn("\nunlink ", source)
        self.assertNotIn("rm -f -- \"$XDG_RUNTIME_DIR", source)
        self.assertNotIn("admin-v1.sock", source)


if __name__ == "__main__":
    unittest.main(verbosity=2)
