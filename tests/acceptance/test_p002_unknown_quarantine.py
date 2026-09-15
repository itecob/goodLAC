import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import packages.adapters
from packages.capabilities import (
    CAPABILITY_MANIFEST_SCHEMA,
    MAX_PENDING_PERMISSION_RECORDS,
    CapabilityManifest,
    CapabilityRegistry,
    CapabilityRequestContext,
    CapabilityRequestDenied,
    CapabilityRequestValidator,
    PendingPermissionRepository,
)
from packages.core import EffectRequest, PolicyDecisionValue
from packages.dispatcher import DispatchCapabilityDenied, Dispatcher
from packages.policy import LocalPolicyDecisionProvider, PolicyRule
from packages.state import EffectRequestRepository, SQLiteStateStore


FIXED = datetime(2026, 9, 15, 16, 0, 0, tzinfo=timezone.utc)


def manifest_fixture(actions=None):
    if actions is None:
        actions = [{
            "action": "document.read",
            "resource": {"type": "document.local", "selectors": ["document:workspace"]},
            "arguments": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "minLength": 1, "maxLength": 128}
                },
                "required": ["document_id"],
                "additionalProperties": False,
            },
            "security_properties": ["read_only"],
        }]
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "test-app",
        "skill_id": "documents",
        "actions": actions,
    }


def request_fixture(n, *, action="document.read", resource="document:workspace", arguments=None):
    return EffectRequest.create(
        request_id=f"effect:p002:{n}",
        run_id="run:p002",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=action,
        resource=resource,
        arguments={"document_id": "doc-1"} if arguments is None else arguments,
        idempotency_key=f"idem:p002:{n}",
        created_at="2026-09-15T15:59:00.000000Z",
        expires_at="2026-09-15T16:10:00.000000Z",
    )


class CountingAdapter:
    adapter_id = "p002-test:v1"
    def __init__(self):
        self.support_calls = 0
        self.invoke_calls = 0
    def supports(self, request):
        self.support_calls += 1
        return True
    def invoke(self, request, *, lease):
        self.invoke_calls += 1
        return {"ok": True}


