import tempfile
import unittest
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from packages.core import Approval, EffectRequest, ExecutionLease, PolicyDecision
from packages.dispatcher import (
    DispatchAdapterError,
    DispatchApprovalRequired,
    DispatchAuthorityError,
    DispatchDenied,
    DispatchRequestExpired,
    Dispatcher,
)
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    ApprovalRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    ExecutionLeaseRepository,
    PolicyDecisionRepository,
    SCHEMA_VERSION,
    SQLiteStateStore,
)


REQUEST_VALUES = {
    "request_id": "effect:dispatch-001",
    "run_id": "run:dispatch-001",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": "simulated.write",
    "resource": "simulated:alpha",
    "arguments": {"value": 7},
    "idempotency_key": "idem:dispatch-001",
    "created_at": "2026-09-12T10:00:00Z",
    "expires_at": "2026-09-12T10:20:00Z",
}


def make_request(**overrides):
    return EffectRequest.create(**{**REQUEST_VALUES, **overrides})


def make_provider(decision, revision="policy:current:v2"):
    return LocalPolicyDecisionProvider(
        revision=revision,
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={"simulated.write"},
        known_resources={"simulated:alpha"},
        rules=(
            PolicyRule.create(
                rule_id=f"rule:{decision.lower()}",
                principal_id="principal:owner",
                agent_id="agent:test",
                action="simulated.write",
                resource="simulated:alpha",
                decision=decision,
            ),
        ),
    )


def fixed_clock(value="2026-09-12T10:04:00+00:00"):
    observed = datetime.fromisoformat(value)
    return lambda: observed


def persist_approval_foundation(store, request, **approval_overrides):
    decision = PolicyDecision.create(
        decision_id="decision:approval-foundation",
        request_id=request.request_id,
        decision="REQUIRE_APPROVAL",
        policy_revision="policy:approval:v1",
        reason_codes=("DECISION:REQUIRE_APPROVAL",),
        evaluated_at="2026-09-12T10:00:01Z",
        canonical_request_hash=request.canonical_hash,
    )
    values = {
        "approval_id": "approval:dispatch-001",
        "request_id": request.request_id,
        "policy_decision_id": decision.decision_id,
        "canonical_request_hash": request.canonical_hash,
        "approver": "principal:owner",
        "decision": "APPROVE",
        "scope": "ONCE",
        "created_at": "2026-09-12T10:00:02Z",
        "expires_at": "2026-09-12T10:10:00Z",
    }
    values.update(approval_overrides)
    approval = Approval.create(**values)
    PolicyDecisionRepository(store).put(decision)
    ApprovalRepository(store).put(approval)
    return decision, approval


class RecordingPolicyProvider:
    def __init__(self, provider, events):
        self.provider = provider
        self.events = events

    @property
    def policy_revision(self):
        return self.provider.policy_revision

    def evaluate(self, request, *, decision_id, evaluated_at):
        self.events.append("policy.evaluate")
        return self.provider.evaluate(
            request, decision_id=decision_id, evaluated_at=evaluated_at
        )


class RecordingAdapter:
    def __init__(self, store, *, events=None, supported=True, raise_on_invoke=False):
        self._store = store
        self._events = events
        self._supported = supported
        self._raise_on_invoke = raise_on_invoke
        self.calls = []
        self.state_seen_at_invoke = None

    @property
    def adapter_id(self):
        return "adapter:test"

    def supports(self, request):
        return self._supported

    def invoke(self, request, *, lease):
        if self._events is not None:
            self._events.append("adapter.invoke")
        self.calls.append((request, lease))
        self.state_seen_at_invoke = {
            "lease": ExecutionLeaseRepository(self._store).get(lease.lease_id),
            "approval_consumed": self._store._conn.execute(
                "SELECT consumed_at FROM approvals WHERE request_id = ? ORDER BY approval_id LIMIT 1",
                (request.request_id,),
            ).fetchone(),
            "current_policy_decision": self._store._conn.execute(
                "SELECT decision FROM policy_decisions WHERE decision_id = ?",
                ("decision:dispatch-current",),
            ).fetchone(),
        }
        if self._raise_on_invoke:
            raise RuntimeError("test adapter failure")
        return {"adapter": self.adapter_id, "lease_id": lease.lease_id}


class BadPolicyProvider:
    @property
    def policy_revision(self):
        return "policy:bad:v1"

    def evaluate(self, request, *, decision_id, evaluated_at):
        return object()


class DispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        EmergencyPauseRepository(self.store).resume()
        self.request = make_request()
        EffectRequestRepository(self.store).put(self.request)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def dispatcher(self, decision="ALLOW", **overrides):
        values = {
            "store": self.store,
            "policy_provider": make_provider(decision),
            "clock": fixed_clock(),
            "lease_seconds": 20,
        }
        values.update(overrides)
        return Dispatcher(**values)

    def dispatch_kwargs(self, **overrides):
        values = {
            "decision_id": "decision:dispatch-current",
            "lease_id": "lease:dispatch-001",
            "executor_id": "executor:test",
        }
        values.update(overrides)
        return values

    def test_allow_rechecks_current_policy_persists_decision_leases_then_invokes(self):
        events = []
        provider = RecordingPolicyProvider(make_provider("ALLOW"), events)
        adapter = RecordingAdapter(self.store, events=events)
        result = Dispatcher(
            store=self.store,
            policy_provider=provider,
            clock=fixed_clock(),
            lease_seconds=20,
        ).dispatch(self.request, adapter=adapter, **self.dispatch_kwargs())
        self.assertEqual(result["lease_id"], "lease:dispatch-001")
        self.assertEqual(events, ["policy.evaluate", "adapter.invoke"])
        self.assertEqual(len(adapter.calls), 1)
        decision = PolicyDecisionRepository(self.store).get("decision:dispatch-current")
        self.assertEqual(decision.decision.value, "ALLOW")
        self.assertEqual(decision.evaluated_at, "2026-09-12T10:04:00.000000Z")
        lease = ExecutionLeaseRepository(self.store).get("lease:dispatch-001")
        self.assertIsNotNone(lease)
        self.assertEqual(lease.issued_at, "2026-09-12T10:04:00.000000Z")
        self.assertEqual(lease.expires_at, "2026-09-12T10:04:20.000000Z")
        self.assertEqual(adapter.state_seen_at_invoke["lease"], lease)
        self.assertEqual(adapter.state_seen_at_invoke["current_policy_decision"][0], "ALLOW")

    def test_current_deny_never_reaches_adapter_and_is_durable(self):
        _, approval = persist_approval_foundation(self.store, self.request)
        adapter = RecordingAdapter(self.store)
        with self.assertRaises(DispatchDenied):
            self.dispatcher("DENY").dispatch(
                self.request,
                adapter=adapter,
                approval_id=approval.approval_id,
                **self.dispatch_kwargs(),
            )
        self.assertEqual(adapter.calls, [])
        self.assertEqual(
            PolicyDecisionRepository(self.store)
            .get("decision:dispatch-current")
            .decision.value,
            "DENY",
        )
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:dispatch-001"))
        self.assertIsNone(ApprovalRepository(self.store).get(approval.approval_id).consumed_at)

    def test_require_approval_without_exact_approval_never_leases_or_invokes(self):
        adapter = RecordingAdapter(self.store)
        with self.assertRaises(DispatchApprovalRequired):
            self.dispatcher("REQUIRE_APPROVAL").dispatch(
                self.request, adapter=adapter, **self.dispatch_kwargs()
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:dispatch-001"))
        self.assertEqual(
            PolicyDecisionRepository(self.store)
            .get("decision:dispatch-current")
            .decision.value,
            "REQUIRE_APPROVAL",
        )

    def test_exact_approval_is_consumed_once_before_adapter_and_cannot_be_reused(self):
        _, approval = persist_approval_foundation(self.store, self.request)
        adapter = RecordingAdapter(self.store)
        self.dispatcher("REQUIRE_APPROVAL").dispatch(
            self.request,
            adapter=adapter,
            approval_id=approval.approval_id,
            **self.dispatch_kwargs(),
        )
        consumed = ApprovalRepository(self.store).get(approval.approval_id)
        self.assertEqual(consumed.consumed_at, "2026-09-12T10:04:00.000000Z")
        self.assertEqual(len(adapter.calls), 1)
        self.assertEqual(
            adapter.state_seen_at_invoke["approval_consumed"][0],
            "2026-09-12T10:04:00.000000Z",
        )

        second = RecordingAdapter(self.store)
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
                    decision_id="decision:dispatch-second",
                    lease_id="lease:dispatch-002",
                ),
            )
        self.assertEqual(second.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:dispatch-002"))

    def test_expired_approval_fails_closed_without_consumption_or_lease(self):
        _, approval = persist_approval_foundation(
            self.store, self.request, expires_at="2026-09-12T10:04:00Z"
        )
        adapter = RecordingAdapter(self.store)
        with self.assertRaises(DispatchAuthorityError):
            self.dispatcher("REQUIRE_APPROVAL").dispatch(
                self.request,
                adapter=adapter,
                approval_id=approval.approval_id,
                **self.dispatch_kwargs(),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ApprovalRepository(self.store).get(approval.approval_id).consumed_at)
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:dispatch-001"))

    def test_competing_lease_blocks_adapter_and_rolls_back_approval_consumption(self):
        _, approval = persist_approval_foundation(self.store, self.request)
        ExecutionLeaseRepository(self.store).acquire(
            ExecutionLease.create(
                lease_id="lease:preexisting",
                request_id=self.request.request_id,
                executor_id="executor:other",
                issued_at="2026-09-12T10:03:50Z",
                expires_at="2026-09-12T10:04:30Z",
            )
        )
        adapter = RecordingAdapter(self.store)
        with self.assertRaises(DispatchAuthorityError):
            self.dispatcher("REQUIRE_APPROVAL").dispatch(
                self.request,
                adapter=adapter,
                approval_id=approval.approval_id,
                **self.dispatch_kwargs(),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ApprovalRepository(self.store).get(approval.approval_id).consumed_at)
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:dispatch-001"))
        self.assertIsNotNone(
            PolicyDecisionRepository(self.store).get("decision:dispatch-current")
        )

    def test_request_expiry_uses_trusted_clock_and_fails_closed(self):
        expired = make_request(
            request_id="effect:expired",
            idempotency_key="idem:expired",
            expires_at="2026-09-12T10:04:00Z",
        )
        EffectRequestRepository(self.store).put(expired)
        adapter = RecordingAdapter(self.store)
        with self.assertRaises(DispatchRequestExpired):
            self.dispatcher("ALLOW").dispatch(
                expired,
                adapter=adapter,
                **self.dispatch_kwargs(decision_id="decision:expired", lease_id="lease:expired"),
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:expired"))
        self.assertEqual(
            PolicyDecisionRepository(self.store).get("decision:expired").decision.value,
            "ALLOW",
        )

    def test_mutated_current_request_fails_closed_before_policy_or_adapter(self):
        mutated = make_request(arguments={"value": 999})
        adapter = RecordingAdapter(self.store)
        with self.assertRaises(DispatchAuthorityError):
            self.dispatcher("ALLOW").dispatch(
                mutated, adapter=adapter, **self.dispatch_kwargs()
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(
            PolicyDecisionRepository(self.store).get("decision:dispatch-current")
        )

    def test_forged_current_request_hash_fails_closed(self):
        forged = replace(self.request, canonical_hash="sha256:" + ("f" * 64))
        adapter = RecordingAdapter(self.store)
        with self.assertRaises(DispatchAuthorityError):
            self.dispatcher("ALLOW").dispatch(
                forged, adapter=adapter, **self.dispatch_kwargs()
            )
        self.assertEqual(adapter.calls, [])

    def test_malformed_policy_output_fails_closed(self):
        adapter = RecordingAdapter(self.store)
        with self.assertRaises(DispatchAuthorityError):
            Dispatcher(
                store=self.store,
                policy_provider=BadPolicyProvider(),
                clock=fixed_clock(),
            ).dispatch(self.request, adapter=adapter, **self.dispatch_kwargs())
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:dispatch-001"))

    def test_unknown_or_unsupported_adapter_fails_closed(self):
        adapter = RecordingAdapter(self.store, supported=False)
        with self.assertRaises(DispatchAdapterError):
            self.dispatcher("ALLOW").dispatch(
                self.request, adapter=adapter, **self.dispatch_kwargs()
            )
        self.assertEqual(adapter.calls, [])
        self.assertIsNone(
            PolicyDecisionRepository(self.store).get("decision:dispatch-current")
        )

    def test_invalid_trusted_clock_and_lease_configuration_fail_closed(self):
        with self.assertRaises(DispatchAuthorityError):
            Dispatcher(
                store=self.store,
                policy_provider=make_provider("ALLOW"),
                clock=lambda: datetime(2026, 9, 12, 10, 4, 0),
            ).dispatch(
                self.request,
                adapter=RecordingAdapter(self.store),
                **self.dispatch_kwargs(),
            )
        with self.assertRaises(Exception):
            Dispatcher(
                store=self.store,
                policy_provider=make_provider("ALLOW"),
                lease_seconds=301,
            )

    def test_adapter_failure_occurs_only_after_durable_lease_and_remains_fail_closed(self):
        adapter = RecordingAdapter(self.store, raise_on_invoke=True)
        with self.assertRaises(DispatchAdapterError):
            self.dispatcher("ALLOW").dispatch(
                self.request, adapter=adapter, **self.dispatch_kwargs()
            )
        self.assertEqual(len(adapter.calls), 1)
        self.assertIsNotNone(ExecutionLeaseRepository(self.store).get("lease:dispatch-001"))

    def test_lease_is_clamped_to_request_expiry(self):
        near_expiry = make_request(
            request_id="effect:near-expiry",
            idempotency_key="idem:near-expiry",
            expires_at="2026-09-12T10:04:05Z",
        )
        EffectRequestRepository(self.store).put(near_expiry)
        adapter = RecordingAdapter(self.store)
        self.dispatcher("ALLOW", lease_seconds=30).dispatch(
            near_expiry,
            adapter=adapter,
            **self.dispatch_kwargs(decision_id="decision:near", lease_id="lease:near"),
        )
        lease = ExecutionLeaseRepository(self.store).get("lease:near")
        self.assertEqual(lease.expires_at, "2026-09-12T10:04:05.000000Z")

    def test_no_schema_migration_or_concrete_adapter_is_introduced(self):
        self.assertEqual(SCHEMA_VERSION, 5)
        self.assertEqual(self.store.schema_version, 5)
        self.assertEqual(
            {name for name in dir(ApprovalRepository) if not name.startswith("_")},
            {"get", "put"},
        )
        self.assertEqual(
            {name for name in dir(ExecutionLeaseRepository) if not name.startswith("_")},
            {"acquire", "get"},
        )


if __name__ == "__main__":
    unittest.main()
