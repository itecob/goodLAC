import tempfile
import unittest
from pathlib import Path

from packages.core import (
    EffectRequest,
    PolicyDecision,
    PolicyDecisionError,
    PolicyDecisionValue,
)
from packages.policy import (
    LocalPolicyDecisionProvider,
    PolicyConfigurationError,
    PolicyRule,
)
from packages.state import (
    EffectRequestRepository,
    PolicyDecisionBindingError,
    PolicyDecisionIdentityConflict,
    PolicyDecisionRepository,
    SQLiteStateStore,
    StateStoreError,
)


BASE_REQUEST = {
    "request_id": "effect:policy-001",
    "run_id": "run:policy-001",
    "principal_id": "principal:owner",
    "agent_id": "agent:test",
    "action": "simulated.write",
    "resource": "simulated:alpha",
    "arguments": {"value": 1},
    "idempotency_key": "idem:policy-001",
    "created_at": "2026-09-10T20:00:00Z",
    "expires_at": "2026-09-10T20:05:00Z",
}


def make_request(**overrides):
    return EffectRequest.create(**{**BASE_REQUEST, **overrides})


def make_rule(rule_id, decision, **overrides):
    values = {
        "rule_id": rule_id,
        "principal_id": "principal:owner",
        "agent_id": "agent:test",
        "action": "simulated.write",
        "resource": "simulated:alpha",
        "decision": decision,
    }
    values.update(overrides)
    return PolicyRule.create(**values)


def make_provider(*rules):
    return LocalPolicyDecisionProvider(
        revision="policy:test:v1",
        known_principals={"principal:owner"},
        known_agents={"agent:test"},
        known_actions={"simulated.write"},
        known_resources={"simulated:alpha"},
        rules=rules,
    )


def evaluate(provider, request=None, decision_id="decision:001"):
    return provider.evaluate(
        request or make_request(),
        decision_id=decision_id,
        evaluated_at="2026-09-10T20:00:01Z",
    )


class PolicyDecisionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "controller.db"

    def tearDown(self) -> None:
        self.tmp.cleanup()

    def test_decision_binds_request_id_and_canonical_hash(self) -> None:
        request = make_request()
        decision = evaluate(make_provider(make_rule("allow", "ALLOW")), request)
        self.assertEqual(decision.request_id, request.request_id)
        self.assertEqual(decision.canonical_request_hash, request.canonical_hash)
        self.assertEqual(decision.policy_revision, "policy:test:v1")

    def test_explicit_deny_wins_over_approval_and_allow(self) -> None:
        provider = make_provider(
            make_rule("z-allow", "ALLOW"),
            make_rule("a-approve", "REQUIRE_APPROVAL"),
            make_rule("m-deny", "DENY"),
        )
        decision = evaluate(provider)
        self.assertEqual(decision.decision, PolicyDecisionValue.DENY)
        self.assertIn("DENY_PRECEDENCE_APPLIED", decision.reason_codes)
        self.assertIn("DECISION:DENY", decision.reason_codes)

    def test_approval_required_wins_over_allow(self) -> None:
        provider = make_provider(
            make_rule("allow", "ALLOW"),
            make_rule("approve", "REQUIRE_APPROVAL"),
        )
        decision = evaluate(provider)
        self.assertEqual(decision.decision, PolicyDecisionValue.REQUIRE_APPROVAL)
        self.assertIn("APPROVAL_PRECEDENCE_APPLIED", decision.reason_codes)

    def test_no_matching_rule_fails_closed(self) -> None:
        decision = evaluate(make_provider())
        self.assertEqual(decision.decision, PolicyDecisionValue.DENY)
        self.assertEqual(decision.reason_codes, ("NO_MATCHING_RULE",))

    def test_unknown_authority_dimensions_fail_closed(self) -> None:
        provider = make_provider(make_rule("allow", "ALLOW"))
        cases = {
            "principal_id": ("principal:unknown", "UNKNOWN_PRINCIPAL"),
            "agent_id": ("agent:unknown", "UNKNOWN_AGENT"),
            "action": ("unknown.action", "UNKNOWN_ACTION"),
            "resource": ("unknown:resource", "UNKNOWN_RESOURCE"),
        }
        for field, (value, reason) in cases.items():
            with self.subTest(field=field):
                decision = evaluate(provider, make_request(**{field: value}))
                self.assertEqual(decision.decision, PolicyDecisionValue.DENY)
                self.assertIn(reason, decision.reason_codes)

    def test_rule_order_does_not_change_decision_or_reasons(self) -> None:
        rules = (
            make_rule("rule-b", "ALLOW"),
            make_rule("rule-a", "REQUIRE_APPROVAL"),
        )
        left = evaluate(make_provider(*rules), decision_id="decision:left")
        right = evaluate(make_provider(*reversed(rules)), decision_id="decision:right")
        self.assertEqual(left.decision, right.decision)
        self.assertEqual(left.reason_codes, right.reason_codes)

    def test_malformed_policy_configuration_fails_closed(self) -> None:
        with self.assertRaises(PolicyConfigurationError):
            make_rule("bad", "MAYBE")
        with self.assertRaises(PolicyConfigurationError):
            LocalPolicyDecisionProvider(
                revision="policy:test:v1",
                known_principals={"principal:owner"},
                known_agents={"agent:test"},
                known_actions={"simulated.write"},
                known_resources={"simulated:alpha"},
                rules=(make_rule("bad-ref", "ALLOW", action="unregistered.action"),),
            )

    def test_policy_decision_domain_rejects_bad_hash_and_reasons(self) -> None:
        with self.assertRaises(PolicyDecisionError):
            PolicyDecision.create(
                decision_id="decision:bad",
                request_id="effect:policy-001",
                decision="ALLOW",
                policy_revision="policy:test:v1",
                reason_codes=("RULE",),
                evaluated_at="2026-09-10T20:00:01Z",
                canonical_request_hash="not-a-hash",
            )
        with self.assertRaises(PolicyDecisionError):
            PolicyDecision.create(
                decision_id="decision:bad",
                request_id="effect:policy-001",
                decision="ALLOW",
                policy_revision="policy:test:v1",
                reason_codes=(),
                evaluated_at="2026-09-10T20:00:01Z",
                canonical_request_hash="sha256:" + ("0" * 64),
            )

    def test_persisted_policy_decision_survives_restart(self) -> None:
        request = make_request()
        decision = evaluate(make_provider(make_rule("allow", "ALLOW")), request)
        with SQLiteStateStore(self.db) as store:
            EffectRequestRepository(store).put(request)
            PolicyDecisionRepository(store).put(decision)

        with SQLiteStateStore(self.db) as reopened:
            loaded = PolicyDecisionRepository(reopened).get(decision.decision_id)
            self.assertEqual(loaded, decision)
            self.assertEqual(loaded.canonical_request_hash, request.canonical_hash)

    def test_decision_cannot_persist_without_durable_request(self) -> None:
        decision = evaluate(make_provider(make_rule("allow", "ALLOW")))
        with SQLiteStateStore(self.db) as store:
            with self.assertRaises(PolicyDecisionBindingError):
                PolicyDecisionRepository(store).put(decision)

    def test_decision_cannot_bind_wrong_request_hash(self) -> None:
        request = make_request()
        decision = evaluate(make_provider(make_rule("allow", "ALLOW")), request)
        wrong = PolicyDecision.create(
            decision_id=decision.decision_id,
            request_id=decision.request_id,
            decision=decision.decision,
            policy_revision=decision.policy_revision,
            reason_codes=decision.reason_codes,
            evaluated_at=decision.evaluated_at,
            canonical_request_hash="sha256:" + ("0" * 64),
        )
        with SQLiteStateStore(self.db) as store:
            EffectRequestRepository(store).put(request)
            with self.assertRaises(PolicyDecisionBindingError):
                PolicyDecisionRepository(store).put(wrong)

    def test_duplicate_decision_id_cannot_overwrite_different_decision(self) -> None:
        request = make_request()
        allow = evaluate(make_provider(make_rule("allow", "ALLOW")), request)
        deny = evaluate(
            make_provider(make_rule("deny", "DENY")),
            request,
            decision_id=allow.decision_id,
        )
        with SQLiteStateStore(self.db) as store:
            EffectRequestRepository(store).put(request)
            repo = PolicyDecisionRepository(store)
            repo.put(allow)
            with self.assertRaises(PolicyDecisionIdentityConflict):
                repo.put(deny)
            self.assertEqual(repo.get(allow.decision_id), allow)

    def test_corrupted_persisted_reason_codes_fail_closed(self) -> None:
        request = make_request()
        decision = evaluate(make_provider(make_rule("allow", "ALLOW")), request)
        with SQLiteStateStore(self.db) as store:
            EffectRequestRepository(store).put(request)
            repo = PolicyDecisionRepository(store)
            repo.put(decision)
            with store.transaction() as conn:
                conn.execute(
                    "UPDATE policy_decisions SET reason_codes_json = ? WHERE decision_id = ?",
                    ('["z","a"]', decision.decision_id),
                )
            with self.assertRaises(StateStoreError):
                repo.get(decision.decision_id)


if __name__ == "__main__":
    unittest.main()
