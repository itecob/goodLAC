import copy
import json
import os
import unittest

from packages.admin import AdminService
from packages.core import canonical_json
from packages.policy import StandingPolicyRule
from packages.runtime import (
    ExternalConsumerConfigurationError,
    ExternalConsumerDeclaration,
    ExternalConsumerProtocolError,
    ExternalConsumerRuntime,
    ExternalConsumerRuntimeError,
)
from packages.state import ApprovalRepository, SQLiteStateStore
from tests.acceptance.test_b003_external_consumer import CountingAdapter, Harness


class FailingAdapter(CountingAdapter):
    def invoke(self, request, *, lease):
        self.invoke_calls += 1
        raise RuntimeError("synthetic P4-B002 adapter failure")


class P4B002ExternalConsumerBindingTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.cleanup()

    def _manifest_b(self):
        manifest = copy.deepcopy(self.h.manifest)
        manifest["application_id"] = "b003-external-app-b"
        manifest["skill_id"] = "notes-b"
        return manifest

    def _runtime_b(self, manifest_b, *, adapter=None):
        return ExternalConsumerRuntime(
            store=self.h.store,
            declaration=ExternalConsumerDeclaration.create(manifest_b),
            principal_id="principal:owner",
            agent_id="agent:b003",
            application_id="b003-external-app-b",
            skill_id="notes-b",
            adapter=adapter or self.h.adapter,
        )

    def _register_pair(self):
        self.h.register()
        manifest_b = self._manifest_b()
        self.h.register(manifest_b)
        return manifest_b

    def _counts(self):
        return {
            table: self.h.store._conn.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            ).fetchone()["count"]
            for table in ("policy_decisions", "execution_leases", "effect_receipts")
        }

    def test_cross_binding_existing_request_fails_before_policy_lease_adapter_or_result(self):
        manifest_b = self._register_pair()
        runtime_a = self.h.runtime()
        runtime_b = self._runtime_b(manifest_b)
        request = self.h.request("p4-b002-existing")

        denied = runtime_a.submit(request)
        self.assertEqual(denied["authority_outcome"], "DENY")
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        rows = self.h.store._conn.execute(
            """
            SELECT key, value_json
            FROM system_state
            WHERE key LIKE 'external-consumer/request-binding/v1/%'
            """
        ).fetchall()
        self.assertEqual(len(rows), 1)
        binding = json.loads(rows[0]["value_json"])
        self.assertEqual(canonical_json(binding), rows[0]["value_json"])
        self.assertEqual(
            binding,
            {
                "schema": "lac.external-consumer-request-binding/v1",
                "request_id": request["request_id"],
                "principal_id": "principal:owner",
                "agent_id": "agent:b003",
                "application_id": "b003-external-app",
                "skill_id": "notes",
            },
        )

        before = self._counts()
        with self.assertRaisesRegex(
            ExternalConsumerProtocolError,
            "outside this consumer binding",
        ):
            runtime_b.submit(request)
        self.assertEqual(self._counts(), before)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

    def test_cross_binding_exact_approval_cannot_qualify_or_be_consumed(self):
        manifest_b = self._register_pair()
        ask_b = StandingPolicyRule.create(
            rule_id="p4-b002-ask-b",
            application_id="b003-external-app-b",
            skill_id="notes-b",
            action="notes.write",
            decision="REQUIRE_APPROVAL",
        )
        self.h.set_rules([ask_b])
        runtime_b = self._runtime_b(manifest_b)
        runtime_a = self.h.runtime()
        request = self.h.request("p4-b002-approval", action="notes.write")

        pending = runtime_b.submit(request)
        self.assertEqual(pending["authority_outcome"], "REQUIRE_APPROVAL")
        approved = self.h.approve(pending["decision_id"])
        approval_id = approved["approval"]["approval_id"]
        self.assertIsNone(ApprovalRepository(self.h.store).get(approval_id).consumed_at)

        before = self._counts()
        with self.assertRaisesRegex(
            ExternalConsumerProtocolError,
            "outside this consumer binding",
        ):
            runtime_a.submit(request)
        self.assertEqual(self._counts(), before)
        self.assertIsNone(ApprovalRepository(self.h.store).get(approval_id).consumed_at)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        allowed = runtime_b.submit(request)
        self.assertEqual(allowed["authority_outcome"], "ALLOW")
        self.assertEqual(self.h.adapter.invoke_calls, 1)
        self.assertIsNotNone(ApprovalRepository(self.h.store).get(approval_id).consumed_at)

    def test_success_terminal_replay_status_and_restart_preserve_binding(self):
        manifest_b = self._register_pair()
        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="p4-b002-allow-b",
                application_id="b003-external-app-b",
                skill_id="notes-b",
                action="notes.read",
                decision="ALLOW",
            )
        ])
        runtime_b = self._runtime_b(manifest_b)
        runtime_a = self.h.runtime()
        request = self.h.request("p4-b002-terminal-success")

        first = runtime_b.submit(request)
        self.assertEqual(first["execution_state"], "SUCCEEDED")
        self.assertEqual(self.h.adapter.invoke_calls, 1)

        with self.assertRaisesRegex(
            ExternalConsumerProtocolError,
            "outside this consumer binding",
        ):
            runtime_a.submit(request)
        with self.assertRaisesRegex(
            ExternalConsumerProtocolError,
            "outside this consumer binding",
        ):
            runtime_a.status(request["request_id"])
        self.assertEqual(self.h.adapter.invoke_calls, 1)

        status_b = runtime_b.status(request["request_id"])
        self.assertEqual(status_b["receipt"]["receipt_id"], first["receipt"]["receipt_id"])
        self.assertTrue(status_b["replayed"])

        db_path = self.h.store.path
        self.h.store.close()
        self.h.store = SQLiteStateStore(db_path)
        self.h.admin = AdminService(self.h.store, owner_uid=os.getuid())

        restarted_a = self.h.runtime()
        restarted_b = self._runtime_b(manifest_b)
        with self.assertRaisesRegex(
            ExternalConsumerProtocolError,
            "outside this consumer binding",
        ):
            restarted_a.status(request["request_id"])
        replay = restarted_b.submit(request)
        self.assertEqual(replay["execution_state"], "SUCCEEDED")
        self.assertTrue(replay["replayed"])
        self.assertEqual(replay["receipt"]["receipt_id"], first["receipt"]["receipt_id"])
        self.assertEqual(self.h.adapter.invoke_calls, 1)

    def test_failed_terminal_receipt_is_not_disclosable_across_binding(self):
        manifest_b = self._register_pair()
        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="p4-b002-allow-failure-b",
                application_id="b003-external-app-b",
                skill_id="notes-b",
                action="notes.read",
                decision="ALLOW",
            )
        ])
        failing = FailingAdapter()
        runtime_b = self._runtime_b(manifest_b, adapter=failing)
        runtime_a = ExternalConsumerRuntime(
            store=self.h.store,
            declaration=self.h.declaration,
            principal_id="principal:owner",
            agent_id="agent:b003",
            application_id="b003-external-app",
            skill_id="notes",
            adapter=failing,
        )
        request = self.h.request("p4-b002-terminal-failure")

        with self.assertRaises(ExternalConsumerRuntimeError):
            runtime_b.submit(request)
        self.assertEqual(failing.invoke_calls, 1)

        with self.assertRaisesRegex(
            ExternalConsumerProtocolError,
            "outside this consumer binding",
        ):
            runtime_a.submit(request)
        with self.assertRaisesRegex(
            ExternalConsumerProtocolError,
            "outside this consumer binding",
        ):
            runtime_a.status(request["request_id"])

        failed = runtime_b.status(request["request_id"])
        self.assertEqual(failed["execution_state"], "FAILED")
        self.assertEqual(failed["authority_outcome"], "DENY")
        self.assertTrue(failed["replayed"])
        self.assertEqual(failing.invoke_calls, 1)

    def test_p4_b001_declaration_identity_mismatch_remains_pre_authority(self):
        self.h.register()
        manifest_b = self._manifest_b()
        self.h.register(manifest_b)
        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="p4-b002-borrowed-allow",
                application_id="b003-external-app-b",
                skill_id="notes-b",
                decision="ALLOW",
            )
        ])
        before = self._counts()
        with self.assertRaisesRegex(
            ExternalConsumerConfigurationError,
            "controller-owned binding",
        ):
            ExternalConsumerRuntime(
                store=self.h.store,
                declaration=ExternalConsumerDeclaration.create(manifest_b),
                principal_id="principal:owner",
                agent_id="agent:b003",
                application_id="b003-external-app",
                skill_id="notes",
                adapter=self.h.adapter,
            )
        self.assertEqual(self._counts(), before)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

    def test_legacy_unbound_request_is_not_retroactively_claimable(self):
        from datetime import datetime, timedelta, timezone
        from packages.core import EffectRequest
        from packages.state import EffectRequestRepository

        self.h.register()
        now = datetime.now(timezone.utc)
        request = self.h.request("p4-b002-legacy-unbound")
        legacy = EffectRequest.create(
            request_id=request["request_id"],
            run_id=request["run_id"],
            principal_id="principal:owner",
            agent_id="agent:b003",
            action=request["action"],
            resource=request["resource"],
            arguments=request["arguments"],
            idempotency_key=request["idempotency_key"],
            created_at=now.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            expires_at=(now + timedelta(minutes=5)).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        )
        EffectRequestRepository(self.h.store).put(legacy)

        with self.assertRaisesRegex(
            ExternalConsumerRuntimeError,
            "lacks four-dimensional",
        ):
            self.h.runtime().submit(request)
        self.assertEqual(self.h.adapter.invoke_calls, 0)


if __name__ == "__main__":
    unittest.main()
