import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from packages.core import Approval, EffectRequest, PolicyDecision
from packages.dispatcher import (
    DispatchApprovalRequired,
    DispatchDenied,
    DispatchDuplicateEffect,
    Dispatcher,
)
from packages.effects.filesystem import (
    FILESYSTEM_CREATE_ACTION,
    FILESYSTEM_DELETE_ACTION,
    FILESYSTEM_READ_ACTION,
    FILESYSTEM_REPLACE_ACTION,
    FilesystemEffectAdapter,
)
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    AgentIdentityRepository,
    ApprovalRepository,
    EffectReceiptRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    PolicyDecisionRepository,
    SQLiteStateStore,
)


NOW = "2026-09-13T08:00:05+00:00"


def fixed_clock():
    observed = datetime.fromisoformat(NOW)
    return lambda: observed


def make_request(*, suffix, action, arguments):
    return EffectRequest.create(
        request_id=f"effect:h002:{suffix}",
        run_id="run:h002",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=action,
        resource="filesystem:workspace",
        arguments=arguments,
        idempotency_key=f"idem:h002:{suffix}",
        created_at="2026-09-13T08:00:00Z",
        expires_at="2026-09-13T08:10:00Z",
    )


def provider(action, decision):
    return LocalPolicyDecisionProvider(
        revision=f"policy:h002:{action}:{decision}:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={action},
        known_resources={"filesystem:workspace"},
        rules=(
            PolicyRule.create(
                rule_id=f"rule:h002:{action}:{decision}",
                principal_id="principal:owner",
                agent_id="agent:test",
                action=action,
                resource="filesystem:workspace",
                decision=decision,
            ),
        ),
    )


def approval_foundation(store, request):
    decision = PolicyDecision.create(
        decision_id=f"decision:h002:foundation:{request.request_id}",
        request_id=request.request_id,
        decision="REQUIRE_APPROVAL",
        policy_revision="policy:h002:foundation:v1",
        reason_codes=("DECISION:REQUIRE_APPROVAL",),
        evaluated_at="2026-09-13T08:00:01Z",
        canonical_request_hash=request.canonical_hash,
    )
    approval = Approval.create(
        approval_id=f"approval:h002:{request.request_id}",
        request_id=request.request_id,
        policy_decision_id=decision.decision_id,
        canonical_request_hash=request.canonical_hash,
        approver="principal:owner",
        decision="APPROVE",
        scope="ONCE",
        created_at="2026-09-13T08:00:02Z",
        expires_at="2026-09-13T08:05:00Z",
    )
    PolicyDecisionRepository(store).put(decision)
    ApprovalRepository(store).put(approval)
    return approval


class FilesystemDispatchIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.workspace = base / "workspace"
        self.workspace.mkdir()
        (self.workspace / "existing.txt").write_text("old\n", encoding="utf-8")
        self.store = SQLiteStateStore(base / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")
        self.adapter = FilesystemEffectAdapter(self.workspace)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def dispatch(self, request, decision, *, approval_id=None, suffix="x"):
        EffectRequestRepository(self.store).put(request)
        return Dispatcher(
            store=self.store,
            policy_provider=provider(request.action, decision),
            clock=fixed_clock(),
            lease_seconds=20,
        ).dispatch(
            request,
            adapter=self.adapter,
            decision_id=f"decision:h002:current:{suffix}",
            lease_id=f"lease:h002:{suffix}",
            executor_id="executor:h002",
            approval_id=approval_id,
        )

    def test_allowed_read_returns_content_and_durable_receipt(self):
        req = make_request(suffix="read", action=FILESYSTEM_READ_ACTION, arguments={"path": "existing.txt"})
        result = self.dispatch(req, "ALLOW", suffix="read")
        self.assertEqual(result.content, "old\n")
        self.assertEqual(result.path, "existing.txt")
        self.assertEqual(result.byte_count, 4)
        receipt = EffectReceiptRepository(self.store).get_receipt_for_request(req.request_id)
        self.assertIsNotNone(receipt)
        self.assertEqual(receipt.outcome.value, "SUCCEEDED")

    def test_allowed_create_is_exactly_once_at_dispatch_boundary(self):
        req = make_request(
            suffix="create",
            action=FILESYSTEM_CREATE_ACTION,
            arguments={"path": "created.txt", "content": "created\n"},
        )
        result = self.dispatch(req, "ALLOW", suffix="create")
        self.assertEqual(result.path, "created.txt")
        self.assertEqual((self.workspace / "created.txt").read_text(encoding="utf-8"), "created\n")
        with self.assertRaises(DispatchDuplicateEffect):
            Dispatcher(
                store=self.store,
                policy_provider=provider(req.action, "ALLOW"),
                clock=fixed_clock(),
                lease_seconds=20,
            ).dispatch(
                req,
                adapter=self.adapter,
                decision_id="decision:h002:duplicate",
                lease_id="lease:h002:duplicate",
                executor_id="executor:h002",
            )
        self.assertEqual((self.workspace / "created.txt").read_text(encoding="utf-8"), "created\n")

    def test_replace_requires_exact_approval_before_mutation(self):
        req = make_request(
            suffix="replace",
            action=FILESYSTEM_REPLACE_ACTION,
            arguments={"path": "existing.txt", "content": "new\n"},
        )
        EffectRequestRepository(self.store).put(req)
        with self.assertRaises(DispatchApprovalRequired):
            Dispatcher(
                store=self.store,
                policy_provider=provider(req.action, "REQUIRE_APPROVAL"),
                clock=fixed_clock(),
                lease_seconds=20,
            ).dispatch(
                req,
                adapter=self.adapter,
                decision_id="decision:h002:noapproval",
                lease_id="lease:h002:noapproval",
                executor_id="executor:h002",
            )
        self.assertEqual((self.workspace / "existing.txt").read_text(encoding="utf-8"), "old\n")

        approval = approval_foundation(self.store, req)
        result = Dispatcher(
            store=self.store,
            policy_provider=provider(req.action, "REQUIRE_APPROVAL"),
            clock=fixed_clock(),
            lease_seconds=20,
        ).dispatch(
            req,
            adapter=self.adapter,
            decision_id="decision:h002:approved",
            lease_id="lease:h002:approved",
            executor_id="executor:h002",
            approval_id=approval.approval_id,
        )
        self.assertEqual(result.path, "existing.txt")
        self.assertEqual((self.workspace / "existing.txt").read_text(encoding="utf-8"), "new\n")

    def test_delete_policy_deny_never_mutates_host_file(self):
        req = make_request(
            suffix="delete",
            action=FILESYSTEM_DELETE_ACTION,
            arguments={"path": "existing.txt"},
        )
        with self.assertRaises(DispatchDenied):
            self.dispatch(req, "DENY", suffix="delete")
        self.assertTrue((self.workspace / "existing.txt").is_file())
        self.assertEqual((self.workspace / "existing.txt").read_text(encoding="utf-8"), "old\n")


if __name__ == "__main__":
    unittest.main()
