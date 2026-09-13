import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from packages.core import Approval, EffectExecutionState, EffectOutcome, EffectRequest, PolicyDecision, result_hash_for_json
from packages.dispatcher import (
    DispatchAdapterError,
    DispatchAuthorityError,
    DispatchDuplicateEffect,
    DispatchPaused,
    Dispatcher,
)
from packages.effects.simulated import SimulatedEffectAdapter
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    AgentIdentityRepository,
    ApprovalRepository,
    AuditRepository,
    EffectReceiptRepository,
    EffectRequestRepository,
    PolicyDecisionRepository,
    EmergencyPauseRepository,
    SQLiteStateStore,
)


class SimulatedCrash(BaseException):
    pass


def make_request(request_id="effect:c010-001", idempotency_key="idem:c010-001"):
    return EffectRequest.create(
        request_id=request_id, run_id="run:c010", principal_id="principal:owner",
        agent_id="agent:test", action="simulated.write", resource="simulated:alpha",
        arguments={"value": 17}, idempotency_key=idempotency_key,
        created_at="2026-09-12T10:00:00Z", expires_at="2026-09-12T10:20:00Z"
    )


def provider(decision="ALLOW"):
    return LocalPolicyDecisionProvider(
        revision=f"policy:c010:{decision.lower()}:v1",
        known_principals={"principal:owner"}, known_agents={"agent:test"},
        known_actions={"simulated.write"}, known_resources={"simulated:alpha"},
        rules=(PolicyRule.create(
            rule_id=f"rule:c010:{decision.lower()}", principal_id="principal:owner",
            agent_id="agent:test", action="simulated.write", resource="simulated:alpha",
            decision=decision,
        ),),
    )


def clock(value="2026-09-12T10:04:00+00:00"):
    dt = datetime.fromisoformat(value)
    return lambda: dt


class CountingAdapter(SimulatedEffectAdapter):
    def __init__(self):
        self.invocations = 0
        self.reconciliations = 0
    def invoke(self, request, *, lease):
        self.invocations += 1
        return super().invoke(request, lease=lease)
    def reconcile(self, request, *, lease):
        self.reconciliations += 1
        return super().reconcile(request, lease=lease)


class FailureAdapter(CountingAdapter):
    def invoke(self, request, *, lease):
        self.invocations += 1
        raise RuntimeError("deterministic adapter failure")


class CrashDuringInvokeAdapter(CountingAdapter):
    def invoke(self, request, *, lease):
        self.invocations += 1
        raise SimulatedCrash("process crash during ambiguous invocation window")


class CrashAfterAuthorityStore(SQLiteStateStore):
    def __init__(self, path):
        self.crash_after_current_transaction = False
        super().__init__(path)
    @contextmanager
    def transaction(self):
        with super().transaction() as conn:
            yield conn
        if self.crash_after_current_transaction:
            self.crash_after_current_transaction = False
            raise SimulatedCrash("process crash after LEASED commit")


class ArmingProvider:
    def __init__(self, wrapped, store):
        self.wrapped = wrapped
        self.store = store
    @property
    def policy_revision(self):
        return self.wrapped.policy_revision
    def evaluate(self, request, *, decision_id, evaluated_at):
        self.store.crash_after_current_transaction = True
        return self.wrapped.evaluate(request, decision_id=decision_id, evaluated_at=evaluated_at)


