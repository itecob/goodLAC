from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from packages.admin import AdminRequest, AdminService
from packages.adapters.pi.production import (
    PI_V1_AGENT_ID,
    PI_V1_APPLICATION_ID,
    PI_V1_CAPABILITY_MANIFEST,
    PI_V1_PRINCIPAL_ID,
    PI_V1_SKILL_ID,
    PiPermissionRuntime,
)
from packages.capabilities import CapabilityManifest, PendingPermissionRepository
from packages.effects.filesystem import FilesystemEffectAdapter
from packages.effects.shell import ShellEffectAdapter
from packages.policy import StandingPolicyRule
from packages.runtime.pi_continuation import PiWorkflowContinuationIntegrityError
from packages.state import AgentIdentityRepository, EmergencyPauseRepository, SQLiteStateStore


class MutableClock:
    def __init__(self):
        self.value = datetime(2026, 9, 17, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value

    def advance(self, seconds: int):
        self.value += timedelta(seconds=seconds)


class PiV1WorkflowContinuationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix="lac-pi002-d001-")
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
        self.runtime = self.make_runtime("run:d001:test")
        self.register_manifest()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def make_runtime(self, run_id, *, clock=None, continuation_ttl_seconds=3600):
        return PiPermissionRuntime(
            store=self.store,
            filesystem_adapter=self.fs,
            shell_adapter=self.shell,
            run_id=run_id,
            clock=clock,
            continuation_ttl_seconds=continuation_ttl_seconds,
        )

    def admin_call(self, operation, arguments):
        request = AdminRequest.create(
            request_id=f"admin:d001:{operation}:{os.urandom(6).hex()}",
            operation=operation,
            arguments=arguments,
        )
        return self.admin.execute(request, peer_uid=os.getuid())

    def register_manifest(self):
        manifest = CapabilityManifest.create(PI_V1_CAPABILITY_MANIFEST)
        return self.admin_call(
            "skills.register", {"manifest": json.loads(manifest.canonical_json())}
        )

    def set_policy(self, decision, *, rule_id="d001-rule"):
        rule = StandingPolicyRule.create(
            rule_id=rule_id,
            application_id=PI_V1_APPLICATION_ID,
            skill_id=PI_V1_SKILL_ID,
            action="filesystem.create",
            resource_selector="filesystem:workspace",
            decision=decision,
        )
        return self.admin_call(
            "permissions.replace", {"rules": [rule.to_material()], "defaults": []}
        )

    def msg(self, call_id, *, path=None, content=None):
        return {
            "toolCallId": call_id,
            "toolName": "lac_fs_create",
            "arguments": {
                "path": path or f"{call_id}.txt",
                "content": content or call_id,
            },
        }

    def block(self, call_id, *, path=None, content=None, runtime=None):
        runtime = runtime or self.runtime
        message = self.msg(call_id, path=path, content=content)
        result = runtime.submit_message(message)
        self.assertEqual(result["authority_outcome"], "DENY")
        self.assertTrue(result["permission_configuration"]["required"])
        status = result["workflow_continuation"]
        self.assertEqual(status["state"], "WAITING_PERMISSION")
        return message, result, status

    def resolve(self, pending_id, resolution="POLICY_UPDATED"):
        return self.admin_call(
            "pending.resolve", {"pending_id": pending_id, "resolution": resolution}
        )

    def test_allow_continuation_uses_one_fresh_request_and_never_revives_original(self):
        message, blocked, status = self.block(
            "allow", path="allow.txt", content="continued"
        )
        original = blocked["request_id"]
        continuation_id = status["continuation_id"]
        self.assertFalse((self.workspace / "allow.txt").exists())

        self.set_policy("ALLOW")
        self.resolve(status["pending_id"])
        resumed = self.runtime.resume_continuation(
            continuation_id, expected_message=message
        )
        result = resumed["result"]
        self.assertEqual((result["authority_outcome"], result["execution_state"]), ("ALLOW", "SUCCEEDED"))
        fresh = result["request_id"]
        self.assertNotEqual(fresh, original)
        self.assertEqual(result["workflow_continuation"]["resume_budget_used"], 1)
        self.assertEqual((self.workspace / "allow.txt").read_text(), "continued")

        original_again = self.runtime.submit_message(message)
        self.assertEqual(original_again["request_id"], original)
        self.assertEqual(original_again["authority_outcome"], "DENY")
        self.assertTrue(original_again["permission_configuration"]["required"])
        closure = PendingPermissionRepository(self.store).get_closure(original)
        self.assertIsNotNone(closure)

        duplicate = self.runtime.resume_continuation(
            continuation_id, expected_message=message
        )["result"]
        self.assertEqual(duplicate["request_id"], fresh)
        self.assertTrue(duplicate["replayed"])
        self.assertEqual(
            duplicate["receipt"]["receipt_id"], result["receipt"]["receipt_id"]
        )

    def test_require_approval_continuation_preserves_exact_approval_semantics(self):
        message, _blocked, status = self.block(
            "ask", path="ask.txt", content="approved-once"
        )
        self.set_policy("REQUIRE_APPROVAL")
        self.resolve(status["pending_id"])

        pending = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(
            (pending["authority_outcome"], pending["execution_state"]),
            ("REQUIRE_APPROVAL", "PENDING_APPROVAL"),
        )
        self.assertFalse((self.workspace / "ask.txt").exists())
        decision_id = pending["decision_id"]
        self.admin_call("approvals.approve", {"decision_id": decision_id})

        executed = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(
            (executed["authority_outcome"], executed["execution_state"]),
            ("ALLOW", "SUCCEEDED"),
        )
        self.assertEqual((self.workspace / "ask.txt").read_text(), "approved-once")
        self.assertEqual(
            executed["request_id"], pending["request_id"], "approval must bind same fresh request"
        )

    def test_configured_deny_after_resolution_creates_fresh_request_but_no_effect(self):
        message, blocked, status = self.block(
            "deny", path="deny.txt", content="never"
        )
        self.set_policy("DENY")
        self.resolve(status["pending_id"])
        resumed = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(resumed["authority_outcome"], "DENY")
        self.assertEqual(resumed["execution_state"], "DENIED")
        self.assertNotEqual(resumed["request_id"], blocked["request_id"])
        self.assertFalse((self.workspace / "deny.txt").exists())
        self.assertEqual(resumed["workflow_continuation"]["resume_budget_used"], 1)

    def test_dismiss_is_explicit_nonauthorizing_without_fresh_request(self):
        message, _blocked, status = self.block(
            "dismiss", path="dismiss.txt", content="never"
        )
        self.admin_call("pending.dismiss", {"pending_id": status["pending_id"]})
        dismissed = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )
        self.assertEqual(dismissed["kind"], "CLOSED_NONAUTH")
        self.assertEqual(dismissed["result"]["authority_outcome"], "DENY")
        self.assertEqual(dismissed["workflow_continuation"]["resume_budget_used"], 0)
        self.assertIsNone(dismissed["workflow_continuation"]["fresh_request_id"])
        self.assertFalse((self.workspace / "dismiss.txt").exists())

    def test_no_change_is_explicit_nonauthorizing_without_fresh_request(self):
        message, _blocked, status = self.block(
            "no-change", path="no-change.txt", content="never"
        )
        self.resolve(status["pending_id"], "NO_CHANGE")
        outcome = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )
        self.assertEqual(outcome["kind"], "CLOSED_NONAUTH")
        self.assertEqual(outcome["result"]["execution_state"], "NOT_EXECUTED")
        self.assertEqual(outcome["workflow_continuation"]["resume_budget_used"], 0)
        self.assertFalse((self.workspace / "no-change.txt").exists())


    def test_fresh_continuation_rechecks_emergency_pause(self):
        message, blocked, status = self.block(
            "emergency", path="emergency.txt", content="never"
        )
        self.set_policy("ALLOW")
        self.resolve(status["pending_id"])
        self.admin_call("emergency.pause", {})
        resumed = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )
        outcome = resumed["result"]
        self.assertEqual(outcome["authority_outcome"], "DENY")
        self.assertEqual(outcome["execution_state"], "DENIED")
        self.assertEqual(outcome["reason"], "EMERGENCY_PAUSED")
        self.assertIsNone(outcome["receipt"])
        self.assertEqual(resumed["workflow_continuation"]["state"], "COMPLETED")
        self.assertEqual(resumed["workflow_continuation"]["resume_budget_used"], 1)
        self.assertNotEqual(outcome["request_id"], blocked["request_id"])
        self.assertFalse((self.workspace / "emergency.txt").exists())

        # The fresh continuation budget is exhausted even if emergency pause is later lifted.
        # Repeated resume returns the explicit stored non-effect result and never dispatches.
        self.admin_call("emergency.resume", {})
        replay = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )
        replay_result = replay["result"]
        self.assertEqual(replay_result["request_id"], outcome["request_id"])
        self.assertEqual(replay_result["authority_outcome"], "DENY")
        self.assertEqual(replay_result["execution_state"], "DENIED")
        self.assertEqual(replay_result["reason"], "EMERGENCY_PAUSED")
        self.assertEqual(replay["workflow_continuation"]["resume_budget_used"], 1)
        self.assertFalse((self.workspace / "emergency.txt").exists())

    def test_authorizing_admin_disposition_without_authorizing_policy_is_one_shot_nonauthorizing(self):
        message, _blocked, status = self.block(
            "cap-only", path="cap-only.txt", content="never"
        )
        self.resolve(status["pending_id"], "CAPABILITY_UPDATED")
        outcome = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )
        result = outcome["result"]
        self.assertEqual(result["authority_outcome"], "DENY")
        self.assertEqual(result["execution_state"], "DENIED")
        self.assertFalse(result["permission_configuration"]["required"])
        self.assertEqual(
            result["permission_configuration"]["reason"],
            "CONTINUATION_BUDGET_EXHAUSTED",
        )
        self.assertEqual(outcome["workflow_continuation"]["resume_budget_used"], 1)
        self.assertFalse((self.workspace / "cap-only.txt").exists())

    def test_material_mutation_invalidates_continuation_before_budget_is_consumed(self):
        message, _blocked, status = self.block(
            "mutation", path="mutation.txt", content="original"
        )
        self.set_policy("ALLOW")
        self.resolve(status["pending_id"])
        mutated = self.msg(
            "mutation", path="mutation.txt", content="mutated-security-relevant-argument"
        )
        with self.assertRaises(Exception):
            self.runtime.resume_continuation(
                status["continuation_id"], expected_message=mutated
            )
        unchanged = self.runtime.continuation_status(status["continuation_id"])
        self.assertEqual(unchanged["state"], "WAITING_PERMISSION")
        self.assertEqual(unchanged["resume_budget_used"], 0)
        self.assertFalse((self.workspace / "mutation.txt").exists())

        allowed = self.runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )["result"]
        self.assertEqual(allowed["execution_state"], "SUCCEEDED")
        self.assertEqual((self.workspace / "mutation.txt").read_text(), "original")

    def test_restart_is_recoverable_but_restart_alone_never_dispatches(self):
        _message, _blocked, status = self.block(
            "restart", path="restart.txt", content="after-explicit-resume"
        )
        self.set_policy("ALLOW")
        self.resolve(status["pending_id"])

        restarted = self.make_runtime("run:d001:after-restart")
        recoverable = restarted.list_continuations(recoverable_only=True)
        ids = {item["continuation_id"] for item in recoverable}
        self.assertIn(status["continuation_id"], ids)
        self.assertFalse((self.workspace / "restart.txt").exists())

        resumed = restarted.resume_continuation(status["continuation_id"])["result"]
        self.assertEqual(resumed["execution_state"], "SUCCEEDED")
        self.assertEqual(
            (self.workspace / "restart.txt").read_text(), "after-explicit-resume"
        )

    def test_expired_and_malformed_continuation_state_fail_closed(self):
        clock = MutableClock()
        runtime = self.make_runtime(
            "run:d001:expiry", clock=clock, continuation_ttl_seconds=30
        )
        message, _blocked, status = self.block(
            "expiry", path="expiry.txt", content="never", runtime=runtime
        )
        self.set_policy("ALLOW")
        self.resolve(status["pending_id"])
        clock.advance(31)
        expired = runtime.resume_continuation(
            status["continuation_id"], expected_message=message
        )
        self.assertEqual(expired["kind"], "EXPIRED")
        self.assertEqual(expired["workflow_continuation"]["resume_budget_used"], 0)
        self.assertFalse((self.workspace / "expiry.txt").exists())

        self.store.set_system_state("pi_v1.workflow_continuations.v1", {"bad": True})
        with self.assertRaises(PiWorkflowContinuationIntegrityError):
            runtime.list_continuations()

    def test_stale_prior_pending_resolution_cannot_authorize_a_later_continuation(self):
        first_message, _first, first_status = self.block(
            "stale-a", path="stale-a.txt", content="A"
        )
        self.resolve(first_status["pending_id"], "NO_CHANGE")

        second_message, _second, second_status = self.block(
            "stale-b", path="stale-b.txt", content="B"
        )
        self.assertEqual(first_status["pending_id"], second_status["pending_id"])
        self.assertEqual(second_status["resolution_baseline_revision"], 1)
        self.assertIsNone(second_status["owner_resolution"])
        waiting = self.runtime.resume_continuation(second_status["continuation_id"])
        self.assertEqual(waiting["kind"], "WAITING_PERMISSION")
        self.assertFalse((self.workspace / "stale-b.txt").exists())

        self.set_policy("ALLOW")
        self.resolve(first_status["pending_id"], "POLICY_UPDATED")

        # The earlier continuation binds the first post-capture owner event (NO_CHANGE),
        # so a later policy update cannot retroactively revive that blocked workflow.
        first_outcome = self.runtime.resume_continuation(
            first_status["continuation_id"], expected_message=first_message
        )
        self.assertEqual(first_outcome["kind"], "CLOSED_NONAUTH")
        self.assertFalse((self.workspace / "stale-a.txt").exists())

        second_outcome = self.runtime.resume_continuation(
            second_status["continuation_id"], expected_message=second_message
        )["result"]
        self.assertEqual(second_outcome["execution_state"], "SUCCEEDED")
        self.assertEqual((self.workspace / "stale-b.txt").read_text(), "B")

    def test_equivalent_pending_aggregation_never_cross_binds_continuations(self):
        first_message, _first, first_status = self.block(
            "aggregate-a", path="aggregate-a.txt", content="A"
        )
        second_message, _second, second_status = self.block(
            "aggregate-b", path="aggregate-b.txt", content="B"
        )
        self.assertEqual(first_status["pending_id"], second_status["pending_id"])
        self.assertNotEqual(
            first_status["continuation_id"], second_status["continuation_id"]
        )

        self.set_policy("ALLOW")
        self.resolve(first_status["pending_id"])
        first_result = self.runtime.resume_continuation(
            first_status["continuation_id"], expected_message=first_message
        )["result"]
        second_result = self.runtime.resume_continuation(
            second_status["continuation_id"], expected_message=second_message
        )["result"]
        self.assertNotEqual(first_result["request_id"], second_result["request_id"])
        self.assertEqual((self.workspace / "aggregate-a.txt").read_text(), "A")
        self.assertEqual((self.workspace / "aggregate-b.txt").read_text(), "B")
        self.assertEqual(
            first_result["workflow_continuation"]["original_request_id"],
            first_status["original_request_id"],
        )
        self.assertEqual(
            second_result["workflow_continuation"]["original_request_id"],
            second_status["original_request_id"],
        )

    def test_status_projection_exposes_no_captured_arguments_or_admin_capability(self):
        _message, _blocked, status = self.block(
            "projection", path="projection.txt", content="captured-content"
        )
        projected = self.runtime.continuation_status(status["continuation_id"])
        self.assertNotIn("arguments", projected)
        self.assertNotIn("idempotency_key", projected)
        self.assertNotIn("admin", projected)
        for name in ("approve", "register", "replace_policy", "admin"):
            self.assertFalse(hasattr(self.runtime.continuations, name))


if __name__ == "__main__":
    unittest.main(verbosity=2)
