import tempfile
import unittest
from datetime import datetime
from pathlib import Path

from packages.core import EffectRequest
from packages.dispatcher import DispatchAgentRevoked, DispatchDenied, Dispatcher
from packages.effects.simulated import SimulatedEffectAdapter
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import (
    AgentIdentityRepository,
    EffectReceiptRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    ExecutionLeaseRepository,
    PolicyDecisionRepository,
    SQLiteStateStore,
)


class CountingAdapter(SimulatedEffectAdapter):
    def __init__(self):
        self.invocations = 0

    def invoke(self, request, *, lease):
        self.invocations += 1
        return super().invoke(request, lease=lease)


def fixed_clock():
    observed = datetime.fromisoformat("2026-09-12T10:04:00+00:00")
    return lambda: observed


def make_request(agent_id="agent:test", *, suffix="test"):
    return EffectRequest.create(
        request_id=f"effect:acceptance:{suffix}",
        run_id="run:acceptance",
        principal_id="principal:owner",
        agent_id=agent_id,
        action="simulated.write",
        resource="simulated:alpha",
        arguments={"value": 31},
        idempotency_key=f"idem:acceptance:{suffix}",
        created_at="2026-09-12T10:00:00Z",
        expires_at="2026-09-12T10:20:00Z",
    )


def provider():
    return LocalPolicyDecisionProvider(
        revision="policy:acceptance:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={"simulated.write"},
        known_resources={"simulated:alpha"},
        rules=(
            PolicyRule.create(
                rule_id="rule:acceptance:allow",
                principal_id="principal:owner",
                agent_id="agent:test",
                action="simulated.write",
                resource="simulated:alpha",
                decision="ALLOW",
            ),
        ),
    )


class Phase1AuthorizationAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"
        self.store = SQLiteStateStore(self.db)
        EmergencyPauseRepository(self.store).resume()

    def tearDown(self):
        try:
            self.store.close()
        finally:
            self.tmp.cleanup()

    def dispatcher(self):
        return Dispatcher(
            store=self.store,
            policy_provider=provider(),
            clock=fixed_clock(),
            lease_seconds=20,
        )

    def test_revoked_agent_cannot_act(self):
        identities = AgentIdentityRepository(self.store)
        identities.register_active("agent:test", "principal:owner")
        identities.revoke("agent:test")
        request = make_request()
        EffectRequestRepository(self.store).put(request)

        self.store.close()
        self.store = SQLiteStateStore(self.db)
        adapter = CountingAdapter()
        with self.assertRaises(DispatchAgentRevoked):
            self.dispatcher().dispatch(
                request,
                adapter=adapter,
                decision_id="decision:acceptance:revoked",
                lease_id="lease:acceptance:revoked",
                executor_id="executor:acceptance",
            )
        self.assertEqual(adapter.invocations, 0)
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:acceptance:revoked"))
        self.assertIsNone(EffectReceiptRepository(self.store).get_execution(request.request_id))

    def test_unknown_agent_preserves_policy_deny_behavior(self):
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")
        request = make_request("agent:unknown", suffix="unknown")
        EffectRequestRepository(self.store).put(request)
        adapter = CountingAdapter()
        with self.assertRaises(DispatchDenied):
            self.dispatcher().dispatch(
                request,
                adapter=adapter,
                decision_id="decision:acceptance:unknown",
                lease_id="lease:acceptance:unknown",
                executor_id="executor:acceptance",
            )
        self.assertEqual(adapter.invocations, 0)
        decision = PolicyDecisionRepository(self.store).get("decision:acceptance:unknown")
        self.assertEqual(decision.decision.value, "DENY")
        self.assertIn("UNKNOWN_AGENT", decision.reason_codes)
        self.assertIsNone(ExecutionLeaseRepository(self.store).get("lease:acceptance:unknown"))


if __name__ == "__main__":
    unittest.main()
