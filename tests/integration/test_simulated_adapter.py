import tempfile
import unittest
from dataclasses import replace
from datetime import datetime
from pathlib import Path

from packages.core import Approval, EffectRequest, ExecutionLease, PolicyDecision
from packages.dispatcher import (
    DispatchAdapterError,
    DispatchApprovalRequired,
    DispatchAuthorityError,
    DispatchDenied,
    Dispatcher,
    EffectAdapter,
)
from packages.effects.simulated import (
    SIMULATED_ACTION,
    SIMULATED_ADAPTER_ID,
    SIMULATED_RESOURCE,
    SIMULATED_RESULT_SCHEMA,
    SimulatedEffectAdapter,
    SimulatedEffectError,
)
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    ApprovalRepository,
    EffectRequestRepository,
    ExecutionLeaseRepository,
    PolicyDecisionRepository,
    SCHEMA_VERSION,
    SQLiteStateStore,
)


REQUEST_VALUES = {
    "request_id": "effect:simulated-001",
    "run_id": "run:simulated-001",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": SIMULATED_ACTION,
    "resource": SIMULATED_RESOURCE,
    "arguments": {"value": 7},
    "idempotency_key": "idem:simulated-001",
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
        revision=f"policy:c008:{decision.lower()}:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={SIMULATED_ACTION},
        known_resources={SIMULATED_RESOURCE},
        rules=(
            PolicyRule.create(
                rule_id=f"rule:c008:{decision.lower()}",
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
        decision_id="decision:c008:approval-foundation",
        request_id=request.request_id,
        decision="REQUIRE_APPROVAL",
        policy_revision="policy:c008:approval-foundation:v1",
        reason_codes=("DECISION:REQUIRE_APPROVAL",),
        evaluated_at="2026-09-12T10:00:01Z",
        canonical_request_hash=request.canonical_hash,
    )
    approval = Approval.create(
        approval_id="approval:c008:001",
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
    return approval


class StateObservingSimulatedAdapter(SimulatedEffectAdapter):
    def __init__(self, store):
        self._store = store
        self.calls = []
        self.state_seen = []

    def invoke(self, request, *, lease):
        approval_row = self._store._conn.execute(
            "SELECT consumed_at FROM approvals WHERE request_id = ? ORDER BY approval_id LIMIT 1",
            (request.request_id,),
        ).fetchone()
        decision_row = self._store._conn.execute(
            "SELECT decision FROM policy_decisions WHERE request_id = ? ORDER BY evaluated_at DESC, decision_id DESC LIMIT 1",
            (request.request_id,),
        ).fetchone()
        durable_lease = ExecutionLeaseRepository(self._store).get(lease.lease_id)
        self.calls.append((request, lease))
        self.state_seen.append(
            {
                "approval_consumed_at": None if approval_row is None else approval_row[0],
                "decision": None if decision_row is None else decision_row[0],
                "lease": durable_lease,
            }
        )
        return super().invoke(request, lease=lease)


class SimulatedAdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        self.request = make_request()
        EffectRequestRepository(self.store).put(self.request)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def dispatcher(self, decision):
        return Dispatcher(
            store=self.store,
            policy_provider=make_provider(decision),
            clock=fixed_clock(),
            lease_seconds=20,
        )

    @staticmethod
    def dispatch_kwargs(**overrides):
        values = {
            "decision_id": "decision:c008:current",
            "lease_id": "lease:c008:001",
            "executor_id": "executor:c008",
        }
        values.update(overrides)
        return values

    def test_adapter_implements_protocol_and_exact_support_contract(self):
        adapter = SimulatedEffectAdapter()
        self.assertIsInstance(adapter, EffectAdapter)
        self.assertEqual(adapter.adapter_id, SIMULATED_ADAPTER_ID)
        self.assertTrue(adapter.supports(self.request))

        unsupported = (
            make_request(request_id="effect:bad-action", idempotency_key="idem:bad-action", action="simulated.other"),
            make_request(request_id="effect:bad-resource", idempotency_key="idem:bad-resource", resource="simulated:other"),
            make_request(request_id="effect:extra-arg", idempotency_key="idem:extra-arg", arguments={"value": 7, "other": 1}),
            make_request(request_id="effect:bool", idempotency_key="idem:bool", arguments={"value": True}),
            make_request(request_id="effect:string", idempotency_key="idem:string", arguments={"value": "7"}),
            replace(self.request, canonical_hash="sha256:" + ("f" * 64)),
        )
        for request in unsupported:
            with self.subTest(request_id=request.request_id):
                self.assertFalse(adapter.supports(request))

    def test_direct_invoke_is_stateless_deterministic_and_lease_bound(self):
        adapter = SimulatedEffectAdapter()
        lease = ExecutionLease.create(
            lease_id="lease:direct",
            request_id=self.request.request_id,
            executor_id="executor:direct",
            issued_at="2026-09-12T10:04:00Z",
            expires_at="2026-09-12T10:04:20Z",
        )
        first = adapter.invoke(self.request, lease=lease)
        second = adapter.invoke(self.request, lease=lease)
        self.assertEqual(first, second)
        self.assertEqual(first.schema, SIMULATED_RESULT_SCHEMA)
        self.assertEqual(first.canonical_request_hash, self.request.canonical_hash)
        self.assertEqual(first.lease_id, lease.lease_id)
        self.assertEqual(first.executor_id, lease.executor_id)
        self.assertEqual(first.simulated_value, 7)
        self.assertTrue(first.lease_hash.startswith("sha256:"))
        self.assertTrue(first.result_hash.startswith("sha256:"))

        wrong_lease = ExecutionLease.create(
            lease_id="lease:wrong",
            request_id="effect:other",
            executor_id="executor:direct",
            issued_at="2026-09-12T10:04:00Z",
            expires_at="2026-09-12T10:04:20Z",
        )
        with self.assertRaises(SimulatedEffectError):
            adapter.invoke(self.request, lease=wrong_lease)
        with self.assertRaises(SimulatedEffectError):
            adapter.invoke(
                make_request(
                    request_id="effect:unsupported",
                    idempotency_key="idem:unsupported",
                    arguments={"value": 7, "other": 1},
                ),
                lease=lease,
            )

    def test_allow_reaches_concrete_adapter_only_after_policy_and_lease(self):
        adapter = StateObservingSimulatedAdapter(self.store)
        result = self.dispatcher("ALLOW").dispatch(
            self.request,
            adapter=adapter,
            **self.dispatch_kwargs(),
        )
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(result.adapter_id, SIMULATED_ADAPTER_ID)
        self.assertEqual(result.canonical_request_hash, self.request.canonical_hash)
        self.assertEqual(result.lease_id, "lease:c008:001")
        self.assertEqual(adapter.state_seen[0]["decision"], "ALLOW")
        self.assertEqual(
            adapter.state_seen[0]["lease"],
            ExecutionLeaseRepository(self.store).get("lease:c008:001"),
        )
        self.assertIsNone(adapter.state_seen[0]["approval_consumed_at"])

    def test_deny_never_invokes_concrete_adapter(self):
        adapter = StateObservingSimulatedAdapter(self.store)
        with self.assertRaises(DispatchDenied):
            self.dispatcher("DENY").dispatch(
                self.request,
                adapter=adapter,
                **self.dispatch_kwargs(),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:c008:001"))

    def test_require_approval_without_exact_approval_never_invokes(self):
        adapter = StateObservingSimulatedAdapter(self.store)
        with self.assertRaises(DispatchApprovalRequired):
            self.dispatcher("REQUIRE_APPROVAL").dispatch(
                self.request,
                adapter=adapter,
                **self.dispatch_kwargs(),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:c008:001"))

    def test_exact_one_time_approval_is_consumed_and_leased_before_invoke(self):
        approval = persist_approval_foundation(self.store, self.request)
        adapter = StateObservingSimulatedAdapter(self.store)
        result = self.dispatcher("REQUIRE_APPROVAL").dispatch(
            self.request,
            adapter=adapter,
            approval_id=approval.approval_id,
            **self.dispatch_kwargs(),
        )
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(result.request_id, self.request.request_id)
        self.assertEqual(
            adapter.state_seen[0]["approval_consumed_at"],
            "2026-09-12T10:04:00.000000Z",
        )
        self.assertEqual(adapter.state_seen[0]["decision"], "REQUIRE_APPROVAL")
        self.assertIsNotNone(adapter.state_seen[0]["lease"])

        second = StateObservingSimulatedAdapter(self.store)
        with self.assertRaises(DispatchAuthorityError):
            Dispatcher(
                store=self.store,
                policy_provider=make_provider("REQUIRE_APPROVAL"),
                clock=fixed_clock("2026-09-12T10:04:30+00:00"),
                lease_seconds=20,
            ).dispatch(
                self.request,
                adapter=second,
                approval_id=approval.approval_id,
                **self.dispatch_kwargs(
                    decision_id="decision:c008:second",
                    lease_id="lease:c008:002",
                ),
            )
        self.assertEqual(second.calls, [])

    def test_invalid_authority_and_unsupported_shape_never_invoke(self):
        adapter = StateObservingSimulatedAdapter(self.store)
        mutated = make_request(arguments={"value": 8})
        with self.assertRaises(DispatchAuthorityError):
            self.dispatcher("ALLOW").dispatch(
                mutated,
                adapter=adapter,
                **self.dispatch_kwargs(),
            )
        self.assertEqual(adapter.calls, [])

        unsupported = make_request(
            request_id="effect:unsupported-shape",
            idempotency_key="idem:unsupported-shape",
            arguments={"value": 7, "extra": 1},
        )
        EffectRequestRepository(self.store).put(unsupported)
        with self.assertRaises(DispatchAdapterError):
            self.dispatcher("ALLOW").dispatch(
                unsupported,
                adapter=adapter,
                **self.dispatch_kwargs(
                    decision_id="decision:c008:unsupported",
                    lease_id="lease:c008:unsupported",
                ),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(
            PolicyDecisionRepository(self.store).get("decision:c008:unsupported")
        )
        self.assertIsNone(
            ExecutionLeaseRepository(self.store).get("lease:c008:unsupported")
        )

    def test_c008_introduces_no_schema_migration(self):
        self.assertEqual(SCHEMA_VERSION, 5)
        self.assertEqual(self.store.schema_version, 5)


if __name__ == "__main__":
    unittest.main()
