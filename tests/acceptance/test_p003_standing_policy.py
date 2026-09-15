import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import packages.adapters
from packages.capabilities import (
    CAPABILITY_MANIFEST_SCHEMA,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilityRequestContext,
    PendingPermissionRepository,
)
from packages.core import EffectRequest
from packages.dispatcher import (
    DispatchApprovalRequired,
    DispatchCapabilityDenied,
    DispatchDenied,
    Dispatcher,
)
from packages.policy import (
    StandingPolicyCondition,
    StandingPolicyDecisionProvider,
    StandingPolicyDefault,
    StandingPolicyRepository,
    StandingPolicyRule,
)
from packages.state import (
    AgentIdentityRepository,
    EffectRequestRepository,
    EmergencyPauseRepository,
    SQLiteStateStore,
)


FIXED = datetime(2026, 9, 15, 17, 30, 0, tzinfo=timezone.utc)


def action_fixture(action, properties):
    return {
        "action": action,
        "resource": {"type": "document.local", "selectors": ["document:workspace"]},
        "arguments": {
            "type": "object",
            "properties": {
                "document_id": {"type": "string", "minLength": 1, "maxLength": 128},
                "requires_confirmation": {"type": "boolean"},
            },
            "required": ["document_id", "requires_confirmation"],
            "additionalProperties": False,
        },
        "security_properties": properties,
    }


def manifest_fixture(actions=None):
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "test-app",
        "skill_id": "documents",
        "actions": actions or [
            action_fixture("document.read", ["read_only"]),
            action_fixture("document.write", ["local_mutation"]),
        ],
    }


def request_fixture(name, *, action="document.read", arguments=None):
    return EffectRequest.create(
        request_id=f"effect:p003:acceptance:{name}",
        run_id="run:p003:acceptance",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=action,
        resource="document:workspace",
        arguments={"document_id": "doc-1", "requires_confirmation": False}
        if arguments is None else arguments,
        idempotency_key=f"idem:p003:acceptance:{name}",
        created_at="2026-09-15T17:29:00.000000Z",
        expires_at="2026-09-15T17:40:00.000000Z",
    )


class CountingAdapter:
    adapter_id = "p003-test:v1"

    def __init__(self):
        self.support_calls = 0
        self.invoke_calls = 0

    def supports(self, request):
        self.support_calls += 1
        return True

    def invoke(self, request, *, lease):
        self.invoke_calls += 1
        return {"ok": True, "request_id": request.request_id}