class P002UnknownQuarantineTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStateStore(Path(self.tmp.name) / "controller.db")
        self.registry = CapabilityRegistry(self.store)
        self.registration = self.registry.register_admin(
            CapabilityManifest.create(manifest_fixture())
        )
        self.context = CapabilityRequestContext(
            application_id="test-app",
            skill_id="documents",
            capability_revision=self.registration.revision,
            manifest_version=1,
            resource_type="document.local",
        )
        rule = PolicyRule.create(
            rule_id="allow-read",
            principal_id="principal:owner",
            agent_id="agent:test",
            action="document.read",
            resource="document:workspace",
            decision=PolicyDecisionValue.ALLOW,
        )
        provider = LocalPolicyDecisionProvider(
            revision="policy:p002-fixture",
            known_principals=["principal:owner"],
            known_agents=["agent:test"],
            known_actions=["document.read"],
            known_resources=["document:workspace"],
            rules=[rule],
        )
        self.dispatcher = Dispatcher(store=self.store, policy_provider=provider, clock=lambda: FIXED)
        self.adapter = CountingAdapter()

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def persist(self, request):
        return EffectRequestRepository(self.store).put(request)

    def counts(self):
        return {
            table: int(self.store._conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
            for table in ("policy_decisions", "approvals", "execution_leases", "effect_executions")
        }

    def dispatch_denied(self, request, context=None):
        self.persist(request)
        with self.assertRaises(DispatchCapabilityDenied):
            self.dispatcher.dispatch_capability(
                request,
                capability_context=context or self.context,
                adapter=self.adapter,
                decision_id=f"decision:{request.request_id}",
                lease_id=f"lease:{request.request_id}",
                executor_id="executor:test",
            )

    def test_unknown_action_is_terminal_before_policy_lease_or_adapter(self):
        self.dispatch_denied(request_fixture("unknown-action", action="document.write"))
        pending = PendingPermissionRepository(self.store).list_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["reason"], "UNKNOWN_ACTION")
        self.assertEqual(self.counts(), {
            "policy_decisions": 0, "approvals": 0, "execution_leases": 0, "effect_executions": 0
        })
        self.assertEqual(self.adapter.support_calls, 0)
        self.assertEqual(self.adapter.invoke_calls, 0)

    def test_unknown_resource_type_and_scope_are_terminal(self):
        bad_type = CapabilityRequestContext(
            application_id="test-app", skill_id="documents",
            capability_revision=1, manifest_version=1, resource_type="document.remote",
        )
        self.dispatch_denied(request_fixture("bad-type"), bad_type)
        self.dispatch_denied(request_fixture("bad-scope", resource="document:other"))
        reasons = {r["reason"] for r in PendingPermissionRepository(self.store).list_pending()}
        self.assertEqual(reasons, {"UNKNOWN_RESOURCE_TYPE", "UNKNOWN_RESOURCE_SCOPE"})
        self.assertEqual(self.counts()["execution_leases"], 0)

    def test_unsupported_revision_version_and_material_shape_fail_closed(self):
        bad_revision = CapabilityRequestContext(
            application_id="test-app", skill_id="documents",
            capability_revision=99, manifest_version=1, resource_type="document.local",
        )
        self.dispatch_denied(request_fixture("bad-revision"), bad_revision)
        bad_version = CapabilityRequestContext(
            application_id="test-app", skill_id="documents",
            capability_revision=1, manifest_version=2, resource_type="document.local",
        )
        self.dispatch_denied(request_fixture("bad-version"), bad_version)
        self.dispatch_denied(request_fixture(
            "bad-shape", arguments={"document_id": "doc-1", "new_field": True}
        ))
        reasons = {r["reason"] for r in PendingPermissionRepository(self.store).list_pending()}
        self.assertEqual(reasons, {
            "UNKNOWN_CAPABILITY_OR_REVISION", "UNSUPPORTED_MANIFEST_VERSION", "MATERIAL_ARGUMENT_SHAPE"
        })

    def test_equivalent_repeats_aggregate_deterministically(self):
        validator = CapabilityRequestValidator(self.store)
        for n, observed in (
            ("repeat-1", "2026-09-15T16:00:00.000000Z"),
            ("repeat-2", "2026-09-15T16:01:00.000000Z"),
            ("repeat-3", "2026-09-15T16:02:00.000000Z"),
        ):
            with self.assertRaises(CapabilityRequestDenied):
                validator.validate_or_quarantine(
                    request_fixture(n, action="document.unknown"),
                    context=self.context,
                    observed_at_utc=observed,
                )
        pending = PendingPermissionRepository(self.store).list_pending()
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["count"], 3)
        self.assertEqual(pending[0]["first_seen_at_utc"], "2026-09-15T16:00:00.000000Z")
        self.assertEqual(pending[0]["last_seen_at_utc"], "2026-09-15T16:02:00.000000Z")

    def test_pending_metadata_contains_no_raw_credential_value(self):
        canary = "P002_CANARY_RAW_SERVICE_CREDENTIAL_DO_NOT_PERSIST"
        validator = CapabilityRequestValidator(self.store)
        with self.assertRaises(CapabilityRequestDenied):
            validator.validate_or_quarantine(
                request_fixture(
                    "credential-shape",
                    arguments={"document_id": "doc-1", "access_token": canary},
                ),
                context=self.context,
                observed_at_utc="2026-09-15T16:00:00.000000Z",
            )
        rows = self.store._conn.execute(
            "SELECT value_json FROM system_state WHERE key LIKE 'pending_permission.%' "
            "OR key LIKE 'capability_denial.request.%'"
        ).fetchall()
        material = "\n".join(str(row[0]) for row in rows)
        self.assertNotIn(canary, material)
        self.assertIn("<credential-key>", material)

    def test_pending_is_not_authority_or_resumable_state(self):
        self.dispatch_denied(request_fixture("not-authority", action="document.unknown"))
        repo = PendingPermissionRepository(self.store)
        self.assertFalse(hasattr(repo, "approve"))
        self.assertFalse(hasattr(repo, "resolve"))
        self.assertFalse(hasattr(repo, "lease"))
        self.assertEqual(self.counts(), {
            "policy_decisions": 0, "approvals": 0, "execution_leases": 0, "effect_executions": 0
        })

    def test_registry_change_never_revives_closed_effect_even_via_base_dispatch(self):
        req = request_fixture("closed", action="document.write")
        self.dispatch_denied(req)
        actions = manifest_fixture()["actions"] + [{
            "action": "document.write",
            "resource": {"type": "document.local", "selectors": ["document:workspace"]},
            "arguments": {
                "type": "object",
                "properties": {
                    "document_id": {"type": "string", "minLength": 1, "maxLength": 128}
                },
                "required": ["document_id"],
                "additionalProperties": False,
            },
            "security_properties": ["local_mutation"],
        }]
        newer = self.registry.register_admin(CapabilityManifest.create(manifest_fixture(actions)))
        new_context = CapabilityRequestContext(
            application_id="test-app", skill_id="documents",
            capability_revision=newer.revision, manifest_version=1, resource_type="document.local",
        )
        with self.assertRaises(DispatchCapabilityDenied):
            self.dispatcher.dispatch_capability(
                req, capability_context=new_context, adapter=self.adapter,
                decision_id="decision:closed:cap", lease_id="lease:closed:cap",
                executor_id="executor:test",
            )
        with self.assertRaises(DispatchCapabilityDenied):
            self.dispatcher.dispatch(
                req, adapter=self.adapter,
                decision_id="decision:closed:base", lease_id="lease:closed:base",
                executor_id="executor:test",
            )
        self.assertEqual(self.adapter.invoke_calls, 0)
        self.assertEqual(self.counts()["execution_leases"], 0)

    def test_runtime_namespaces_expose_no_registry_or_pending_mutation(self):
        self.assertFalse(hasattr(packages.adapters, "CapabilityRegistry"))
        self.assertFalse(hasattr(packages.adapters, "PendingPermissionRepository"))
        self.assertFalse(hasattr(Dispatcher, "register_admin"))
        self.assertFalse(hasattr(Dispatcher, "resolve_pending"))

    def test_queue_has_hard_distinct_record_bound(self):
        validator = CapabilityRequestValidator(self.store)
        for i in range(MAX_PENDING_PERMISSION_RECORDS + 12):
            with self.assertRaises(CapabilityRequestDenied):
                validator.validate_or_quarantine(
                    request_fixture(f"bounded-{i}", action=f"unknown.action.{i}"),
                    context=self.context,
                    observed_at_utc=f"2026-09-15T16:00:{i % 60:02d}.000000Z",
                )
        queue = self.store.get_system_state("pending_permission.queue.v1")
        self.assertEqual(len(queue["records"]), MAX_PENDING_PERMISSION_RECORDS)
        self.assertEqual(queue["overflow_distinct"], 12)

    def test_known_request_validates_without_granting_authority(self):
        validation = CapabilityRequestValidator(self.store).validate_or_quarantine(
            request_fixture("known"),
            context=self.context,
            observed_at_utc="2026-09-15T16:00:00.000000Z",
        )
        self.assertEqual(validation.action, "document.read")
        self.assertEqual(PendingPermissionRepository(self.store).list_pending(), [])
        self.assertEqual(self.counts(), {
            "policy_decisions": 0, "approvals": 0, "execution_leases": 0, "effect_executions": 0
        })


if __name__ == "__main__":
    unittest.main()
