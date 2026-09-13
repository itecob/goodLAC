import tempfile
import unittest
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

from packages.core import EffectExecutionState, EffectRequest
from packages.dispatcher import (
    DispatchAgentRevoked,
    DispatchReconciliationRequired,
    DispatchRequestExpired,
    Dispatcher,
)
from packages.effects.simulated import SimulatedEffectAdapter
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    AgentIdentityRepository,
    EffectReceiptRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    SQLiteStateStore,
)


class SimulatedCrash(BaseException):
    pass


class SequenceClock:
    def __init__(self, *values):
        self.values = [datetime.fromisoformat(value) for value in values]
        self.index = 0

    def __call__(self):
        if self.index >= len(self.values):
            raise AssertionError("trusted clock called more times than the test authorizes")
        value = self.values[self.index]
        self.index += 1
        return value


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
            raise SimulatedCrash("process crash after durable LEASED transition")


class ArmingProvider:
    def __init__(self, wrapped, store):
        self.wrapped = wrapped
        self.store = store

    @property
    def policy_revision(self):
        return self.wrapped.policy_revision

    def evaluate(self, request, *, decision_id, evaluated_at):
        self.store.crash_after_current_transaction = True
        return self.wrapped.evaluate(
            request, decision_id=decision_id, evaluated_at=evaluated_at
        )


class RevokingAfterAuthorityStore(SQLiteStateStore):
    def __init__(self, path):
        self.revoke_after_current_transaction = False
        super().__init__(path)

    @contextmanager
    def transaction(self):
        with super().transaction() as conn:
            yield conn
        if self.revoke_after_current_transaction:
            self.revoke_after_current_transaction = False
            AgentIdentityRepository(self).revoke("agent:test")


class RevokeArmingProvider:
    def __init__(self, wrapped, store):
        self.wrapped = wrapped
        self.store = store

    @property
    def policy_revision(self):
        return self.wrapped.policy_revision

    def evaluate(self, request, *, decision_id, evaluated_at):
        self.store.revoke_after_current_transaction = True
        return self.wrapped.evaluate(
            request, decision_id=decision_id, evaluated_at=evaluated_at
        )


def make_request(
    *,
    request_id="effect:freshness-001",
    idempotency_key="idem:freshness-001",
    expires_at="2026-09-12T10:20:00Z",
):
    return EffectRequest.create(
        request_id=request_id,
        run_id="run:freshness",
        principal_id="principal:owner",
        agent_id="agent:test",
        action="simulated.write",
        resource="simulated:alpha",
        arguments={"value": 23},
        idempotency_key=idempotency_key,
        created_at="2026-09-12T10:00:00Z",
        expires_at=expires_at,
    )


def provider():
    return LocalPolicyDecisionProvider(
        revision="policy:freshness:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={"simulated.write"},
        known_resources={"simulated:alpha"},
        rules=(
            PolicyRule.create(
                rule_id="rule:freshness:allow",
                principal_id="principal:owner",
                agent_id="agent:test",
                action="simulated.write",
                resource="simulated:alpha",
                decision="ALLOW",
            ),
        ),
    )