class C010ReceiptReconciliationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")
        self.request = make_request()
        EffectRequestRepository(self.store).put(self.request)

    def tearDown(self):
        try:
            self.store.close()
        finally:
            self.tmp.cleanup()

    def dispatcher(self, decision="ALLOW", *, store=None, policy=None, at=None):
        return Dispatcher(
            store=store or self.store, policy_provider=policy or provider(decision),
            clock=clock(at or "2026-09-12T10:04:00+00:00"), lease_seconds=20,
        )

    @staticmethod
    def kwargs(suffix="1"):
        return {
            "decision_id": f"decision:c010:{suffix}",
            "lease_id": f"lease:c010:{suffix}",
            "executor_id": "executor:c010",
        }

    def test_success_receipt_audit_restart_and_terminal_duplicate_are_exactly_once(self):
        adapter = CountingAdapter()
        result = self.dispatcher().dispatch(self.request, adapter=adapter, **self.kwargs())
        self.assertEqual(result.request_id, self.request.request_id)
        self.assertEqual(adapter.invocations, 1)
        execution = EffectReceiptRepository(self.store).get_execution(self.request.request_id)
        receipt = EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id)
        self.assertEqual(execution.state, EffectExecutionState.SUCCEEDED)
        self.assertEqual(receipt.outcome, EffectOutcome.SUCCEEDED)
        self.assertEqual(receipt.canonical_request_hash, self.request.canonical_hash)
        self.assertEqual(receipt.adapter_id, "simulated:v1")
        self.assertEqual(receipt.result["result_hash"], result.result_hash)
        self.assertEqual(receipt.result_hash, result_hash_for_json(receipt.result_json))
        self.assertEqual(
            [e.event_type for e in AuditRepository(self.store).list_for_request(self.request.request_id)],
            ["EFFECT_LEASED", "EFFECT_PREPARED", "EFFECT_SUCCEEDED"],
        )
        self.store.close()
        self.store = SQLiteStateStore(self.db)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id), receipt
        )
        with self.assertRaises(DispatchDuplicateEffect):
            self.dispatcher(at="2026-09-12T10:04:05+00:00").dispatch(
                self.request, adapter=adapter, **self.kwargs("duplicate")
            )
        self.assertEqual(adapter.invocations, 1)


    def test_approval_dispatch_receipt_binds_exact_consumed_approval(self):
        foundation = PolicyDecision.create(
            decision_id="decision:c010:approval-foundation",
            request_id=self.request.request_id, decision="REQUIRE_APPROVAL",
            policy_revision="policy:c010:approval-foundation:v1",
            reason_codes=("DECISION:REQUIRE_APPROVAL",),
            evaluated_at="2026-09-12T10:00:01Z",
            canonical_request_hash=self.request.canonical_hash,
        )
        approval = Approval.create(
            approval_id="approval:c010:001", request_id=self.request.request_id,
            policy_decision_id=foundation.decision_id,
            canonical_request_hash=self.request.canonical_hash, approver="principal:owner",
            decision="APPROVE", scope="ONCE", created_at="2026-09-12T10:00:02Z",
            expires_at="2026-09-12T10:10:00Z",
        )
        PolicyDecisionRepository(self.store).put(foundation)
        ApprovalRepository(self.store).put(approval)
        adapter = CountingAdapter()
        self.dispatcher("REQUIRE_APPROVAL").dispatch(
            self.request, adapter=adapter, approval_id=approval.approval_id, **self.kwargs()
        )
        receipt = EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id)
        consumed = ApprovalRepository(self.store).get(approval.approval_id)
        self.assertEqual(receipt.approval_id, approval.approval_id)
        self.assertEqual(consumed.consumed_at, "2026-09-12T10:04:00.000000Z")
        self.assertEqual(adapter.invocations, 1)

    def test_adapter_failure_has_durable_failure_receipt_and_cannot_retry_effect(self):
        adapter = FailureAdapter()
        with self.assertRaises(DispatchAdapterError):
            self.dispatcher().dispatch(self.request, adapter=adapter, **self.kwargs())
        self.assertEqual(adapter.invocations, 1)
        execution = EffectReceiptRepository(self.store).get_execution(self.request.request_id)
        receipt = EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id)
        self.assertEqual(execution.state, EffectExecutionState.FAILED)
        self.assertEqual(receipt.outcome, EffectOutcome.FAILED)
        self.assertEqual(receipt.result, {"error_code": "ADAPTER_INVOCATION_FAILED"})
        with self.assertRaises(DispatchDuplicateEffect):
            self.dispatcher(at="2026-09-12T10:04:05+00:00").dispatch(
                self.request, adapter=adapter, **self.kwargs("retry")
            )
        self.assertEqual(adapter.invocations, 1)

    def test_crash_after_lease_is_distinguishable_has_no_false_success_and_recovers(self):
        self.store.close()
        self.store = CrashAfterAuthorityStore(self.db)
        adapter = CountingAdapter()
        armed = ArmingProvider(provider("ALLOW"), self.store)
        with self.assertRaises(SimulatedCrash):
            self.dispatcher(store=self.store, policy=armed).dispatch(
                self.request, adapter=adapter, **self.kwargs()
            )
        execution = EffectReceiptRepository(self.store).get_execution(self.request.request_id)
        self.assertEqual(execution.state, EffectExecutionState.LEASED)
        self.assertIsNone(EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id))
        self.assertEqual(adapter.invocations, 0)
        self.store.close()
        self.store = SQLiteStateStore(self.db)
        result = self.dispatcher(at="2026-09-12T10:04:05+00:00").dispatch(
            self.request, adapter=adapter, **self.kwargs("recover")
        )
        self.assertEqual(result.request_id, self.request.request_id)
        self.assertEqual(adapter.invocations, 1)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(self.request.request_id).state,
            EffectExecutionState.SUCCEEDED,
        )

    def test_crash_after_lease_with_consumed_approval_recovers_only_reserved_exact_approval(self):
        foundation = PolicyDecision.create(
            decision_id="decision:c010:approval-crash-foundation",
            request_id=self.request.request_id, decision="REQUIRE_APPROVAL",
            policy_revision="policy:c010:approval-foundation:v1",
            reason_codes=("DECISION:REQUIRE_APPROVAL",),
            evaluated_at="2026-09-12T10:00:01Z",
            canonical_request_hash=self.request.canonical_hash,
        )
        approval = Approval.create(
            approval_id="approval:c010:crash", request_id=self.request.request_id,
            policy_decision_id=foundation.decision_id, canonical_request_hash=self.request.canonical_hash,
            approver="principal:owner", decision="APPROVE", scope="ONCE",
            created_at="2026-09-12T10:00:02Z", expires_at="2026-09-12T10:10:00Z",
        )
        PolicyDecisionRepository(self.store).put(foundation)
        ApprovalRepository(self.store).put(approval)
        self.store.close()
        self.store = CrashAfterAuthorityStore(self.db)
        adapter = CountingAdapter()
        armed = ArmingProvider(provider("REQUIRE_APPROVAL"), self.store)
        with self.assertRaises(SimulatedCrash):
            self.dispatcher(store=self.store, policy=armed).dispatch(
                self.request, adapter=adapter, approval_id=approval.approval_id, **self.kwargs()
            )
        execution = EffectReceiptRepository(self.store).get_execution(self.request.request_id)
        self.assertEqual(execution.state, EffectExecutionState.LEASED)
        self.assertEqual(execution.approval_id, approval.approval_id)
        self.assertEqual(
            ApprovalRepository(self.store).get(approval.approval_id).consumed_at,
            execution.leased_at,
        )
        self.store.close()
        self.store = SQLiteStateStore(self.db)
        self.dispatcher("REQUIRE_APPROVAL", at="2026-09-12T10:04:05+00:00").dispatch(
            self.request, adapter=adapter, approval_id=approval.approval_id, **self.kwargs("approval-recover")
        )
        self.assertEqual(adapter.invocations, 1)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id).approval_id,
            approval.approval_id,
        )

    def test_crash_during_invocation_leaves_prepared_and_reconciles_without_second_invoke(self):
        crashing = CrashDuringInvokeAdapter()
        with self.assertRaises(SimulatedCrash):
            self.dispatcher().dispatch(self.request, adapter=crashing, **self.kwargs())
        self.assertEqual(crashing.invocations, 1)
        execution = EffectReceiptRepository(self.store).get_execution(self.request.request_id)
        self.assertEqual(execution.state, EffectExecutionState.PREPARED)
        self.assertIsNone(EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id))
        self.store.close()
        self.store = SQLiteStateStore(self.db)
        reconciler = CountingAdapter()
        result = self.dispatcher(at="2026-09-12T10:04:05+00:00").dispatch(
            self.request, adapter=reconciler, **self.kwargs("reconcile")
        )
        self.assertEqual(result.request_id, self.request.request_id)
        self.assertEqual(reconciler.invocations, 0)
        self.assertEqual(reconciler.reconciliations, 1)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(self.request.request_id).state,
            EffectExecutionState.SUCCEEDED,
        )
        self.assertIn(
            "EFFECT_RECONCILED_SUCCEEDED",
            [e.event_type for e in AuditRepository(self.store).list_for_request(self.request.request_id)],
        )

    def test_emergency_pause_after_authority_commit_leaves_leased_not_receipt(self):
        self.store.close()
        self.store = CrashAfterAuthorityStore(self.db)
        adapter = CountingAdapter()
        class PauseArmingProvider(ArmingProvider):
            def evaluate(inner_self, request, *, decision_id, evaluated_at):
                # Reuse post-transaction hook to commit a pause instead of crashing.
                inner_self.store.crash_after_current_transaction = False
                value = inner_self.wrapped.evaluate(request, decision_id=decision_id, evaluated_at=evaluated_at)
                inner_self.store.crash_after_current_transaction = "pause"
                return value
        original_transaction = self.store.transaction
        @contextmanager
        def tx_with_pause():
            with SQLiteStateStore.transaction(self.store) as conn:
                yield conn
            if self.store.crash_after_current_transaction == "pause":
                self.store.crash_after_current_transaction = False
                EmergencyPauseRepository(self.store).pause()
        self.store.transaction = tx_with_pause
        armed = PauseArmingProvider(provider("ALLOW"), self.store)
        with self.assertRaises(DispatchPaused):
            self.dispatcher(store=self.store, policy=armed).dispatch(
                self.request, adapter=adapter, **self.kwargs()
            )
        self.assertEqual(adapter.invocations, 0)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(self.request.request_id).state,
            EffectExecutionState.LEASED,
        )
        self.assertIsNone(EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id))

    def test_corrupted_reconciliation_state_fails_closed(self):
        adapter = CrashDuringInvokeAdapter()
        with self.assertRaises(SimulatedCrash):
            self.dispatcher().dispatch(self.request, adapter=adapter, **self.kwargs())
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE effect_executions SET input_hash=? WHERE request_id=?",
                ("sha256:" + "f" * 64, self.request.request_id),
            )
        with self.assertRaises(DispatchAuthorityError):
            self.dispatcher(at="2026-09-12T10:04:05+00:00").dispatch(
                self.request, adapter=CountingAdapter(), **self.kwargs("corrupt")
            )


if __name__ == "__main__":
    unittest.main()