class P003StandingPolicyAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStateStore(Path(self.tmp.name) / "controller.db")
        EmergencyPauseRepository(self.store).resume()
        self.registry = CapabilityRegistry(self.store)
        registration = self.registry.register_admin(CapabilityManifest.create(manifest_fixture()))
        self.context = CapabilityRequestContext(
            application_id="test-app",
            skill_id="documents",
            capability_revision=registration.revision,
            manifest_version=1,
            resource_type="document.local",
        )
        AgentIdentityRepository(self.store).register_active("agent:test", "principal:owner")
        self.policy_repo = StandingPolicyRepository(self.store)
        self.provider = StandingPolicyDecisionProvider(self.store)
        self.dispatcher = Dispatcher(
            store=self.store,
            policy_provider=self.provider,
            clock=lambda: FIXED,
        )
        self.adapter = CountingAdapter()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def persist(self, request):
        return EffectRequestRepository(self.store).put(request)

    def dispatch(self, request, *, context=None):
        self.persist(request)
        return self.dispatcher.dispatch_capability(
            request,
            capability_context=context or self.context,
            adapter=self.adapter,
            decision_id=f"decision:{request.request_id}",
            lease_id=f"lease:{request.request_id}",
            executor_id="executor:p003",
        )

    def test_allow_path_executes_only_after_p002_validation_and_standing_policy(self):
        self.policy_repo.replace_admin(
            rules=[],
            defaults=[StandingPolicyDefault.create(
                default_id="documents-allow", application_id="test-app",
                skill_id="documents", decision="ALLOW",
            )],
        )
        request = request_fixture("allow")
        result = self.dispatch(request)
        self.assertTrue(result["ok"])
        self.assertEqual(self.adapter.invoke_calls, 1)
        decisions = self.store._conn.execute(
            "SELECT decision, policy_revision FROM policy_decisions WHERE request_id = ?",
            (request.request_id,),
        ).fetchall()
        self.assertEqual(len(decisions), 1)
        self.assertEqual(decisions[0]["decision"], "ALLOW")
        self.assertTrue(str(decisions[0]["policy_revision"]).startswith("standing-policy:1:sha256:"))

    def test_conditional_ask_never_invokes_adapter_without_exact_approval(self):
        self.policy_repo.replace_admin(
            rules=[StandingPolicyRule.create(
                rule_id="ask-confirmed-write",
                application_id="test-app", skill_id="documents", action="document.write",
                conditions=[StandingPolicyCondition.create(
                    source="REQUEST", key="arguments:/requires_confirmation", equals=True
                )],
                decision="REQUIRE_APPROVAL",
            )],
            defaults=[StandingPolicyDefault.create(
                default_id="documents-allow", application_id="test-app",
                skill_id="documents", decision="ALLOW",
            )],
        )
        request = request_fixture(
            "ask", action="document.write",
            arguments={"document_id": "doc-1", "requires_confirmation": True},
        )
        self.persist(request)
        with self.assertRaises(DispatchApprovalRequired):
            self.dispatcher.dispatch_capability(
                request, capability_context=self.context, adapter=self.adapter,
                decision_id="decision:ask", lease_id="lease:ask",
                executor_id="executor:p003",
            )
        self.assertEqual(self.adapter.invoke_calls, 0)
        self.assertEqual(
            int(self.store._conn.execute("SELECT COUNT(*) FROM execution_leases").fetchone()[0]),
            0,
        )

    def test_p002_material_shape_denial_occurs_before_standing_policy(self):
        self.policy_repo.replace_admin(
            rules=[StandingPolicyRule.create(
                rule_id="allow-all-docs", application_id="test-app", skill_id="documents",
                decision="ALLOW",
            )]
        )
        request = request_fixture(
            "bad-shape",
            arguments={
                "document_id": "doc-1",
                "requires_confirmation": False,
                "new_material_field": "must-deny",
            },
        )
        self.persist(request)
        with self.assertRaises(DispatchCapabilityDenied):
            self.dispatcher.dispatch_capability(
                request, capability_context=self.context, adapter=self.adapter,
                decision_id="decision:bad-shape", lease_id="lease:bad-shape",
                executor_id="executor:p003",
            )
        self.assertEqual(self.adapter.support_calls, 0)
        self.assertEqual(self.adapter.invoke_calls, 0)
        self.assertEqual(
            int(self.store._conn.execute("SELECT COUNT(*) FROM policy_decisions").fetchone()[0]),
            0,
        )
        pending = PendingPermissionRepository(self.store).list_pending()
        self.assertEqual(pending[0]["reason"], "MATERIAL_ARGUMENT_SHAPE")

    def test_policy_and_registry_changes_never_revive_p002_closed_effect(self):
        self.policy_repo.replace_admin(rules=[], defaults=[])
        request = request_fixture("closed", action="document.delete")
        self.persist(request)
        with self.assertRaises(DispatchCapabilityDenied):
            self.dispatcher.dispatch_capability(
                request, capability_context=self.context, adapter=self.adapter,
                decision_id="decision:closed:initial", lease_id="lease:closed:initial",
                executor_id="executor:p003",
            )

        newer_manifest = manifest_fixture(
            actions=manifest_fixture()["actions"] + [
                action_fixture("document.delete", ["destructive", "local_mutation"])
            ]
        )
        newer = self.registry.register_admin(CapabilityManifest.create(newer_manifest))
        newer_context = CapabilityRequestContext(
            application_id="test-app", skill_id="documents",
            capability_revision=newer.revision, manifest_version=1,
            resource_type="document.local",
        )
        self.policy_repo.replace_admin(
            rules=[StandingPolicyRule.create(
                rule_id="delete-allow", application_id="test-app", skill_id="documents",
                action="document.delete", decision="ALLOW",
            )]
        )
        with self.assertRaises(DispatchCapabilityDenied):
            self.dispatcher.dispatch_capability(
                request, capability_context=newer_context, adapter=self.adapter,
                decision_id="decision:closed:later", lease_id="lease:closed:later",
                executor_id="executor:p003",
            )
        self.assertEqual(self.adapter.invoke_calls, 0)
        self.assertEqual(
            int(self.store._conn.execute("SELECT COUNT(*) FROM execution_leases").fetchone()[0]),
            0,
        )

    def test_direct_dispatch_cannot_bypass_validated_capability_context(self):
        self.policy_repo.replace_admin(
            rules=[StandingPolicyRule.create(
                rule_id="broad-allow", application_id="test-app", decision="ALLOW"
            )]
        )
        request = request_fixture("direct-bypass")
        self.persist(request)
        with self.assertRaises(DispatchDenied):
            self.dispatcher.dispatch(
                request,
                adapter=self.adapter,
                decision_id="decision:direct",
                lease_id="lease:direct",
                executor_id="executor:p003",
            )
        self.assertEqual(self.adapter.invoke_calls, 0)
        self.assertEqual(
            int(self.store._conn.execute("SELECT COUNT(*) FROM execution_leases").fetchone()[0]),
            0,
        )

    def test_runtime_surface_exposes_no_standing_policy_mutation(self):
        self.assertFalse(hasattr(packages.adapters, "StandingPolicyRepository"))
        self.assertFalse(hasattr(Dispatcher, "replace_policy_admin"))
        self.assertFalse(hasattr(Dispatcher, "set_standing_policy"))
        self.assertFalse(hasattr(StandingPolicyDecisionProvider, "replace_admin"))


if __name__ == "__main__":
    unittest.main()
