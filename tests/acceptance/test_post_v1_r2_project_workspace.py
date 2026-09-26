from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from packages.admin import AdminRequest, AdminService
from packages.adapters.pi.production import (
    PI_V1_AGENT_ID,
    PI_V1_PRINCIPAL_ID,
    PI_V1_SKILL_ID,
    PiPermissionRuntime,
    canonical_project_root,
    pi_v1_capability_manifest,
    pi_v1_project_application_id,
)
from packages.capabilities import CapabilityManifest
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.productization import v1
from packages.state import AgentIdentityRepository, EmergencyPauseRepository, SQLiteStateStore

ROOT = Path(__file__).resolve().parents[2]


class PostV1R2ProjectWorkspaceTests(unittest.TestCase):
    def test_project_identity_is_canonical_stable_and_distinct(self):
        with tempfile.TemporaryDirectory(prefix="goodlac-r2-project-id-") as raw:
            root = Path(raw)
            a = root / "a"; b = root / "b"; a.mkdir(); b.mkdir()
            alias = root / "alias"; alias.symlink_to(a, target_is_directory=True)
            self.assertEqual(canonical_project_root(alias), a.resolve())
            self.assertEqual(pi_v1_project_application_id(alias), pi_v1_project_application_id(a))
            self.assertNotEqual(pi_v1_project_application_id(a), pi_v1_project_application_id(b))
            missing = root / "missing"
            with self.assertRaises(Exception):
                canonical_project_root(missing)
            file_path = root / "file"; file_path.write_text("x")
            with self.assertRaises(Exception):
                canonical_project_root(file_path)

    def test_launcher_precedence_explicit_then_fixed_then_launch_cwd_without_config_mutation(self):
        with tempfile.TemporaryDirectory(prefix="goodlac-r2-launch-") as raw:
            root = Path(raw)
            cwd = root / "cwd"; fixed = root / "fixed"; explicit = root / "explicit"
            for p in (cwd, fixed, explicit): p.mkdir()
            config = {
                "schema": v1.CONFIG_SCHEMA,
                "workspace": str(fixed),
                "workspace_mode": "launch-cwd",
                "state": str(root / "state.db"),
                "trace": str(root / "trace.jsonl"),
                "pi_checkout": str(root / "pi"),
                "runtime": "external",
            }
            old = Path.cwd()
            try:
                os.chdir(cwd)
                selected, forwarded = v1._select_governed_workspace(config, ["--profile-probe"])
                self.assertEqual(selected, cwd.resolve())
                self.assertEqual(forwarded, ["--profile-probe"])
                config["workspace_mode"] = "fixed"
                selected, _ = v1._select_governed_workspace(config, [])
                self.assertEqual(selected, fixed.resolve())
                selected, forwarded = v1._select_governed_workspace(config, ["--workspace", str(explicit), "--profile-probe"])
                self.assertEqual(selected, explicit.resolve())
                self.assertEqual(forwarded, ["--profile-probe"])
            finally:
                os.chdir(old)

    def test_legacy_config_loads_as_launch_cwd_without_rewrite(self):
        with tempfile.TemporaryDirectory(prefix="goodlac-r2-config-") as raw:
            home = Path(raw) / "home"; home.mkdir()
            p = v1.paths(home); p["config"].parent.mkdir(parents=True)
            legacy = v1.default_config(home); legacy.pop("workspace_mode")
            original = (json.dumps(legacy, sort_keys=True) + "\n").encode()
            p["config"].write_bytes(original); p["config"].chmod(0o600)
            loaded = v1.load_config(home)
            self.assertEqual(loaded["workspace_mode"], "launch-cwd")
            self.assertEqual(p["config"].read_bytes(), original)

    def test_project_a_always_allow_does_not_authorize_project_b_and_r1_continues(self):
        with tempfile.TemporaryDirectory(prefix="goodlac-r2-scope-") as raw:
            root = Path(raw); a = root / "a"; b = root / "b"; a.mkdir(); b.mkdir()
            state = root / "controller.db"
            store = SQLiteStateStore(state)
            try:
                EmergencyPauseRepository(store).resume()
                AgentIdentityRepository(store).register_active(PI_V1_AGENT_ID, PI_V1_PRINCIPAL_ID)
                admin = AdminService(store, owner_uid=os.getuid())
                app_a = pi_v1_project_application_id(a); app_b = pi_v1_project_application_id(b)
                for app in (app_a, app_b):
                    manifest = CapabilityManifest.create(pi_v1_capability_manifest(app))
                    admin.execute(AdminRequest.create(
                        request_id=f"admin:r2:register:{app.rsplit('.',1)[-1]}", operation="skills.register",
                        arguments={"manifest": json.loads(manifest.canonical_json())}), peer_uid=os.getuid())
                def runtime(project, app, run):
                    return PiPermissionRuntime(
                        store=store,
                        filesystem_adapter=FilesystemEffectAdapter(project),
                        shell_adapter=ShellEffectAdapter(project, allowed_executables=(Path("/usr/bin/printf"),)),
                        run_id=run,
                        application_id=app,
                    )
                ra = runtime(a, app_a, "run:r2:a")
                rb = runtime(b, app_b, "run:r2:b")
                msg = lambda call, name: {"toolCallId":call,"toolName":"lac_fs_create","arguments":{"path":name,"content":call}}
                blocked = ra.submit_message(msg("a-first", "a-first.txt"))
                status = blocked["workflow_continuation"]
                decision = admin.execute(AdminRequest.create(
                    request_id="admin:r2:always-a", operation="permissions.decide",
                    arguments={"continuation_id":status["continuation_id"],"pending_id":status["pending_id"],"choice":"ALWAYS_ALLOW","scope":"RESOURCE"}), peer_uid=os.getuid())
                self.assertEqual(decision["subject"]["application_id"], app_a)
                resumed = ra.resume_continuation(status["continuation_id"], expected_message=msg("a-first", "a-first.txt"))["result"]
                self.assertEqual((resumed["authority_outcome"], resumed["execution_state"]), ("ALLOW", "SUCCEEDED"))
                later_a = ra.submit_message(msg("a-later", "a-later.txt"))
                self.assertEqual((later_a["authority_outcome"], later_a["execution_state"]), ("ALLOW", "SUCCEEDED"))
                first_b = rb.submit_message(msg("b-first", "b-first.txt"))
                self.assertEqual((first_b["authority_outcome"], first_b["execution_state"]), ("DENY", "DENIED"))
                self.assertTrue(first_b["permission_configuration"]["required"])
                self.assertFalse((b / "b-first.txt").exists())
                with self.assertRaises(Exception):
                    rb.submit_message({**msg("b-spoof", "spoof.txt"), "project_root": str(a)})
            finally:
                store.close()

    def test_cross_project_continuation_listing_and_resume_fail_closed(self):
        with tempfile.TemporaryDirectory(prefix="goodlac-r2-continuation-") as raw:
            root = Path(raw); a = root / "a"; b = root / "b"; a.mkdir(); b.mkdir()
            state = root / "controller.db"; trace = root / "trace.jsonl"
            env = dict(os.environ); env["PYTHONDONTWRITEBYTECODE"] = "1"
            def call(args, payload=None):
                return subprocess.run([sys.executable, str(ROOT / "scripts/pi_v1_controller_bridge.py"), *args],
                    input=None if payload is None else json.dumps(payload), text=True, capture_output=True, env=env, check=False)
            # Initialize durable identity, then use the runtime-level test above to create project-specific state indirectly
            self.assertEqual(call(["init","--state",str(state),"--workspace",str(a)]).returncode, 0)
            store = SQLiteStateStore(state)
            try:
                app_a = pi_v1_project_application_id(a)
                EmergencyPauseRepository(store).resume()
                AgentIdentityRepository(store).register_active(PI_V1_AGENT_ID, PI_V1_PRINCIPAL_ID)
                admin = AdminService(store, owner_uid=os.getuid())
                manifest = CapabilityManifest.create(pi_v1_capability_manifest(app_a))
                admin.execute(AdminRequest.create(request_id="admin:r2:cont-reg",operation="skills.register",arguments={"manifest":json.loads(manifest.canonical_json())}),peer_uid=os.getuid())
                ra = PiPermissionRuntime(store=store,filesystem_adapter=FilesystemEffectAdapter(a),shell_adapter=ShellEffectAdapter(a,allowed_executables=(Path("/usr/bin/printf"),)),run_id="run:r2:cont",application_id=app_a)
                blocked = ra.submit_message({"toolCallId":"cont-a","toolName":"lac_fs_create","arguments":{"path":"cont.txt","content":"A"}})
                cid = blocked["workflow_continuation"]["continuation_id"]
            finally:
                store.close()
            a_list = call(["continuation-list","--state",str(state),"--workspace",str(a),"--recoverable-only"])
            b_list = call(["continuation-list","--state",str(state),"--workspace",str(b),"--recoverable-only"])
            self.assertEqual(a_list.returncode, 0, a_list.stderr)
            self.assertEqual(b_list.returncode, 0, b_list.stderr)
            self.assertEqual(len(json.loads(a_list.stdout)["continuations"]), 1)
            self.assertEqual(json.loads(b_list.stdout)["continuations"], [])
            wrong = call(["continuation-resume","--state",str(state),"--workspace",str(b),"--run-id","run:r2:b",cid], {})
            self.assertEqual(wrong.returncode, 0, wrong.stderr)
            material = json.loads(wrong.stdout)
            self.assertFalse(material["ok"])
            self.assertIn("different governed project", material["error"])
            self.assertFalse((b / "cont.txt").exists())

    def test_native_host_mounts_only_selected_project_read_only_and_resources_stay_disabled(self):
        host = (ROOT / "scripts/pi_native_tui_host.py").read_text(encoding="utf-8")
        self.assertIn('SandboxMount(source=workspace, target=PurePosixPath("/workspace"), writable=False)', host)
        self.assertIn('"--no-extensions", "-e", "/lac/pi_native_tui.mjs"', host)
        self.assertIn('"--no-skills"', host)
        self.assertIn('"--no-prompt-templates"', host)
        self.assertIn('"--no-themes"', host)
        self.assertIn('"--no-context-files"', host)
        self.assertIn('"--no-session"', host)
        self.assertNotIn('SandboxMount(source=Path("/")', host)


if __name__ == "__main__": unittest.main(verbosity=2)
