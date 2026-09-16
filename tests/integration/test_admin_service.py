import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from packages.admin import AdminConflict, AdminRequest, AdminService, AdminUnauthorized
from packages.capabilities import (
    CAPABILITY_MANIFEST_SCHEMA,
    CapabilityRequestContext,
    CapabilityRequestDenied,
    CapabilityRequestValidator,
    PendingPermissionRepository,
)
from packages.core import EffectRequest, PolicyDecision, PolicyDecisionValue
from packages.policy import StandingPolicyDefault, StandingPolicyRule
from packages.state import EffectRequestRepository, PolicyDecisionRepository, SQLiteStateStore


def rfc3339(value):
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def action(action_id, properties):
    return {
        "action": action_id,
        "resource": {"type": "document.local", "selectors": ["document:workspace"]},
        "arguments": {
            "type": "object",
            "properties": {"document_id": {"type": "string", "minLength": 1, "maxLength": 128}},
            "required": ["document_id"],
            "additionalProperties": False,
        },
        "security_properties": properties,
    }


def manifest(actions=None):
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": "test-app",
        "skill_id": "documents",
        "actions": actions or [action("document.read", ["read_only"])],
    }


class AdminServiceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = SQLiteStateStore(Path(self.tmp.name) / "controller.db")
        self.uid = os.getuid()
        self.service = AdminService(self.store, owner_uid=self.uid)

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def call(self, operation, arguments, *, peer_uid=None, request_id=None):
        request = AdminRequest.create(
            request_id=request_id or f"admin:{operation}", operation=operation, arguments=arguments
        )
        return self.service.execute(request, peer_uid=self.uid if peer_uid is None else peer_uid)

    def test_wrong_uid_is_rejected_before_mutation_and_registration_grants_zero_authority(self):
        with self.assertRaises(AdminUnauthorized):
            self.call("skills.register", {"manifest": manifest()}, peer_uid=self.uid + 1)
        self.assertEqual(self.call("skills.list", {})["skills"], [])

        registered = self.call("skills.register", {"manifest": manifest()})
        self.assertEqual(registered["revision"], 1)
        self.assertEqual(self.call("permissions.list", {})["revision"], 0)
        self.assertEqual(int(self.store._conn.execute("SELECT COUNT(*) FROM policy_decisions").fetchone()[0]), 0)
        self.assertEqual(int(self.store._conn.execute("SELECT COUNT(*) FROM approvals").fetchone()[0]), 0)
        self.assertEqual(int(self.store._conn.execute("SELECT COUNT(*) FROM execution_leases").fetchone()[0]), 0)

    def test_policy_replace_and_revoke_are_revisioned_wrappers_over_p003(self):
        rule = StandingPolicyRule.create(
            rule_id="documents-read",
            application_id="test-app",
            skill_id="documents",
            action="document.read",
            decision="ALLOW",
        )
        default = StandingPolicyDefault.create(
            default_id="documents-default",
            application_id="test-app",
            skill_id="documents",
            decision="REQUIRE_APPROVAL",
        )
        first = self.call(
            "permissions.replace",
            {"rules": [rule.to_material()], "defaults": [default.to_material()]},
        )
        self.assertEqual(first["revision"], 1)
        second = self.call("permissions.revoke", {"kind": "RULE", "id": "documents-read"})
        self.assertEqual(second["revision"], 2)
        self.assertEqual(second["rules"], [])
        historical = self.call("permissions.show", {"revision": 1})
        self.assertEqual(historical["rules"][0]["rule_id"], "documents-read")

    def test_pending_resolution_never_reopens_p002_closed_effect_even_after_registry_and_policy_change(self):
        registration = self.call("skills.register", {"manifest": manifest()})
        now = datetime.now(timezone.utc)
        request = EffectRequest.create(
            request_id="effect:p004:closed",
            run_id="run:p004",
            principal_id="principal:owner",
            agent_id="agent:test",
            action="document.delete",
            resource="document:workspace",
            arguments={"document_id": "doc-1"},
            idempotency_key="idem:p004:closed",
            created_at=rfc3339(now - timedelta(minutes=1)),
            expires_at=rfc3339(now + timedelta(minutes=10)),
        )
        EffectRequestRepository(self.store).put(request)
        context = CapabilityRequestContext(
            application_id="test-app",
            skill_id="documents",
            capability_revision=registration["revision"],
            manifest_version=1,
            resource_type="document.local",
        )
        validator = CapabilityRequestValidator(self.store)
        with self.assertRaises(CapabilityRequestDenied):
            validator.validate_or_quarantine(request, context=context, observed_at_utc=rfc3339(now))
        pending_repo = PendingPermissionRepository(self.store)
        pending = pending_repo.list_pending()[0]
        closure_before = pending_repo.get_closure(request.request_id)

        resolved = self.call(
            "pending.resolve", {"pending_id": pending["pending_id"], "resolution": "NO_CHANGE"}
        )
        self.assertEqual(resolved["resolution"]["status"], "RESOLVED")
        self.assertEqual(pending_repo.get_closure(request.request_id), closure_before)

        updated = manifest(
            actions=[
                action("document.read", ["read_only"]),
                action("document.delete", ["destructive", "local_mutation"]),
            ]
        )
        newer = self.call("skills.register", {"manifest": updated})
        allow_delete = StandingPolicyRule.create(
            rule_id="delete-allow",
            application_id="test-app",
            skill_id="documents",
            action="document.delete",
            decision="ALLOW",
        )
        self.call("permissions.replace", {"rules": [allow_delete.to_material()], "defaults": []})
        newer_context = CapabilityRequestContext(
            application_id="test-app",
            skill_id="documents",
            capability_revision=newer["revision"],
            manifest_version=1,
            resource_type="document.local",
        )
        with self.assertRaises(CapabilityRequestDenied):
            validator.validate_or_quarantine(
                request, context=newer_context, observed_at_utc=rfc3339(now + timedelta(seconds=1))
            )
        self.assertEqual(pending_repo.get_closure(request.request_id), closure_before)

    def test_exact_approval_admin_wraps_existing_binding_and_is_immutable(self):
        now = datetime.now(timezone.utc)
        request = EffectRequest.create(
            request_id="effect:p004:approval",
            run_id="run:p004",
            principal_id="principal:owner",
            agent_id="agent:test",
            action="document.write",
            resource="document:workspace",
            arguments={"document_id": "doc-2"},
            idempotency_key="idem:p004:approval",
            created_at=rfc3339(now - timedelta(minutes=2)),
            expires_at=rfc3339(now + timedelta(minutes=10)),
        )
        EffectRequestRepository(self.store).put(request)
        decision = PolicyDecision.create(
            decision_id="decision:p004:approval",
            request_id=request.request_id,
            decision=PolicyDecisionValue.REQUIRE_APPROVAL,
            policy_revision="standing-policy:test",
            reason_codes=("TEST_REQUIRES_APPROVAL",),
            evaluated_at=rfc3339(now - timedelta(minutes=1)),
            canonical_request_hash=request.canonical_hash,
        )
        PolicyDecisionRepository(self.store).put(decision)

        approved = self.call("approvals.approve", {"decision_id": decision.decision_id})
        self.assertEqual(approved["approval"]["decision"], "APPROVE")
        self.assertEqual(approved["approval"]["canonical_request_hash"], request.canonical_hash)
        self.assertEqual(approved["approval"]["scope"], "ONCE")
        with self.assertRaises(AdminConflict):
            self.call("approvals.reject", {"decision_id": decision.decision_id})
        self.assertEqual(int(self.store._conn.execute("SELECT COUNT(*) FROM execution_leases").fetchone()[0]), 0)


if __name__ == "__main__":
    unittest.main()
