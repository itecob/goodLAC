import json
import unittest
from datetime import datetime, timedelta, timezone

from packages.capabilities import CapabilityRequestContext
from packages.core import EffectRequest
from packages.dispatcher import (
    DispatchApprovalRequired,
    DispatchCapabilityDenied,
    DispatchDenied,
    DispatchDuplicateEffect,
)
from packages.effects.calendar import (
    CALENDAR_CREATE_ACTION,
    CALENDAR_DELETE_ACTION,
    CALENDAR_RESOURCE_TYPE,
    CalendarEffectAdapter,
    calendar_capability_manifest,
)
from packages.policy import StandingPolicyRule
from packages.state import (
    ApprovalBindingValidator,
    ApprovalValidationError,
    AuditRepository,
    EffectReceiptRepository,
    EffectRequestRepository,
)
from tests.acceptance.test_p006_permission_management_e2e import Harness

CANARY = "SYNTHETIC_B002_CALENDAR_CANARY_NOT_A_REAL_CREDENTIAL"
APP = "b002-test-app"
SKILL = "google-calendar"
RESOURCE = "calendar:primary"


def rfc3339(dt):
    return dt.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def event_args(**overrides):
    data = {
        "title":"B002 synthetic event",
        "start":"2026-10-01T13:00:00-04:00",
        "end":"2026-10-01T14:00:00-04:00",
        "timezone":"America/Toronto",
        "attendees":["owner@example.com"],
        "location":"Synthetic local fixture",
        "recurrence":[],
        "conference_settings":{"enabled":False,"solution_type":"hangoutsMeet"},
        "send_updates":"none",
    }
    data.update(overrides)
    return data


def effect(name, *, action=CALENDAR_CREATE_ACTION, arguments=None):
    now = datetime.now(timezone.utc)
    return EffectRequest.create(
        request_id=f"effect:b002:{name}",
        run_id="run:b002-permissions",
        principal_id="principal:owner",
        agent_id="agent:test",
        action=action,
        resource=RESOURCE,
        arguments=event_args() if arguments is None else arguments,
        idempotency_key=f"idem:b002:{name}",
        created_at=rfc3339(now - timedelta(seconds=2)),
        expires_at=rfc3339(now + timedelta(minutes=30)),
    )


class SyntheticSecrets:
    def __init__(self): self.calls = []
    def resolve(self, ref):
        self.calls.append(ref)
        return CANARY


class SyntheticCalendarTransport:
    def __init__(self):
        self.invoke_count = 0
        self.mutations = {}
    def search(self, **kwargs): return {"events": []}
    def read(self, *, event_id): return {"event":{"id":event_id}}
    def create(self, *, event, request_id, idempotency_key):
        key = (CALENDAR_CREATE_ACTION, request_id, idempotency_key)
        if key in self.mutations: raise AssertionError("duplicate Calendar create reached transport")
        self.invoke_count += 1
        result = {"event":{"id":f"synthetic-{self.invoke_count}"},"upstream_reference":f"gcal:event:synthetic-{self.invoke_count}"}
        self.mutations[key] = result
        return result
    def modify(self, *, event_id, event_etag, event, request_id, idempotency_key):
        self.invoke_count += 1
        result = {"event":{"id":event_id},"upstream_reference":"gcal:event:"+event_id}
        self.mutations[("calendar.modify",request_id,idempotency_key)] = result
        return result
    def cancel(self, *, event_id, event_etag, send_updates, request_id, idempotency_key):
        self.invoke_count += 1
        result = {"event":{"id":event_id,"status":"cancelled"},"upstream_reference":"gcal:event:"+event_id}
        self.mutations[("calendar.cancel",request_id,idempotency_key)] = result
        return result
    def reconcile(self, *, action, request_id, idempotency_key, operation):
        return self.mutations.get((action, request_id, idempotency_key))


class Factory:
    def __init__(self, transport): self.transport = transport
    def create(self, *, calendar_resource, secret):
        if calendar_resource != RESOURCE or secret != CANARY: raise AssertionError("unexpected synthetic Calendar capability")
        return self.transport


