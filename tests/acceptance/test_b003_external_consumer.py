import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from packages.admin import AdminRequest, AdminService
from packages.capabilities import CapabilityRegistry, PendingPermissionRepository
from packages.core import ApprovalDecision
from packages.policy import StandingPolicyCondition, StandingPolicyRule
from packages.runtime import (
    EXTERNAL_CONSUMER_REQUEST_SCHEMA,
    ExternalConsumerConfigurationError,
    ExternalConsumerDeclaration,
    ExternalConsumerProtocolError,
    ExternalConsumerRuntime,
)
from packages.state import (
    AgentIdentityRepository,
    ApprovalRepository,
    EffectReceiptRepository,
    EmergencyPauseRepository,
    SQLiteStateStore,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "b003_external_consumer_app.py"


class CountingAdapter:
    adapter_id = "b003-notes:v1"

    def __init__(self, *, credential_canary="B003-CREDENTIAL-CANARY-DO-NOT-EXPOSE"):
        self.invoke_calls = 0
        self.credential_canary = credential_canary

    def supports(self, request):
        return request.action in {"notes.read", "notes.write", "notes.publish"} and request.resource == "notes:workspace"

    def invoke(self, request, *, lease):
        self.invoke_calls += 1
        return {
            "schema": "b003.notes-result/v1",
            "request_id": request.request_id,
            "note_id": request.arguments["note_id"],
            "action": request.action,
            "synthetic": True,
        }


class Harness:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.store = SQLiteStateStore(self.root / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        AgentIdentityRepository(self.store).register_active("agent:b003", "principal:owner")
        self.admin = AdminService(self.store, owner_uid=os.getuid())
        self.adapter = CountingAdapter()
        self.manifest = self._fixture_json("declare")
        self.declaration = ExternalConsumerDeclaration.create(self.manifest)

    def cleanup(self):
        self.store.close()
        self.tmp.cleanup()

    def _fixture_json(self, *args):
        result = subprocess.run(
            [sys.executable, str(FIXTURE), *args],
            cwd=REPO_ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=True,
        )
        return json.loads(result.stdout)

    def request(self, name, action="notes.read", note_id=None):
        return self._fixture_json(
            "request",
            "--request-id", f"effect:b003:{name}",
            "--action", action,
            "--note-id", note_id or name,
            "--idempotency-key", f"idem:b003:{name}",
        )

    def admin_call(self, operation, arguments):
        request = AdminRequest.create(
            request_id=f"admin:b003:{operation}:{len(json.dumps(arguments, sort_keys=True))}",
            operation=operation,
            arguments=arguments,
        )
        return self.admin.execute(request, peer_uid=os.getuid())

    def register(self, manifest=None):
        return self.admin_call("skills.register", {"manifest": manifest or self.manifest})

    def set_rules(self, rules):
        return self.admin_call(
            "permissions.replace",
            {"rules": [rule.to_material() for rule in rules], "defaults": []},
        )

    def runtime(
        self,
        *,
        declaration=None,
        application_id="b003-external-app",
        skill_id="notes",
    ):
        return ExternalConsumerRuntime(
            store=self.store,
            declaration=declaration or self.declaration,
            principal_id="principal:owner",
            agent_id="agent:b003",
            application_id=application_id,
            skill_id=skill_id,
            adapter=self.adapter,
        )

    def approve(self, decision_id):
        return self.admin_call("approvals.approve", {"decision_id": decision_id})

    def reject(self, decision_id):
        return self.admin_call("approvals.reject", {"decision_id": decision_id})


class B003ExternalConsumerTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()

    def tearDown(self):
        self.h.cleanup()

    def test_separate_consumer_declaration_is_descriptive_and_registration_grants_zero_authority(self):
        fixture_source = FIXTURE.read_text(encoding="utf-8")
        self.assertNotIn("from packages", fixture_source)
        self.assertNotIn("import packages", fixture_source)
        self.assertEqual(CapabilityRegistry(self.h.store).history("b003-external-app", "notes"), [])
        runtime = self.h.runtime()
        unregistered = runtime.submit(self.h.request("unregistered"))
        self.assertEqual(unregistered["authority_outcome"], "DENY")
        self.assertEqual(self.h.adapter.invoke_calls, 0)
        self.assertEqual(len(PendingPermissionRepository(self.h.store).list_pending()), 1)
        self.assertEqual(CapabilityRegistry(self.h.store).history("b003-external-app", "notes"), [])

        self.h.register()
        registered_only = runtime.submit(self.h.request("registered-zero-authority"))
        self.assertEqual(registered_only["authority_outcome"], "DENY")
        self.assertEqual(self.h.adapter.invoke_calls, 0)
        pending = PendingPermissionRepository(self.h.store).list_pending()
        self.assertTrue(any(item["reason"] == "NO_CONFIGURED_STANDING_PERMISSION" for item in pending))

    def test_controller_owned_application_skill_binding_rejects_borrowed_registered_identity_before_policy_or_lease(self):
        self.h.register()
        borrowed_manifest = json.loads(json.dumps(self.h.manifest))
        borrowed_manifest["application_id"] = "b003-borrowed-app"
        borrowed_manifest["skill_id"] = "borrowed-notes"
        self.h.register(borrowed_manifest)
        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="allow-borrowed-identity",
                application_id="b003-borrowed-app",
                skill_id="borrowed-notes",
                decision="ALLOW",
            )
        ])

        before = {
            table: self.h.store._conn.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            ).fetchone()["count"]
            for table in ("effect_requests", "policy_decisions", "execution_leases")
        }
        with self.assertRaisesRegex(
            ExternalConsumerConfigurationError,
            "controller-owned binding",
        ):
            self.h.runtime(
                declaration=ExternalConsumerDeclaration.create(borrowed_manifest),
                application_id="b003-external-app",
                skill_id="notes",
            )
        after = {
            table: self.h.store._conn.execute(
                f"SELECT COUNT(*) AS count FROM {table}"
            ).fetchone()["count"]
            for table in ("effect_requests", "policy_decisions", "execution_leases")
        }
        self.assertEqual(after, before)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        correctly_bound = self.h.runtime()
        self.assertEqual(correctly_bound.application_id, "b003-external-app")
        self.assertEqual(correctly_bound.skill_id, "notes")
        denied = correctly_bound.submit(self.h.request("borrowed-rule-does-not-apply"))
        self.assertEqual(denied["authority_outcome"], "DENY")
        self.assertEqual(self.h.adapter.invoke_calls, 0)

    def test_allow_returns_typed_result_receipt_and_duplicate_replays_without_second_effect(self):
        self.h.register()
        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="allow-read",
                application_id="b003-external-app",
                skill_id="notes",
                action="notes.read",
                decision="ALLOW",
            )
        ])
        runtime = self.h.runtime()
        request = self.h.request("allow", action="notes.read")
        first = runtime.submit(request)
        self.assertEqual(first["authority_outcome"], "ALLOW")
        self.assertEqual(first["execution_state"], "SUCCEEDED")
        self.assertEqual(first["result"]["note_id"], "allow")
        self.assertEqual(first["receipt"]["request_id"], request["request_id"])
        self.assertNotIn("result_json", first["receipt"])
        self.assertFalse(first["replayed"])
        self.assertEqual(self.h.adapter.invoke_calls, 1)

        second = runtime.submit(request)
        self.assertEqual(second["authority_outcome"], "ALLOW")
        self.assertTrue(second["replayed"])
        self.assertEqual(second["receipt"]["receipt_id"], first["receipt"]["receipt_id"])
        self.assertEqual(self.h.adapter.invoke_calls, 1)

        consumed = subprocess.run(
            [sys.executable, str(FIXTURE), "consume"],
            cwd=REPO_ROOT,
            input=json.dumps(first),
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5,
            check=True,
        )
        self.assertIn("B003_CONSUMER_ACCEPTED=1", consumed.stdout)

    def test_exact_approval_is_owner_created_consumer_cannot_inject_it_and_predispatch_deny_wins(self):
        self.h.register()
        ask = StandingPolicyRule.create(
            rule_id="ask-write",
            application_id="b003-external-app",
            skill_id="notes",
            action="notes.write",
            decision="REQUIRE_APPROVAL",
        )
        self.h.set_rules([ask])
        runtime = self.h.runtime()
        request = self.h.request("approval", action="notes.write")
        pending = runtime.submit(request)
        self.assertEqual(pending["authority_outcome"], "REQUIRE_APPROVAL")
        self.assertIsNotNone(pending["decision_id"])
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        injected = dict(request)
        injected["approval_id"] = "approval:consumer-forged"
        with self.assertRaises(ExternalConsumerProtocolError):
            runtime.submit(injected)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        approved = self.h.approve(pending["decision_id"])
        approval_id = approved["approval"]["approval_id"]
        self.assertEqual(approved["approval"]["decision"], "APPROVE")

        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="deny-write",
                application_id="b003-external-app",
                skill_id="notes",
                action="notes.write",
                decision="DENY",
            )
        ])
        denied = runtime.submit(request)
        self.assertEqual(denied["authority_outcome"], "DENY")
        self.assertEqual(self.h.adapter.invoke_calls, 0)
        self.assertIsNone(ApprovalRepository(self.h.store).get(approval_id).consumed_at)

        self.h.set_rules([ask])
        allowed = runtime.submit(request)
        self.assertEqual(allowed["authority_outcome"], "ALLOW")
        self.assertEqual(self.h.adapter.invoke_calls, 1)
        self.assertIsNotNone(ApprovalRepository(self.h.store).get(approval_id).consumed_at)

    def test_rejected_or_capability_closed_request_cannot_be_revived_by_later_admin(self):
        self.h.register()
        ask = StandingPolicyRule.create(
            rule_id="ask-write",
            application_id="b003-external-app",
            skill_id="notes",
            action="notes.write",
            decision="REQUIRE_APPROVAL",
        )
        self.h.set_rules([ask])
        runtime = self.h.runtime()
        request = self.h.request("reject", action="notes.write")
        first = runtime.submit(request)
        self.h.reject(first["decision_id"])
        rejected = runtime.submit(request)
        self.assertEqual(rejected["authority_outcome"], "DENY")
        self.assertEqual(rejected["execution_state"], "REJECTED")
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        unknown = self.h.request("closed-unknown", action="notes.delete")
        closed = runtime.submit(unknown)
        self.assertEqual(closed["authority_outcome"], "DENY")
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        expanded = json.loads(json.dumps(self.h.manifest))
        expanded["actions"].append({
            "action": "notes.delete",
            "resource": {"type": "notes.local", "selectors": ["notes:workspace"]},
            "arguments": {
                "type": "object",
                "properties": {"note_id": {"type": "string", "minLength": 1, "maxLength": 128}},
                "required": ["note_id"],
                "additionalProperties": False,
            },
            "security_properties": ["destructive", "local_mutation"],
        })
        self.h.register(expanded)
        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="allow-delete",
                application_id="b003-external-app",
                skill_id="notes",
                action="notes.delete",
                decision="ALLOW",
            )
        ])
        expanded_runtime = ExternalConsumerRuntime(
            store=self.h.store,
            declaration=ExternalConsumerDeclaration.create(expanded),
            principal_id="principal:owner",
            agent_id="agent:b003",
            application_id="b003-external-app",
            skill_id="notes",
            adapter=self.h.adapter,
        )
        still_closed = expanded_runtime.submit(unknown)
        self.assertEqual(still_closed["authority_outcome"], "DENY")
        self.assertEqual(self.h.adapter.invoke_calls, 0)

    def test_consumer_protocol_cannot_supply_identity_authority_or_admin_material(self):
        self.h.register()
        runtime = self.h.runtime()
        baseline = self.h.request("boundary")
        for field, value in (
            ("principal_id", "principal:attacker"),
            ("agent_id", "agent:attacker"),
            ("application_id", "other-app"),
            ("skill_id", "other-skill"),
            ("capability_revision", 999),
            ("decision", "ALLOW"),
            ("approval_id", "approval:forged"),
            ("lease_id", "lease:forged"),
            ("executor_id", "executor:forged"),
            ("admin_operation", "permissions.replace"),
            ("credential_ref", "secret:forged"),
        ):
            attempted = dict(baseline)
            attempted[field] = value
            with self.subTest(field=field), self.assertRaises(ExternalConsumerProtocolError):
                runtime.submit(attempted)
        self.assertFalse(hasattr(runtime, "register"))
        self.assertFalse(hasattr(runtime, "replace_policy"))
        self.assertFalse(hasattr(runtime, "approve"))
        self.assertFalse(hasattr(runtime, "admin"))
        source = (REPO_ROOT / "packages" / "runtime" / "external_consumer.py").read_text(encoding="utf-8")
        self.assertNotIn("packages.admin", source)
        self.assertNotIn("admin-v1.sock", source)
        self.assertEqual(self.h.adapter.invoke_calls, 0)

    def test_deny_precedence_and_conditional_policy_remain_controller_owned(self):
        self.h.register()
        external = StandingPolicyCondition.create(source="CAPABILITY", key="external_mutation", equals=True)
        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="publish-allow",
                application_id="b003-external-app",
                skill_id="notes",
                action="notes.publish",
                decision="ALLOW",
            ),
            StandingPolicyRule.create(
                rule_id="publish-deny",
                application_id="b003-external-app",
                skill_id="notes",
                action="notes.publish",
                decision="DENY",
            ),
            StandingPolicyRule.create(
                rule_id="external-ask",
                application_id="b003-external-app",
                skill_id="notes",
                conditions=[external],
                decision="REQUIRE_APPROVAL",
            ),
        ])
        runtime = self.h.runtime()
        denied = runtime.submit(self.h.request("deny-precedence", action="notes.publish"))
        self.assertEqual(denied["authority_outcome"], "DENY")
        self.assertEqual(self.h.adapter.invoke_calls, 0)

        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="external-ask",
                application_id="b003-external-app",
                skill_id="notes",
                conditions=[external],
                decision="REQUIRE_APPROVAL",
            )
        ])
        ask = runtime.submit(self.h.request("conditional", action="notes.publish"))
        self.assertEqual(ask["authority_outcome"], "REQUIRE_APPROVAL")
        self.assertEqual(self.h.adapter.invoke_calls, 0)

    def test_credential_canary_absent_from_consumer_response_receipt_and_durable_receipt(self):
        self.h.register()
        self.h.set_rules([
            StandingPolicyRule.create(
                rule_id="allow-read",
                application_id="b003-external-app",
                skill_id="notes",
                action="notes.read",
                decision="ALLOW",
            )
        ])
        runtime = self.h.runtime()
        response = runtime.submit(self.h.request("credential-isolation"))
        canary = self.h.adapter.credential_canary
        self.assertNotIn(canary, json.dumps(response, sort_keys=True))
        receipt = EffectReceiptRepository(self.h.store).get_receipt_for_request("effect:b003:credential-isolation")
        self.assertIsNotNone(receipt)
        self.assertNotIn(canary, json.dumps(receipt.to_record(), sort_keys=True))


if __name__ == "__main__":
    unittest.main()
