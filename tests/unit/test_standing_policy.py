import json
import tempfile
import unittest
from pathlib import Path

from packages.capabilities import (
    CAPABILITY_MANIFEST_SCHEMA,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilityRequestContext,
    CapabilityRequestValidator,
)
from packages.core import EffectRequest, PolicyDecisionValue
from packages.policy import (
    StandingPolicyCondition,
    StandingPolicyDecisionProvider,
    StandingPolicyDefault,
    StandingPolicyIntegrityError,
    StandingPolicyRepository,
    StandingPolicyRule,
)
from packages.state import SQLiteStateStore


def manifest_fixture():
    arg_schema = {
        "type": "object",
        "properties": {
            "document_id": {"type": "string", "minLength": 1, "maxLength": 128},
            "destructive": {"type": "boolean"},
        },
        "required": ["document_id", "destructive"],
        "additionalProperties": False,
    }
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "test-app",
        "skill_id": "documents",
        "actions": [
            {
                "action": "document.read",
                "resource": {"type": "document.local", "selectors": ["document:workspace"]},
                "arguments": arg_schema,
                "security_properties": ["read_only"],
            },
            {
                "action": "document.write",
                "resource": {"type": "document.local", "selectors": ["document:workspace"]},
                "arguments": arg_schema,
                "security_properties": ["local_mutation"],
            },
            {
                "action": "document.delete",
                "resource": {"type": "document.local", "selectors": ["document:workspace"]},
                "arguments": arg_schema,
                "security_properties": ["destructive", "local_mutation"],
            },
        ],
    }


def request_fixture(name, *, action="document.read", destructive=False):
    return EffectRequest.create(
        request_id=f"effect:p003:{name}",
        run_id="run:p003",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=action,
        resource="document:workspace",
        arguments={"document_id": "doc-1", "destructive": destructive},
        idempotency_key=f"idem:p003:{name}",
        created_at="2026-09-15T17:00:00.000000Z",
        expires_at="2026-09-15T17:10:00.000000Z",
    )


class StandingPolicyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStateStore(Path(self.tmp.name) / "controller.db")
        registration = CapabilityRegistry(self.store).register_admin(
            CapabilityManifest.create(manifest_fixture())
        )
        self.context = CapabilityRequestContext(
            application_id="test-app",
            skill_id="documents",
            capability_revision=registration.revision,
            manifest_version=1,
            resource_type="document.local",
        )
        self.repo = StandingPolicyRepository(self.store)
        self.provider = StandingPolicyDecisionProvider(self.store)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def validation(self, request):
        return CapabilityRequestValidator(self.store).validate_or_quarantine(
            request,
            context=self.context,
            observed_at_utc="2026-09-15T17:00:01.000000Z",
        )

    def evaluate(self, request, *, decision_id="decision:p003"):
        return self.provider.evaluate_capability(
            request,
            capability_context=self.context,
            capability_validation=self.validation(request),
            decision_id=decision_id,
            evaluated_at="2026-09-15T17:00:02.000000Z",
        )

    def test_more_specific_rule_wins_over_broad_rule(self):
        self.repo.replace_admin(
            rules=[
                StandingPolicyRule.create(
                    rule_id="broad-allow", application_id="test-app", skill_id="documents",
                    decision="ALLOW",
                ),
                StandingPolicyRule.create(
                    rule_id="write-ask", application_id="test-app", skill_id="documents",
                    action="document.write", decision="REQUIRE_APPROVAL",
                ),
            ]
        )
        decision = self.evaluate(request_fixture("specific", action="document.write"))
        self.assertEqual(decision.decision, PolicyDecisionValue.REQUIRE_APPROVAL)
        self.assertIn("MATCHED_STANDING_RULE:write-ask", decision.reason_codes)
        self.assertNotIn("MATCHED_STANDING_RULE:broad-allow", decision.reason_codes)

    def test_equal_specificity_deny_precedence_is_deterministic(self):
        self.repo.replace_admin(
            rules=[
                StandingPolicyRule.create(
                    rule_id="allow", application_id="test-app", skill_id="documents",
                    action="document.write", decision="ALLOW",
                ),
                StandingPolicyRule.create(
                    rule_id="deny", application_id="test-app", skill_id="documents",
                    action="document.write", decision="DENY",
                ),
                StandingPolicyRule.create(
                    rule_id="ask", application_id="test-app", skill_id="documents",
                    action="document.write", decision="REQUIRE_APPROVAL",
                ),
            ]
        )
        decision = self.evaluate(request_fixture("precedence", action="document.write"))
        self.assertEqual(decision.decision, PolicyDecisionValue.DENY)
        self.assertIn("DENY_PRECEDENCE_APPLIED", decision.reason_codes)

    def test_capability_condition_uses_manifest_security_metadata(self):
        self.repo.replace_admin(
            rules=[
                StandingPolicyRule.create(
                    rule_id="destructive-deny",
                    application_id="test-app",
                    skill_id="documents",
                    conditions=[
                        StandingPolicyCondition.create(
                            source="CAPABILITY", key="destructive", equals=True
                        )
                    ],
                    decision="DENY",
                )
            ],
            defaults=[
                StandingPolicyDefault.create(
                    default_id="documents-allow",
                    application_id="test-app",
                    skill_id="documents",
                    decision="ALLOW",
                )
            ],
        )
        # The request field says false, but trusted manifest metadata marks delete destructive.
        delete = self.evaluate(
            request_fixture("trusted-delete", action="document.delete", destructive=False),
            decision_id="decision:delete",
        )
        read = self.evaluate(
            request_fixture("trusted-read", action="document.read", destructive=False),
            decision_id="decision:read",
        )
        self.assertEqual(delete.decision, PolicyDecisionValue.DENY)
        self.assertEqual(read.decision, PolicyDecisionValue.ALLOW)

    def test_request_argument_condition_is_exact_and_deterministic(self):
        self.repo.replace_admin(
            rules=[
                StandingPolicyRule.create(
                    rule_id="destructive-argument-ask",
                    application_id="test-app",
                    skill_id="documents",
                    action="document.write",
                    conditions=[
                        StandingPolicyCondition.create(
                            source="REQUEST", key="arguments:/destructive", equals=True
                        )
                    ],
                    decision="REQUIRE_APPROVAL",
                )
            ],
            defaults=[
                StandingPolicyDefault.create(
                    default_id="documents-allow", application_id="test-app",
                    skill_id="documents", decision="ALLOW",
                )
            ],
        )
        ask = self.evaluate(
            request_fixture("arg-true", action="document.write", destructive=True),
            decision_id="decision:arg-true",
        )
        allow = self.evaluate(
            request_fixture("arg-false", action="document.write", destructive=False),
            decision_id="decision:arg-false",
        )
        self.assertEqual(ask.decision, PolicyDecisionValue.REQUIRE_APPROVAL)
        self.assertEqual(allow.decision, PolicyDecisionValue.ALLOW)

    def test_resource_metadata_condition_matches_validated_type(self):
        self.repo.replace_admin(
            rules=[
                StandingPolicyRule.create(
                    rule_id="local-resource-ask",
                    application_id="test-app",
                    skill_id="documents",
                    conditions=[
                        StandingPolicyCondition.create(
                            source="RESOURCE", key="type", equals="document.local"
                        )
                    ],
                    decision="REQUIRE_APPROVAL",
                )
            ]
        )
        decision = self.evaluate(request_fixture("resource-condition"))
        self.assertEqual(decision.decision, PolicyDecisionValue.REQUIRE_APPROVAL)

    def test_skill_default_is_more_specific_than_application_default(self):
        self.repo.replace_admin(
            rules=[],
            defaults=[
                StandingPolicyDefault.create(
                    default_id="app-deny", application_id="test-app", decision="DENY"
                ),
                StandingPolicyDefault.create(
                    default_id="skill-allow", application_id="test-app",
                    skill_id="documents", decision="ALLOW",
                ),
            ],
        )
        decision = self.evaluate(request_fixture("skill-default"))
        self.assertEqual(decision.decision, PolicyDecisionValue.ALLOW)
        self.assertIn("MATCHED_STANDING_DEFAULT:skill-allow", decision.reason_codes)

    def test_absence_of_matching_rule_or_default_denies(self):
        self.repo.replace_admin(rules=[], defaults=[])
        decision = self.evaluate(request_fixture("no-fallback"))
        self.assertEqual(decision.decision, PolicyDecisionValue.DENY)
        self.assertEqual(decision.reason_codes, ("NO_MATCHING_RULE_OR_DEFAULT",))

    def test_semantically_identical_replacement_is_idempotent_and_sorted(self):
        rules = [
            StandingPolicyRule.create(rule_id="z", application_id="test-app", decision="DENY"),
            StandingPolicyRule.create(rule_id="a", application_id="test-app", decision="ALLOW"),
        ]
        first = self.repo.replace_admin(rules=rules)
        second = self.repo.replace_admin(rules=list(reversed(rules)))
        self.assertEqual(first.revision, 1)
        self.assertEqual(second.revision, 1)
        self.assertEqual(first.policy_hash, second.policy_hash)
        self.assertEqual([rule.rule_id for rule in first.rules], ["a", "z"])

    def test_corrupted_durable_snapshot_fails_closed(self):
        self.repo.replace_admin(
            rules=[StandingPolicyRule.create(
                rule_id="allow", application_id="test-app", decision="ALLOW"
            )]
        )
        pointer_key = "standing_policy.latest.v1"
        original_pointer = self.store._conn.execute(
            "SELECT value_json FROM system_state WHERE key = ?", (pointer_key,)
        ).fetchone()[0]
        tampered_pointer = json.loads(original_pointer)
        tampered_pointer["revision"] = True
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE system_state SET value_json = ? WHERE key = ?",
                (json.dumps(tampered_pointer, sort_keys=True, separators=(",", ":")), pointer_key),
            )
        with self.assertRaises(StandingPolicyIntegrityError):
            self.repo.current()
        with self.store.transaction() as conn:
            conn.execute(
                "UPDATE system_state SET value_json = ? WHERE key = ?",
                (original_pointer, pointer_key),
            )
            conn.execute(
                "UPDATE system_state SET value_json = ? WHERE key LIKE 'standing_policy.revision.v1.%'",
                ('{"corrupted":true}',),
            )
        with self.assertRaises(StandingPolicyIntegrityError):
            self.repo.current()

    def test_generic_evaluation_without_p002_context_denies(self):
        self.repo.replace_admin(
            rules=[StandingPolicyRule.create(
                rule_id="allow", application_id="test-app", decision="ALLOW"
            )]
        )
        request = request_fixture("generic-deny")
        decision = self.provider.evaluate(
            request,
            decision_id="decision:generic",
            evaluated_at="2026-09-15T17:00:02.000000Z",
        )
        self.assertEqual(decision.decision, PolicyDecisionValue.DENY)
        self.assertIn(
            "STANDING_POLICY_REQUIRES_VALIDATED_CAPABILITY_CONTEXT",
            decision.reason_codes,
        )


if __name__ == "__main__":
    unittest.main()
