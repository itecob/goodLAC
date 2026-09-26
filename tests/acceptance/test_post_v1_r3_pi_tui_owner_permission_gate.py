from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from packages.admin import AdminRequest, AdminService
from packages.adapters.pi.production import pi_v1_capability_manifest, pi_v1_project_application_id
from packages.capabilities import CapabilityManifest, PendingPermissionRepository
from packages.state import SQLiteStateStore
from scripts import pi_v1_terminal as legacy
from scripts.pi_native_tui_host import AuthorityBroker


class PostV1R3PiTuiOwnerPermissionGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="goodlac-post-v1-r3-")
        self.root = Path(self.tmp.name)
        self.workspace = self.root / "project-a"
        self.workspace.mkdir()
        self.state = self.root / "controller.db"
        self.trace = self.root / "trace.jsonl"
        legacy.initialize_state(self.state, self.workspace)
        self.store = SQLiteStateStore(self.state)
        self.admin = AdminService(self.store, owner_uid=os.getuid())
        self.app_id = pi_v1_project_application_id(self.workspace)
        manifest = CapabilityManifest.create(pi_v1_capability_manifest(self.app_id))
        self.call("skills.register", {"manifest": json.loads(manifest.canonical_json())})
        self.broker = AuthorityBroker(
            workspace=self.workspace,
            state=self.state,
            trace=self.trace,
            mode="interactive",
        )

    def tearDown(self):
        self.broker.close_owner_gate()
        self.store.close()
        self.tmp.cleanup()

    def call(self, operation, arguments):
        return self.admin.execute(
            AdminRequest.create(
                request_id=f"admin:r3:test:{os.urandom(6).hex()}",
                operation=operation,
                arguments=arguments,
            ),
            peer_uid=os.getuid(),
        )

    def effect(self, name, content=None):
        args = {"path": name, "content": content or name}
        return self.broker.handle_rpc(
            "effect_request",
            {
                "toolCallId": f"r3-{name}-{os.urandom(3).hex()}",
                "toolName": "lac_fs_create",
                "arguments": args,
            },
        )

    def permission_gate(self, name, content=None):
        response = self.effect(name, content)
        self.assertTrue(response["ok"])
        gate = response.get("owner_gate")
        self.assertIsInstance(gate, dict)
        self.assertEqual(gate["kind"], "PERMISSION_DECISION")
        self.assertEqual(gate["project"]["application_id"], self.app_id)
        self.assertEqual(gate["project"]["path"], str(self.workspace.resolve()))
        self.assertFalse((self.workspace / name).exists())
        return gate

    def decide(self, gate, choice):
        return self.broker.handle_rpc(
            "permission_decide",
            {"challenge_id": gate["challenge_id"], "choice": choice},
        )

    def approval(self, gate, approve):
        return self.broker.handle_rpc(
            "approval_decide",
            {"challenge_id": gate["challenge_id"], "approve": approve},
        )

    def test_always_allow_is_project_bound_and_one_use(self):
        gate = self.permission_gate("always.txt")
        result = self.decide(gate, "ALWAYS_ALLOW")
        self.assertEqual(
            (result["result"]["authority_outcome"], result["result"]["execution_state"]),
            ("ALLOW", "SUCCEEDED"),
        )
        self.assertEqual((self.workspace / "always.txt").read_text(), "always.txt")
        with self.assertRaises(Exception):
            self.decide(gate, "ALWAYS_ALLOW")

        second = self.effect("always-2.txt")
        self.assertEqual(second["result"]["execution_state"], "SUCCEEDED")
        self.assertNotIn("owner_gate", second)

    def test_allow_once_auto_creates_only_fresh_exact_approval_then_future_requests_ask(self):
        gate = self.permission_gate("once.txt")
        result = self.decide(gate, "ALLOW_ONCE")
        self.assertEqual(result["result"]["execution_state"], "SUCCEEDED")
        self.assertEqual((self.workspace / "once.txt").read_text(), "once.txt")

        future = self.effect("once-future.txt")
        exact = future.get("owner_gate")
        self.assertIsInstance(exact, dict)
        self.assertEqual(exact["kind"], "EXACT_APPROVAL")
        self.assertFalse((self.workspace / "once-future.txt").exists())
        approved = self.approval(exact, True)
        self.assertEqual(approved["result"]["execution_state"], "SUCCEEDED")
        self.assertEqual((self.workspace / "once-future.txt").read_text(), "once-future.txt")

    def test_ask_every_time_uses_second_exact_owner_gate_and_rejection_dispatches_nothing(self):
        gate = self.permission_gate("ask.txt")
        response = self.decide(gate, "ASK_EVERY_TIME")
        exact = response.get("owner_gate")
        self.assertIsInstance(exact, dict)
        self.assertEqual(exact["kind"], "EXACT_APPROVAL")
        self.assertFalse((self.workspace / "ask.txt").exists())
        rejected = self.approval(exact, False)
        self.assertEqual(rejected["result"]["authority_outcome"], "DENY")
        self.assertEqual(rejected["result"]["execution_state"], "REJECTED")
        self.assertFalse((self.workspace / "ask.txt").exists())

    def test_deny_once_and_cancel_are_non_authorizing_and_do_not_create_standing_deny(self):
        first = self.permission_gate("deny-once.txt")
        denied = self.decide(first, "DENY_ONCE")
        self.assertEqual(denied["result"]["authority_outcome"], "DENY")
        self.assertFalse((self.workspace / "deny-once.txt").exists())

        second = self.permission_gate("deny-once-next.txt")
        cancelled = self.broker.handle_rpc(
            "permission_cancel",
            {"challenge_id": second["challenge_id"]},
        )
        self.assertEqual(cancelled["result"]["authority_outcome"], "DENY")
        self.assertFalse((self.workspace / "deny-once-next.txt").exists())

        third = self.permission_gate("deny-once-third.txt")
        self.assertEqual(third["kind"], "PERMISSION_DECISION")

    def test_always_deny_suppresses_future_first_use_prompt(self):
        gate = self.permission_gate("always-deny.txt")
        denied = self.decide(gate, "ALWAYS_DENY")
        self.assertEqual(denied["result"]["authority_outcome"], "DENY")
        self.assertFalse((self.workspace / "always-deny.txt").exists())
        before = len(PendingPermissionRepository(self.store).list_pending())
        later = self.effect("always-deny-next.txt")
        after = len(PendingPermissionRepository(self.store).list_pending())
        self.assertEqual(later["result"]["authority_outcome"], "DENY")
        self.assertNotIn("owner_gate", later)
        self.assertEqual(before, after)


    def test_expired_permission_challenge_cannot_authorize(self):
        gate = self.permission_gate("expired.txt")
        self.broker.owner_gate._permission_challenges[gate["challenge_id"]]["deadline"] = 0.0
        with self.assertRaises(Exception):
            self.decide(gate, "ALWAYS_ALLOW")
        self.assertFalse((self.workspace / "expired.txt").exists())

    def test_restart_invalidates_opaque_challenge_but_explicit_recovery_can_mint_new_one(self):
        gate = self.permission_gate("restart.txt")
        listed = self.broker.handle_rpc("continuation_list", {"recoverable_only": True})
        self.assertEqual(len(listed["continuations"]), 1)
        continuation_id = listed["continuations"][0]["continuation_id"]
        self.broker.close_owner_gate()

        replacement = AuthorityBroker(
            workspace=self.workspace,
            state=self.state,
            trace=self.trace,
            mode="interactive",
        )
        self.broker = replacement
        with self.assertRaises(Exception):
            self.decide(gate, "ALWAYS_ALLOW")

        recovered = replacement.handle_rpc(
            "permission_challenge",
            {"continuation_id": continuation_id},
        )
        new_gate = recovered["owner_gate"]
        self.assertNotEqual(new_gate["challenge_id"], gate["challenge_id"])
        completed = replacement.handle_rpc(
            "permission_decide",
            {"challenge_id": new_gate["challenge_id"], "choice": "ALWAYS_ALLOW"},
        )
        self.assertEqual(completed["result"]["execution_state"], "SUCCEEDED")

    def test_cross_project_recovery_fails_closed_before_owner_gate(self):
        self.permission_gate("project-a.txt")
        listed = self.broker.handle_rpc("continuation_list", {"recoverable_only": True})
        continuation_id = listed["continuations"][0]["continuation_id"]
        project_b = self.root / "project-b"
        project_b.mkdir()
        legacy.initialize_state(self.state, project_b)
        app_b = pi_v1_project_application_id(project_b)
        manifest_b = CapabilityManifest.create(pi_v1_capability_manifest(app_b))
        self.call("skills.register", {"manifest": json.loads(manifest_b.canonical_json())})

        other = AuthorityBroker(
            workspace=project_b,
            state=self.state,
            trace=self.root / "trace-b.jsonl",
            mode="interactive",
        )
        try:
            with self.assertRaises(Exception):
                other.handle_rpc(
                    "permission_challenge",
                    {"continuation_id": continuation_id},
                )
        finally:
            other.close_owner_gate()
        self.assertFalse((self.workspace / "project-a.txt").exists())

    def test_emergency_pause_still_wins_after_exact_owner_approval(self):
        gate = self.permission_gate("pause.txt")
        response = self.decide(gate, "ASK_EVERY_TIME")
        exact = response["owner_gate"]
        self.call("emergency.pause", {})
        result = self.approval(exact, True)
        self.assertEqual(result["result"]["authority_outcome"], "DENY")
        self.assertEqual(result["result"]["reason"], "EMERGENCY_PAUSED")
        self.assertFalse((self.workspace / "pause.txt").exists())

    def test_source_uses_exact_pinned_ui_gate_and_model_tool_surface_remains_four(self):
        repo = Path(__file__).resolve().parents[2]
        extension = (repo / "scripts" / "pi_native_tui.mjs").read_text()
        governed = (repo / "packages" / "adapters" / "pi" / "governed_pi.mjs").read_text()
        host = (repo / "scripts" / "pi_native_tui_host.py").read_text()
        for label in (
            "Allow once",
            "Always allow",
            "Ask every time",
            "Deny once",
            "Always deny",
        ):
            self.assertIn(label, extension)
        self.assertIn("ctx.ui.select(", extension)
        self.assertIn("ctx.ui.confirm(", extension)
        self.assertIn("Approval alone does not dispatch.", extension)
        self.assertIn("context: ctx", governed)
        self.assertNotIn("permissions.decide", governed)
        self.assertNotIn("approvals.approve", governed)
        self.assertIn('"admin_socket_visible"', host)
        self.assertIn("exactly the four governed tools", host)


if __name__ == "__main__":
    unittest.main(verbosity=2)