class B002CalendarPermissionTests(unittest.TestCase):
    def setUp(self):
        self.h = Harness()
        registration = self.h.admin_call("skills.register", {"manifest": calendar_capability_manifest(application_id=APP, skill_id=SKILL)})
        self.context = CapabilityRequestContext(
            application_id=APP,
            skill_id=SKILL,
            capability_revision=registration["revision"],
            manifest_version=1,
            resource_type=CALENDAR_RESOURCE_TYPE,
        )
        self.secrets = SyntheticSecrets()
        self.transport = SyntheticCalendarTransport()
        self.adapter = CalendarEffectAdapter(secret_provider=self.secrets, transport_factory=Factory(self.transport))

    def tearDown(self): self.h.cleanup()

    def dispatch(self, req, label, *, approval_id=None):
        EffectRequestRepository(self.h.store).put(req)
        kwargs = {} if approval_id is None else {"approval_id": approval_id}
        return self.h.dispatcher().dispatch_capability(
            req,
            capability_context=self.context,
            adapter=self.adapter,
            decision_id=f"decision:b002:{label}",
            lease_id=f"lease:b002:{label}",
            executor_id="executor:b002",
            **kwargs,
        )

    def set_rule(self, decision, *, action=CALENDAR_CREATE_ACTION):
        return self.h.set_policy(rules=[StandingPolicyRule.create(
            rule_id=f"b002-{action}-{decision.lower()}", application_id=APP, skill_id=SKILL,
            action=action, resource_selector=RESOURCE, decision=decision,
        )])

    def test_first_use_unconfigured_is_terminal_denied_reviewable_nonresumable_then_fresh_allow_executes(self):
        original = effect("unconfigured-original")
        with self.assertRaises(DispatchDenied): self.dispatch(original, "unconfigured-original")
        self.assertEqual(self.transport.invoke_count, 0)
        self.assertEqual(self.secrets.calls, [])
        leases = self.h.store._conn.execute("SELECT COUNT(*) FROM execution_leases WHERE request_id=?", (original.request_id,)).fetchone()[0]
        self.assertEqual(int(leases), 0)
        pending = self.h.lacctl_json("pending", "list")["pending"]
        self.assertEqual(len(pending), 1)
        self.assertEqual(pending[0]["reason"], "NO_CONFIGURED_STANDING_PERMISSION")
        pending_id = pending[0]["pending_id"]
        self.assertNotIn("B002 synthetic event", json.dumps(pending[0], sort_keys=True))

        self.set_rule("ALLOW")
        self.h.lacctl_json("pending", "resolve", pending_id, "POLICY_UPDATED")
        with self.assertRaises(DispatchCapabilityDenied): self.dispatch(original, "original-after-config")
        self.assertEqual(self.transport.invoke_count, 0)

        fresh = effect("fresh-after-allow")
        result = self.dispatch(fresh, "fresh-after-allow")
        self.assertEqual(result.upstream_reference, "gcal:event:synthetic-1")
        self.assertEqual(self.transport.invoke_count, 1)
        self.assertEqual(self.secrets.calls, ["google-calendar:primary"])

        stored_request = EffectRequestRepository(self.h.store).get(fresh.request_id).to_record()
        receipt = EffectReceiptRepository(self.h.store).get_receipt_for_request(fresh.request_id).to_record()
        audit = [x.details for x in AuditRepository(self.h.store).list_for_request(fresh.request_id)]
        durable = repr(stored_request) + repr(receipt) + repr(audit)
        self.assertNotIn(CANARY, durable)
        self.assertNotIn("google-calendar:primary", durable)

    def test_explicit_deny_creates_no_permission_discovery_noise_or_adapter_access(self):
        self.set_rule("DENY")
        req = effect("explicit-deny")
        with self.assertRaises(DispatchDenied): self.dispatch(req, "explicit-deny")
        self.assertEqual(self.h.lacctl_json("pending", "list")["pending"], [])
        self.assertEqual(self.transport.invoke_count, 0)
        self.assertEqual(self.secrets.calls, [])

    def test_require_approval_is_exact_rechecked_and_single_use(self):
        self.set_rule("REQUIRE_APPROVAL")
        req = effect("ask")
        with self.assertRaises(DispatchApprovalRequired): self.dispatch(req, "ask")
        self.assertEqual(self.transport.invoke_count, 0)
        approved = self.h.lacctl_json("approvals", "approve", "decision:b002:ask")
        approval_id = approved["approval"]["approval_id"]
        self.assertEqual(self.transport.invoke_count, 0)

        mutated = EffectRequest.create(
            request_id=req.request_id,
            run_id=req.run_id,
            principal_id=req.principal_id,
            agent_id=req.agent_id,
            action=req.action,
            resource=req.resource,
            arguments=event_args(title="Mutated after approval"),
            idempotency_key=req.idempotency_key,
            created_at=req.created_at,
            expires_at=req.expires_at,
        )
        with self.assertRaises(ApprovalValidationError):
            ApprovalBindingValidator(self.h.store).validate(approval_id=approval_id, current_request=mutated, at=rfc3339(datetime.now(timezone.utc)))

        self.set_rule("DENY")
        with self.assertRaises(DispatchDenied): self.dispatch(req, "ask-policy-recheck", approval_id=approval_id)
        self.assertEqual(self.transport.invoke_count, 0)

        self.set_rule("REQUIRE_APPROVAL")
        result = self.dispatch(req, "ask-approved", approval_id=approval_id)
        self.assertTrue(result.upstream_reference.startswith("gcal:event:"))
        self.assertEqual(self.transport.invoke_count, 1)
        with self.assertRaises(DispatchDuplicateEffect): self.dispatch(req, "ask-duplicate", approval_id=approval_id)
        self.assertEqual(self.transport.invoke_count, 1)

    def test_calendar_delete_is_policy_denied_and_never_reaches_credentials(self):
        self.set_rule("DENY", action=CALENDAR_DELETE_ACTION)
        req = effect("delete", action=CALENDAR_DELETE_ACTION, arguments={"event_id":"evt_1","event_etag":"\"v1\""})
        with self.assertRaises(DispatchDenied): self.dispatch(req, "delete")
        self.assertEqual(self.secrets.calls, [])
        self.assertEqual(self.transport.invoke_count, 0)

if __name__ == "__main__":
    unittest.main()
