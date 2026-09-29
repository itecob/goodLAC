from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from packages.admin import AdminRequest, AdminService
from packages.adapters.pi.production import (
    PI_V1_AGENT_ID,
    PI_V1_CAPABILITY_MANIFEST,
    PI_V1_PRINCIPAL_ID,
    PiPermissionRuntime,
)
from packages.capabilities import CapabilityManifest
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.state import AgentIdentityRepository, EmergencyPauseRepository, SQLiteStateStore
from scripts import pi_native_tui_host as native


class PostV1R5R003Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="goodlac-r5-r003-")
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.store = SQLiteStateStore(self.root / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active(
            PI_V1_AGENT_ID, PI_V1_PRINCIPAL_ID
        )
        self.admin = AdminService(self.store, owner_uid=os.getuid())
        self.runtime = PiPermissionRuntime(
            store=self.store,
            filesystem_adapter=FilesystemEffectAdapter(self.workspace),
            shell_adapter=ShellEffectAdapter(
                self.workspace,
                allowed_executables=(Path("/usr/bin/printf"), Path("/usr/bin/true")),
            ),
            run_id="run:r5:r003",
        )
        manifest = CapabilityManifest.create(PI_V1_CAPABILITY_MANIFEST)
        self.call("skills.register", {"manifest": json.loads(manifest.canonical_json())})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def call(self, operation, arguments):
        return self.admin.execute(
            AdminRequest.create(
                request_id=f"admin:r5:r003:{operation}:{os.urandom(5).hex()}",
                operation=operation,
                arguments=arguments,
            ),
            peer_uid=os.getuid(),
        )

    def shell(self, call_id, executable="/usr/bin/printf", argv=None):
        return {
            "toolCallId": call_id,
            "toolName": "lac_shell_exec",
            "arguments": {
                "executable": executable,
                "argv": ["scope-test"] if argv is None else list(argv),
                "cwd": ".",
                "environment": {},
            },
        }

    def block(self, message):
        result = self.runtime.submit_message(message)
        self.assertEqual((result["authority_outcome"], result["execution_state"]), ("DENY", "DENIED"))
        status = result["workflow_continuation"]
        self.assertEqual(status["state"], "WAITING_PERMISSION")
        return status

    def decide(self, status, choice, scope):
        return self.call(
            "permissions.decide",
            {
                "continuation_id": status["continuation_id"],
                "pending_id": status["pending_id"],
                "choice": choice,
                "scope": scope,
            },
        )

    def resume(self, status, message):
        return self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]

    def test_shell_exact_command_scope_does_not_broaden_argv(self):
        first = self.shell("exact-a", argv=["A"])
        status = self.block(first)
        chosen = self.decide(status, "ALWAYS_ALLOW", "SHELL_COMMAND")
        self.assertEqual(chosen["policy"]["permission_scope"], "SHELL_COMMAND")
        self.assertEqual(self.resume(status, first)["execution_state"], "SUCCEEDED")

        same = self.runtime.submit_message(self.shell("exact-b", argv=["A"]))
        self.assertEqual(same["execution_state"], "SUCCEEDED")

        changed = self.runtime.submit_message(self.shell("exact-c", argv=["B"]))
        self.assertEqual((changed["authority_outcome"], changed["execution_state"]), ("DENY", "DENIED"))
        self.assertTrue(changed["permission_configuration"]["required"])

    def test_shell_executable_scope_allows_same_binary_but_not_other_binary(self):
        first = self.shell("exe-a", argv=["A"])
        status = self.block(first)
        chosen = self.decide(status, "ALWAYS_ALLOW", "SHELL_EXECUTABLE")
        self.assertEqual(chosen["policy"]["permission_scope"], "SHELL_EXECUTABLE")
        self.assertEqual(self.resume(status, first)["execution_state"], "SUCCEEDED")

        same_binary = self.runtime.submit_message(self.shell("exe-b", argv=["different"]))
        self.assertEqual(same_binary["execution_state"], "SUCCEEDED")

        other = self.runtime.submit_message(self.shell("exe-c", executable="/usr/bin/true", argv=[]))
        self.assertEqual((other["authority_outcome"], other["execution_state"]), ("DENY", "DENIED"))
        self.assertTrue(other["permission_configuration"]["required"])

    def test_resource_scope_retains_all_shell_in_project_semantics(self):
        first = self.shell("resource-a")
        status = self.block(first)
        self.decide(status, "ALWAYS_ALLOW", "RESOURCE")
        self.assertEqual(self.resume(status, first)["execution_state"], "SUCCEEDED")
        other = self.runtime.submit_message(self.shell("resource-b", executable="/usr/bin/true", argv=[]))
        self.assertEqual(other["execution_state"], "SUCCEEDED")

    def test_one_time_choice_rejects_standing_shell_scope(self):
        status = self.block(self.shell("once-a"))
        with self.assertRaises(Exception):
            self.decide(status, "ALLOW_ONCE", "SHELL_EXECUTABLE")

    def test_model_catalog_exposes_gpt_and_qwen_and_unknown_model_fails_closed(self):
        catalog = native.model_catalog()
        ids = {item["id"] for item in catalog}
        self.assertIn("lac-a003-gpt-oss-20b", ids)
        self.assertIn("goodlac-exp-qwen36-35b-a3b-nvfp4", ids)
        self.assertEqual(
            native._model_route({"model": "goodlac-exp-qwen36-35b-a3b-nvfp4"})["base_url"],
            "http://127.0.0.1:19360",
        )
        with self.assertRaises(Exception):
            native._model_route({"model": "not-owner-allowlisted"})


if __name__ == "__main__":
    unittest.main(verbosity=2)