class AuthorityFreshnessTests(unittest.TestCase):
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

    @staticmethod
    def kwargs(suffix="1"):
        return {
            "decision_id": f"decision:freshness:{suffix}",
            "lease_id": f"lease:freshness:{suffix}",
            "executor_id": "executor:freshness",
        }

    def dispatcher(self, clock, *, store=None, policy=None, lease_seconds=20):
        return Dispatcher(
            store=store or self.store,
            policy_provider=policy or provider(),
            clock=clock,
            lease_seconds=lease_seconds,
        )

    def test_lease_expiry_after_lease_transition_cannot_reach_adapter_or_revive_on_retry(self):
        adapter = CountingAdapter()
        clock = SequenceClock(
            "2026-09-12T10:04:00+00:00",
            "2026-09-12T10:04:20+00:00",
        )
        with self.assertRaises(DispatchReconciliationRequired):
            self.dispatcher(clock).dispatch(
                self.request, adapter=adapter, **self.kwargs()
            )
        self.assertEqual(adapter.invocations, 0)
        self.assertEqual(adapter.reconciliations, 0)
        execution = EffectReceiptRepository(self.store).get_execution(self.request.request_id)
        self.assertEqual(execution.state, EffectExecutionState.LEASED)
        self.assertIsNone(
            EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id)
        )

        retry = CountingAdapter()
        with self.assertRaises(DispatchReconciliationRequired):
            self.dispatcher(
                SequenceClock("2026-09-12T10:04:21+00:00")
            ).dispatch(self.request, adapter=retry, **self.kwargs("retry"))
        self.assertEqual(retry.invocations, 0)
        self.assertEqual(retry.reconciliations, 0)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(self.request.request_id).state,
            EffectExecutionState.LEASED,
        )

    def test_request_expiry_after_lease_transition_cannot_reach_adapter(self):
        expiring = make_request(
            request_id="effect:freshness-request-expiry",
            idempotency_key="idem:freshness-request-expiry",
            expires_at="2026-09-12T10:04:05Z",
        )
        EffectRequestRepository(self.store).put(expiring)
        adapter = CountingAdapter()
        with self.assertRaises(DispatchRequestExpired):
            self.dispatcher(
                SequenceClock(
                    "2026-09-12T10:04:00+00:00",
                    "2026-09-12T10:04:05+00:00",
                ),
                lease_seconds=30,
            ).dispatch(expiring, adapter=adapter, **self.kwargs("request-expiry"))
        self.assertEqual(adapter.invocations, 0)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(expiring.request_id).state,
            EffectExecutionState.LEASED,
        )
        self.assertIsNone(EffectReceiptRepository(self.store).get_receipt_for_request(expiring.request_id))

    def test_leased_recovery_rechecks_fresh_time_before_new_invocation(self):
        self.store.close()
        self.store = CrashAfterAuthorityStore(self.db)
        adapter = CountingAdapter()
        armed = ArmingProvider(provider(), self.store)
        with self.assertRaises(SimulatedCrash):
            self.dispatcher(
                SequenceClock("2026-09-12T10:04:00+00:00"),
                store=self.store,
                policy=armed,
            ).dispatch(self.request, adapter=adapter, **self.kwargs())
        self.assertEqual(adapter.invocations, 0)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(self.request.request_id).state,
            EffectExecutionState.LEASED,
        )

        recovery = CountingAdapter()
        with self.assertRaises(DispatchReconciliationRequired):
            self.dispatcher(
                SequenceClock(
                    "2026-09-12T10:04:05+00:00",
                    "2026-09-12T10:04:20+00:00",
                ),
                store=self.store,
            ).dispatch(self.request, adapter=recovery, **self.kwargs("recover"))
        self.assertEqual(recovery.invocations, 0)
        self.assertEqual(recovery.reconciliations, 0)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(self.request.request_id).state,
            EffectExecutionState.LEASED,
        )

        with self.assertRaises(DispatchReconciliationRequired):
            self.dispatcher(
                SequenceClock("2026-09-12T10:04:21+00:00"),
                store=self.store,
            ).dispatch(self.request, adapter=recovery, **self.kwargs("recover-again"))
        self.assertEqual(recovery.invocations, 0)

    def test_revocation_after_authority_commit_still_blocks_final_invocation(self):
        self.store.close()
        self.store = RevokingAfterAuthorityStore(self.db)
        adapter = CountingAdapter()
        armed = RevokeArmingProvider(provider(), self.store)
        with self.assertRaises(DispatchAgentRevoked):
            self.dispatcher(
                SequenceClock(
                    "2026-09-12T10:04:00+00:00",
                    "2026-09-12T10:04:01+00:00",
                ),
                store=self.store,
                policy=armed,
            ).dispatch(self.request, adapter=adapter, **self.kwargs("revoked-late"))
        self.assertEqual(adapter.invocations, 0)
        self.assertEqual(adapter.reconciliations, 0)
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(self.request.request_id).state,
            EffectExecutionState.LEASED,
        )
        self.assertIsNone(
            EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id)
        )

    def test_nonexpired_dispatch_succeeds_and_terminal_timestamp_is_fresh(self):
        adapter = CountingAdapter()
        result = self.dispatcher(
            SequenceClock(
                "2026-09-12T10:04:00+00:00",
                "2026-09-12T10:04:01+00:00",
                "2026-09-12T10:04:09+00:00",
            )
        ).dispatch(self.request, adapter=adapter, **self.kwargs())
        self.assertEqual(result.request_id, self.request.request_id)
        self.assertEqual(adapter.invocations, 1)
        receipt = EffectReceiptRepository(self.store).get_receipt_for_request(self.request.request_id)
        self.assertEqual(receipt.completed_at, "2026-09-12T10:04:09.000000Z")
        self.assertEqual(
            EffectReceiptRepository(self.store).get_execution(self.request.request_id).state,
            EffectExecutionState.SUCCEEDED,
        )


if __name__ == "__main__":
    unittest.main()
