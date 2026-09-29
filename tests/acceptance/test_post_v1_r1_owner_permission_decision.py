from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from packages.admin import AdminConflict, AdminRequest, AdminService
from packages.adapters.pi.production import (
    PI_V1_AGENT_ID,
    PI_V1_CAPABILITY_MANIFEST,
    PI_V1_PRINCIPAL_ID,
    PiPermissionRuntime,
)
from packages.capabilities import CapabilityManifest, PendingPermissionRepository
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.state import AgentIdentityRepository, EmergencyPauseRepository, SQLiteStateStore


class PostV1R1OwnerPermissionDecisionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="goodlac-post-v1-r1-")
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "workspace"
        self.workspace.mkdir()
        self.store = SQLiteStateStore(self.root / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active(
            PI_V1_AGENT_ID, PI_V1_PRINCIPAL_ID
        )
        self.admin = AdminService(self.store, owner_uid=os.getuid())
        self.fs = FilesystemEffectAdapter(self.workspace)
        self.shell = ShellEffectAdapter(
            self.workspace, allowed_executables=(Path("/usr/bin/printf"),)
        )
        self.runtime = PiPermissionRuntime(
            store=self.store,
            filesystem_adapter=self.fs,
            shell_adapter=self.shell,
            run_id="run:post-v1:r1",
        )
        manifest = CapabilityManifest.create(PI_V1_CAPABILITY_MANIFEST)
        self.call("skills.register", {"manifest": json.loads(manifest.canonical_json())})

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def call(self, operation, arguments):
        return self.admin.execute(
            AdminRequest.create(
                request_id=f"admin:r1:{operation}:{os.urandom(5).hex()}",
                operation=operation,
                arguments=arguments,
            ),
            peer_uid=os.getuid(),
        )

    def message(self, call_id, path):
        return {
            "toolCallId": call_id,
            "toolName": "lac_fs_create",
            "arguments": {"path": path, "content": call_id},
        }

    def block(self, call_id, path):
        message = self.message(call_id, path)
        result = self.runtime.submit_message(message)
        self.assertEqual(result["authority_outcome"], "DENY")
        self.assertEqual(result["execution_state"], "DENIED")
        self.assertTrue(result["permission_configuration"]["required"])
        status = result["workflow_continuation"]
        self.assertEqual(status["state"], "WAITING_PERMISSION")
        self.assertFalse((self.workspace / path).exists())
        return message, result, status

    def decide(self, status, choice):
        return self.call(
            "permissions.decide",
            {
                "continuation_id": status["continuation_id"],
                "pending_id": status["pending_id"],
                "choice": choice,
                "scope": "RESOURCE",
            },
        )

    def approve(self, decision_id):
        return self.call("approvals.approve", {"decision_id": decision_id})

    def reject(self, decision_id):
        return self.call("approvals.reject", {"decision_id": decision_id})

    def test_allow_once_uses_exact_transient_approval_rule_and_future_requests_return_to_first_use(self):
        message, blocked, status = self.block("allow-once-a", "allow-once-a.txt")
        original = blocked["request_id"]
        choice = self.decide(status, "ALLOW_ONCE")
        self.assertEqual(choice["policy"]["decision"], "REQUIRE_APPROVAL")
        self.assertIs(choice["policy"]["transient_exact_request"], True)
        self.assertTrue(choice["policy"]["rule_id"].startswith("owner-permission:allow-once:"))
        self.assertEqual(choice["next_action"], "RESUME_THEN_APPROVE_EXACT")
        self.assertEqual(choice["subject"]["resource"], "filesystem:workspace")

        pending = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(
            (pending["authority_outcome"], pending["execution_state"]),
            ("REQUIRE_APPROVAL", "PENDING_APPROVAL"),
        )
        self.assertNotEqual(pending["request_id"], original)
        self.assertFalse((self.workspace / "allow-once-a.txt").exists())
        self.approve(pending["decision_id"])
        executed = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(executed["execution_state"], "SUCCEEDED")
        self.assertEqual((self.workspace / "allow-once-a.txt").read_text(), "allow-once-a")
        self.assertIsNotNone(PendingPermissionRepository(self.store).get_closure(original))

        later = self.runtime.submit_message(self.message("allow-once-b", "allow-once-b.txt"))
        self.assertEqual((later["authority_outcome"], later["execution_state"]), ("DENY", "DENIED"))
        self.assertTrue(later["permission_configuration"]["required"])
        self.assertEqual(later["workflow_continuation"]["state"], "WAITING_PERMISSION")
        self.assertFalse((self.workspace / "allow-once-b.txt").exists())

    def test_always_allow_continues_current_and_later_matching_requests_without_prompt(self):
        message, _blocked, status = self.block("always-a", "always-a.txt")
        choice = self.decide(status, "ALWAYS_ALLOW")
        self.assertEqual(choice["policy"]["decision"], "ALLOW")
        result = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual((result["authority_outcome"], result["execution_state"]), ("ALLOW", "SUCCEEDED"))
        later = self.runtime.submit_message(self.message("always-b", "always-b.txt"))
        self.assertEqual((later["authority_outcome"], later["execution_state"]), ("ALLOW", "SUCCEEDED"))

    def test_ask_every_time_requires_fresh_exact_owner_decision_each_time(self):
        message, _blocked, status = self.block("ask-a", "ask-a.txt")
        choice = self.decide(status, "ASK_EVERY_TIME")
        self.assertEqual(choice["policy"]["decision"], "REQUIRE_APPROVAL")
        first = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(first["execution_state"], "PENDING_APPROVAL")
        self.assertFalse((self.workspace / "ask-a.txt").exists())
        self.approve(first["decision_id"])
        executed = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(executed["execution_state"], "SUCCEEDED")

        second = self.runtime.submit_message(self.message("ask-b", "ask-b.txt"))
        self.assertEqual(second["execution_state"], "PENDING_APPROVAL")
        self.assertNotEqual(second["decision_id"], first["decision_id"])
        self.assertFalse((self.workspace / "ask-b.txt").exists())

    def test_deny_once_closes_only_exact_continuation_and_equivalent_request_can_ask_again(self):
        first_message, _first, first = self.block("deny-once-a", "deny-once-a.txt")
        second_message, _second, second = self.block("deny-once-b", "deny-once-b.txt")
        self.assertEqual(first["pending_id"], second["pending_id"])
        self.assertNotEqual(first["continuation_id"], second["continuation_id"])

        choice = self.decide(first, "DENY_ONCE")
        self.assertIsNone(choice["policy"])
        self.assertIsNone(choice["pending_resolution"])
        self.assertEqual(choice["continuation"]["state"], "CLOSED_NONAUTH")
        first_outcome = self.runtime.resume_continuation(
            first["continuation_id"], expected_message=first_message
        )
        self.assertEqual(first_outcome["kind"], "CLOSED_NONAUTH")
        self.assertEqual(first_outcome["workflow_continuation"]["resume_budget_used"], 0)
        self.assertFalse((self.workspace / "deny-once-a.txt").exists())

        second_wait = self.runtime.resume_continuation(
            second["continuation_id"], expected_message=second_message
        )
        self.assertEqual(second_wait["kind"], "WAITING_PERMISSION")
        self.decide(second, "DENY_ONCE")
        self.assertEqual(
            self.runtime.resume_continuation(second["continuation_id"])["kind"],
            "CLOSED_NONAUTH",
        )
        third = self.runtime.submit_message(self.message("deny-once-c", "deny-once-c.txt"))
        self.assertTrue(third["permission_configuration"]["required"])
        self.assertEqual(third["workflow_continuation"]["state"], "WAITING_PERMISSION")

    def test_always_deny_denies_current_fresh_request_and_suppresses_future_discovery_noise(self):
        message, _blocked, status = self.block("deny-always-a", "deny-always-a.txt")
        choice = self.decide(status, "ALWAYS_DENY")
        self.assertEqual(choice["policy"]["decision"], "DENY")
        current = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual((current["authority_outcome"], current["execution_state"]), ("DENY", "DENIED"))
        self.assertFalse((self.workspace / "deny-always-a.txt").exists())

        before = len(PendingPermissionRepository(self.store).list_pending())
        later = self.runtime.submit_message(self.message("deny-always-b", "deny-always-b.txt"))
        after = len(PendingPermissionRepository(self.store).list_pending())
        self.assertEqual((later["authority_outcome"], later["execution_state"]), ("DENY", "DENIED"))
        self.assertFalse(later["permission_configuration"]["required"])
        self.assertEqual(before, after)

    def test_reconfigured_after_policy_revoke_records_fresh_owner_resolution_revision(self):
        message, _blocked, first = self.block("reconfigure-a", "reconfigure-a.txt")
        allowed = self.decide(first, "ALWAYS_ALLOW")
        self.runtime.resume_continuation(
            first["continuation_id"], expected_message=message
        )
        self.call("permissions.revoke", {"kind": "RULE", "id": allowed["policy"]["rule_id"]})

        _message2, _blocked2, second = self.block("reconfigure-b", "reconfigure-b.txt")
        self.assertEqual(second["pending_id"], first["pending_id"])
        self.assertEqual(second["resolution_baseline_revision"], 1)
        chosen = self.decide(second, "ALLOW_ONCE")
        self.assertEqual(chosen["pending_resolution"]["revision"], 2)
        self.assertEqual(chosen["continuation"]["owner_resolution"]["revision"], 2)

    def test_stale_or_wrong_binding_is_rejected_without_effect(self):
        _message, _blocked, status = self.block("stale", "stale.txt")
        with self.assertRaises(AdminConflict):
            self.call(
                "permissions.decide",
                {
                    "continuation_id": status["continuation_id"],
                    "pending_id": "pending:not-the-bound-item",
                    "choice": "ALWAYS_ALLOW",
                    "scope": "RESOURCE",
                },
            )
        self.call(
            "pending.resolve",
            {"pending_id": status["pending_id"], "resolution": "NO_CHANGE"},
        )
        with self.assertRaises(AdminConflict):
            self.decide(status, "ALWAYS_ALLOW")
        self.assertFalse((self.workspace / "stale.txt").exists())

    def test_allow_once_still_loses_to_emergency_pause_before_dispatch(self):
        message, _blocked, status = self.block("pause", "pause.txt")
        self.decide(status, "ALLOW_ONCE")
        pending = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.approve(pending["decision_id"])
        self.call("emergency.pause", {})
        result = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(result["authority_outcome"], "DENY")
        self.assertEqual(result["reason"], "EMERGENCY_PAUSED")
        self.assertFalse((self.workspace / "pause.txt").exists())

    def test_model_facing_runtime_has_no_owner_permission_decision_method(self):
        for name in (
            "decide_permission",
            "owner_permission_decide",
            "permissions_decide",
            "approve",
            "replace_policy",
        ):
            self.assertFalse(hasattr(self.runtime, name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
