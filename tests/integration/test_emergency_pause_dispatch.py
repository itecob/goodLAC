import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from packages.core import Approval, EffectRequest, PolicyDecision
from packages.dispatcher import (
    DispatchApprovalRequired,
    DispatchAuthorityError,
    DispatchDenied,
    DispatchPaused,
    DispatchRequestExpired,
    Dispatcher,
)
from packages.effects.simulated import (
    SIMULATED_ACTION,
    SIMULATED_RESOURCE,
    SimulatedEffectAdapter,
)
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    AgentIdentityRepository,
    ApprovalRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    ExecutionLeaseRepository,
    PolicyDecisionRepository,
    SQLiteStateStore,
)

REQUEST_VALUES = {
    "request_id": "effect:c009-001",
    "run_id": "run:c009-001",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": SIMULATED_ACTION,
    "resource": SIMULATED_RESOURCE,
    "arguments": {"value": 9},
    "idempotency_key": "idem:c009-001",
    "created_at": "2026-09-12T10:00:00Z",
    "expires_at": "2026-09-12T10:20:00Z",
}


def make_request(**overrides):
    return EffectRequest.create(**{**REQUEST_VALUES, **overrides})


def fixed_clock(value="2026-09-12T10:04:00+00:00"):
    observed = datetime.fromisoformat(value)
    return lambda: observed


def make_provider(decision):
    return LocalPolicyDecisionProvider(
        revision=f"policy:c009:{decision.lower()}:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={SIMULATED_ACTION},
        known_resources={SIMULATED_RESOURCE},
        rules=(
            PolicyRule.create(
                rule_id=f"rule:c009:{decision.lower()}",
                principal_id="principal:owner",
                agent_id="agent:test",
                action=SIMULATED_ACTION,
                resource=SIMULATED_RESOURCE,
                decision=decision,
            ),
        ),
    )


def persist_approval_foundation(store, request):
    decision = PolicyDecision.create(
        decision_id="decision:c009:approval-foundation",
        request_id=request.request_id,
        decision="REQUIRE_APPROVAL",
        policy_revision="policy:c009:approval-foundation:v1",
        reason_codes=("DECISION:REQUIRE_APPROVAL",),
        evaluated_at="2026-09-12T10:00:01Z",
        canonical_request_hash=request.canonical_hash,
    )
    approval = Approval.create(
        approval_id="approval:c009:001",
        request_id=request.request_id,
        policy_decision_id=decision.decision_id,
        canonical_request_hash=request.canonical_hash,
        approver="principal:owner",
        decision="APPROVE",
        scope="ONCE",
        created_at="2026-09-12T10:00:02Z",
        expires_at="2026-09-12T10:10:00Z",
    )
    PolicyDecisionRepository(store).put(decision)
    ApprovalRepository(store).put(approval)
    return decision, approval


class RecordingAdapter(SimulatedEffectAdapter):
    def __init__(self):
        self.calls = []
    def invoke(self, request, *, lease):
        self.calls.append((request, lease))
        return super().invoke(request, lease=lease)


class PauseAfterAuthorityCommitStore(SQLiteStateStore):
    def __init__(self, path):
        self.pause_after_current_transaction = False
        super().__init__(path)
    @contextmanager
    def transaction(self):
        with super().transaction() as conn:
            yield conn
        if self.pause_after_current_transaction:
            self.pause_after_current_transaction = False
            EmergencyPauseRepository(self).pause()


class ArmingPolicyProvider:
    def __init__(self, provider, store):
        self.provider = provider
        self.store = store
    @property
    def policy_revision(self):
        return self.provider.policy_revision
    def evaluate(self, request, *, decision_id, evaluated_at):
        self.store.pause_after_current_transaction = True
        return self.provider.evaluate(
            request, decision_id=decision_id, evaluated_at=evaluated_at
        )


class EmergencyPauseDispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        self.pause = EmergencyPauseRepository(self.store)
        self.pause.resume()
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")
        self.request = make_request()
        EffectRequestRepository(self.store).put(self.request)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def dispatcher(self, decision="ALLOW", *, clock=None, store=None, provider=None):
        active_store = store or self.store
        return Dispatcher(
            store=active_store,
            policy_provider=provider or make_provider(decision),
            clock=clock or fixed_clock(),
            lease_seconds=20,
        )

    def kwargs(self, **overrides):
        values = {
            "decision_id": "decision:c009:current",
            "lease_id": "lease:c009:001",
            "executor_id": "executor:c009",
        }
        values.update(overrides)
        return values

    def test_paused_blocks_allow_before_lease_and_adapter_invocation(self):
        self.pause.pause()
        adapter = RecordingAdapter()
        with self.assertRaises(DispatchPaused):
            self.dispatcher("ALLOW").dispatch(
                self.request, adapter=adapter, **self.kwargs()
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:c009:001"))
        self.assertEqual(
            PolicyDecisionRepository(self.store).get("decision:c009:current").decision.value,
            "ALLOW",
        )

    def test_paused_blocks_qualifying_approval_without_consuming_it(self):
        _, approval = persist_approval_foundation(self.store, self.request)
        self.pause.pause()
        adapter = RecordingAdapter()
        with self.assertRaises(DispatchPaused):
            self.dispatcher("REQUIRE_APPROVAL").dispatch(
                self.request,
                adapter=adapter,
                approval_id=approval.approval_id,
                **self.kwargs(),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:c009:001"))
        self.assertIsNone(ApprovalRepository(self.store).get(approval.approval_id).consumed_at)

    def test_pause_survives_restart_and_preserves_read_only_inspection_state(self):
        decision, approval = persist_approval_foundation(self.store, self.request)
        self.pause.pause()
        self.store.close()
        self.store = SQLiteStateStore(self.db)
        self.pause = EmergencyPauseRepository(self.store)
        self.assertTrue(self.pause.get().paused)
        self.assertEqual(EffectRequestRepository(self.store).get(self.request.request_id), self.request)
        self.assertEqual(PolicyDecisionRepository(self.store).get(decision.decision_id), decision)
        self.assertEqual(ApprovalRepository(self.store).get(approval.approval_id), approval)

    def test_missing_and_malformed_pause_authority_fail_closed(self):
        adapter = RecordingAdapter()
        self.store.delete_system_state("controller.emergency_pause")
        with self.assertRaises(DispatchAuthorityError):
            self.dispatcher("ALLOW").dispatch(
                self.request, adapter=adapter, **self.kwargs()
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:c009:001"))

        self.pause.resume()
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE system_state SET value_json = ? WHERE key = ?",
                ('{"schema":"lac.emergency-pause/v1","paused":"no"}', "controller.emergency_pause"),
            )
        with self.assertRaises(DispatchAuthorityError):
            self.dispatcher("ALLOW").dispatch(
                self.request,
                adapter=adapter,
                **self.kwargs(decision_id="decision:c009:malformed", lease_id="lease:c009:malformed"),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:c009:malformed"))

    def test_resume_never_executes_and_expired_request_remains_blocked(self):
        expiring = make_request(
            request_id="effect:c009:expired",
            idempotency_key="idem:c009:expired",
            expires_at="2026-09-12T10:05:00Z",
        )
        EffectRequestRepository(self.store).put(expiring)
        adapter = RecordingAdapter()
        self.pause.pause()
        with self.assertRaises(DispatchPaused):
            self.dispatcher("ALLOW").dispatch(
                expiring,
                adapter=adapter,
                **self.kwargs(decision_id="decision:c009:paused-expiring", lease_id="lease:c009:paused-expiring"),
            )
        self.assertEqual(adapter.calls, [])
        self.pause.resume()
        self.assertEqual(adapter.calls, [])
        with self.assertRaises(DispatchRequestExpired):
            self.dispatcher(
                "ALLOW", clock=fixed_clock("2026-09-12T10:05:00+00:00")
            ).dispatch(
                expiring,
                adapter=adapter,
                **self.kwargs(decision_id="decision:c009:expired", lease_id="lease:c009:expired"),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:c009:expired"))

    def test_deny_and_missing_approval_ordering_remain_authoritative(self):
        self.pause.pause()
        adapter = RecordingAdapter()
        with self.assertRaises(DispatchDenied):
            self.dispatcher("DENY").dispatch(
                self.request, adapter=adapter, **self.kwargs()
            )
        self.assertEqual(adapter.calls, [])
        self.pause.resume()
        with self.assertRaises(DispatchApprovalRequired):
            self.dispatcher("REQUIRE_APPROVAL").dispatch(
                self.request,
                adapter=adapter,
                **self.kwargs(decision_id="decision:c009:approval-needed", lease_id="lease:c009:approval-needed"),
            )
        self.assertEqual(adapter.calls, [])

    def test_pause_committed_after_lease_commit_blocks_final_invocation(self):
        self.store.close()
        self.store = PauseAfterAuthorityCommitStore(self.db)
        self.pause = EmergencyPauseRepository(self.store)
        self.assertFalse(self.pause.get().paused)
        provider = ArmingPolicyProvider(make_provider("ALLOW"), self.store)
        adapter = RecordingAdapter()
        with self.assertRaises(DispatchPaused):
            self.dispatcher(store=self.store, provider=provider).dispatch(
                self.request, adapter=adapter, **self.kwargs()
            )
        self.assertEqual(adapter.calls, [])
        self.assertTrue(self.pause.get().paused)
        self.assertIsNotNone(ExecutionLeaseRepository(self.store).get("lease:c009:001"))


if __name__ == "__main__":
    unittest.main()
