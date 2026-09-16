import json
import unittest

from packages.dispatcher import DispatchCapabilityDenied, DispatchDenied
from packages.policy import (
    StandingPolicyDefault,
    StandingPolicyRepository,
    StandingPolicyRule,
)
from tests.acceptance.test_p006_permission_management_e2e import (
    CountingAdapter,
    Harness,
    action_fixture,
    request_fixture,
)


class P006FirstUsePermissionDiscoveryTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.cleanup()

    def test_known_valid_unconfigured_denies_aggregates_closes_and_requires_fresh_request(self):
        registration = self.h.register(
            [
                action_fixture("document.read", ["read_only"]),
                action_fixture("document.write", ["local_mutation"]),
            ]
        )
        context = self.h.context(registration["revision"])
        adapter = CountingAdapter()

        original = request_fixture("known-unconfigured-sensitive-value", "document.read")
        self.h.persist(original)
        with self.assertRaises(DispatchDenied):
            self.h.dispatcher().dispatch_capability(
                original,
                capability_context=context,
                adapter=adapter,
                decision_id="decision:p006-uat:known-unconfigured",
                lease_id="lease:p006-uat:known-unconfigured",
                executor_id="executor:p006-uat",
            )
        self.assertEqual(adapter.invoke_calls, 0)
        self.assertEqual(
            int(
                self.h.store._conn.execute(
                    "SELECT COUNT(*) FROM execution_leases WHERE request_id = ?",
                    (original.request_id,),
                ).fetchone()[0]
            ),
            0,
        )

        pending = self.h.lacctl_json("pending", "list")["pending"]
        self.assertEqual(len(pending), 1)
        item = pending[0]
        self.assertEqual(item["reason"], "NO_CONFIGURED_STANDING_PERMISSION")
        self.assertEqual(item["application_id"], "test-app")
        self.assertEqual(item["skill_id"], "documents")
        self.assertEqual(item["action"], "document.read")
        self.assertEqual(item["resource_type"], "document.local")
        self.assertEqual(item["resource"], "document:workspace")
        self.assertEqual(item["count"], 1)
        self.assertNotIn(
            "known-unconfigured-sensitive-value",
            json.dumps(item, sort_keys=True),
        )
        pending_id = item["pending_id"]

        self.h.set_policy(
            rules=[
                StandingPolicyRule.create(
                    rule_id="unrelated-write-allow",
                    application_id="test-app",
                    skill_id="documents",
                    action="document.write",
                    decision="ALLOW",
                )
            ]
        )
        repeated = request_fixture("same-shape-second-request", "document.read")
        self.h.persist(repeated)
        with self.assertRaises(DispatchDenied):
            self.h.dispatcher().dispatch_capability(
                repeated,
                capability_context=context,
                adapter=adapter,
                decision_id="decision:p006-uat:known-unconfigured-repeat",
                lease_id="lease:p006-uat:known-unconfigured-repeat",
                executor_id="executor:p006-uat",
            )
        pending = self.h.lacctl_json("pending", "list")["pending"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["pending_id"], pending_id)
        self.assertEqual(pending[0]["count"], 2)

        self.h.set_policy(
            rules=[
                StandingPolicyRule.create(
                    rule_id="read-allow",
                    application_id="test-app",
                    skill_id="documents",
                    action="document.read",
                    decision="ALLOW",
                )
            ]
        )
        resolved = self.h.lacctl_json(
            "pending", "resolve", pending_id, "POLICY_UPDATED"
        )
        self.assertEqual(resolved["resolution"]["status"], "RESOLVED")

        with self.assertRaises(DispatchCapabilityDenied):
            self.h.dispatcher().dispatch_capability(
                original,
                capability_context=context,
                adapter=adapter,
                decision_id="decision:p006-uat:original-after-config",
                lease_id="lease:p006-uat:original-after-config",
                executor_id="executor:p006-uat",
            )
        self.assertEqual(adapter.invoke_calls, 0)

        fresh = request_fixture("fresh-read-after-config", "document.read")
        self.h.persist(fresh)
        result = self.h.dispatcher().dispatch_capability(
            fresh,
            capability_context=context,
            adapter=adapter,
            decision_id="decision:p006-uat:fresh-after-config",
            lease_id="lease:p006-uat:fresh-after-config",
            executor_id="executor:p006-uat",
        )
        self.assertTrue(result["ok"])
        self.assertEqual(adapter.invoke_calls, 1)

    def test_explicit_rule_and_default_deny_create_no_discovery_noise(self):
        registration = self.h.register(
            [
                action_fixture("document.read", ["read_only"]),
                action_fixture("document.write", ["local_mutation"]),
            ]
        )
        context = self.h.context(registration["revision"])
        adapter = CountingAdapter()
        repository = StandingPolicyRepository(self.h.store)

        repository.replace_admin(
            rules=[
                StandingPolicyRule.create(
                    rule_id="read-explicit-deny",
                    application_id="test-app",
                    skill_id="documents",
                    action="document.read",
                    decision="DENY",
                )
            ],
            defaults=[],
        )
        denied_by_rule = request_fixture("explicit-rule-deny", "document.read")
        self.h.persist(denied_by_rule)
        with self.assertRaises(DispatchDenied):
            self.h.dispatcher().dispatch_capability(
                denied_by_rule,
                capability_context=context,
                adapter=adapter,
                decision_id="decision:p006-uat:explicit-rule-deny",
                lease_id="lease:p006-uat:explicit-rule-deny",
                executor_id="executor:p006-uat",
            )
        self.assertEqual(self.h.lacctl_json("pending", "list")["pending"], [])

        repository.replace_admin(
            rules=[],
            defaults=[
                StandingPolicyDefault.create(
                    default_id="documents-explicit-deny",
                    application_id="test-app",
                    skill_id="documents",
                    decision="DENY",
                )
            ],
        )
        denied_by_default = request_fixture("explicit-default-deny", "document.write")
        self.h.persist(denied_by_default)
        with self.assertRaises(DispatchDenied):
            self.h.dispatcher().dispatch_capability(
                denied_by_default,
                capability_context=context,
                adapter=adapter,
                decision_id="decision:p006-uat:explicit-default-deny",
                lease_id="lease:p006-uat:explicit-default-deny",
                executor_id="executor:p006-uat",
            )
        self.assertEqual(self.h.lacctl_json("pending", "list")["pending"], [])
        self.assertEqual(adapter.invoke_calls, 0)


if __name__ == "__main__":
    unittest.main()
