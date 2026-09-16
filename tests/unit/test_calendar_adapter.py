import unittest

from packages.core import EffectRequest, ExecutionLease
from packages.effects.calendar import (
    CALENDAR_CANCEL_ACTION,
    CALENDAR_CREATE_ACTION,
    CALENDAR_DELETE_ACTION,
    CALENDAR_MODIFY_ACTION,
    CALENDAR_PROPOSE_ACTION,
    CALENDAR_READ_ACTION,
    CALENDAR_SEARCH_ACTION,
    CalendarEffectAdapter,
    CalendarEffectError,
)

RESOURCE = "calendar:primary"


def event_args(**overrides):
    data = {
        "title": "Synthetic planning event",
        "start": "2026-10-01T13:00:00-04:00",
        "end": "2026-10-01T14:00:00-04:00",
        "timezone": "America/Toronto",
        "attendees": ["alpha@example.com", "owner@example.com"],
        "location": "Synthetic room",
        "recurrence": [],
        "conference_settings": {"enabled": False, "solution_type": "hangoutsMeet"},
        "send_updates": "none",
    }
    data.update(overrides)
    return data


def request(action, arguments, *, suffix="x", resource=RESOURCE):
    return EffectRequest.create(
        request_id=f"effect:b002:{suffix}",
        run_id="run:b002",
        principal_id="principal:owner",
        agent_id="agent:calendar-consumer",
        action=action,
        resource=resource,
        arguments=arguments,
        idempotency_key=f"idem:b002:{suffix}",
        created_at="2026-09-16T18:00:00Z",
        expires_at="2026-09-16T19:00:00Z",
    )


def lease(req):
    return ExecutionLease.create(
        lease_id=f"lease:{req.request_id}",
        request_id=req.request_id,
        executor_id="executor:b002",
        issued_at="2026-09-16T18:00:01Z",
        expires_at="2026-09-16T18:00:30Z",
    )


class Secrets:
    def __init__(self):
        self.calls = []
        self.secret = object()
    def resolve(self, ref):
        self.calls.append(ref)
        return self.secret


class Transport:
    def __init__(self):
        self.calls = []
        self.mutations = {}
    def search(self, **kwargs):
        self.calls.append(("search", kwargs))
        return {"events": []}
    def read(self, *, event_id):
        self.calls.append(("read", event_id))
        return {"event": {"id": event_id}}
    def create(self, *, event, request_id, idempotency_key):
        self.calls.append(("create", request_id, idempotency_key, event))
        result = {"event": {"id": "evt-create"}, "upstream_reference": "gcal:event:evt-create"}
        self.mutations[(CALENDAR_CREATE_ACTION, request_id, idempotency_key)] = result
        return result
    def modify(self, *, event_id, event_etag, event, request_id, idempotency_key):
        self.calls.append(("modify", event_id, event_etag, request_id, event))
        result = {"event": {"id": event_id}, "upstream_reference": "gcal:event:" + event_id}
        self.mutations[(CALENDAR_MODIFY_ACTION, request_id, idempotency_key)] = result
        return result
    def cancel(self, *, event_id, event_etag, send_updates, request_id, idempotency_key):
        self.calls.append(("cancel", event_id, event_etag, send_updates, request_id))
        result = {"event": {"id": event_id, "status": "cancelled"}, "upstream_reference": "gcal:event:" + event_id}
        self.mutations[(CALENDAR_CANCEL_ACTION, request_id, idempotency_key)] = result
        return result
    def reconcile(self, *, action, request_id, idempotency_key, operation):
        self.calls.append(("reconcile", action, request_id, idempotency_key))
        return self.mutations.get((action, request_id, idempotency_key))


class Factory:
    def __init__(self, transport):
        self.transport = transport
        self.calls = []
    def create(self, *, calendar_resource, secret):
        self.calls.append((calendar_resource, secret))
        return self.transport


class LeakyTransport(Transport):
    def read(self, *, event_id):
        return {"event": {"id": event_id}, "access_token": "SYNTHETIC_NOT_REAL"}


class CalendarAdapterTests(unittest.TestCase):
    def setUp(self):
        self.secrets = Secrets()
        self.transport = Transport()
        self.factory = Factory(self.transport)
        self.adapter = CalendarEffectAdapter(secret_provider=self.secrets, transport_factory=self.factory)

    def test_supports_all_canonical_actions_without_resolving_credentials(self):
        cases = [
            request(CALENDAR_SEARCH_ACTION, {"time_min":"2026-10-01T00:00:00Z","time_max":"2026-10-02T00:00:00Z","query":"","max_results":10}, suffix="search"),
            request(CALENDAR_READ_ACTION, {"event_id":"evt_1"}, suffix="read"),
            request(CALENDAR_PROPOSE_ACTION, event_args(), suffix="propose"),
            request(CALENDAR_CREATE_ACTION, event_args(), suffix="create"),
            request(CALENDAR_MODIFY_ACTION, {"event_id":"evt_1","event_etag":"\"v1\"", **event_args()}, suffix="modify"),
            request(CALENDAR_CANCEL_ACTION, {"event_id":"evt_1","event_etag":"\"v1\"","send_updates":"none"}, suffix="cancel"),
            request(CALENDAR_DELETE_ACTION, {"event_id":"evt_1","event_etag":"\"v1\""}, suffix="delete"),
        ]
        for req in cases:
            with self.subTest(req.action):
                self.assertTrue(self.adapter.supports(req))
        self.assertEqual(self.secrets.calls, [])
        self.assertEqual(self.factory.calls, [])

    def test_malformed_material_fails_closed_before_credentials(self):
        self.assertFalse(self.adapter.supports(request("calendar.invite", {}, suffix="unknown")))
        self.assertFalse(self.adapter.supports(request(CALENDAR_CREATE_ACTION, event_args(timezone="Not/AZone"), suffix="tz")))
        self.assertFalse(self.adapter.supports(request(CALENDAR_CREATE_ACTION, event_args(attendees=["owner@example.com", "alpha@example.com"]), suffix="order")))
        self.assertFalse(self.adapter.supports(request(CALENDAR_CREATE_ACTION, event_args(end="2026-10-01T12:00:00-04:00"), suffix="time")))
        self.assertEqual(self.secrets.calls, [])

    def test_propose_is_local_and_never_resolves_service_credential(self):
        req = request(CALENDAR_PROPOSE_ACTION, event_args(), suffix="proposal")
        result = self.adapter.invoke(req, lease=lease(req))
        self.assertTrue(result.data["synthetic"])
        self.assertEqual(result.data["proposal"]["title"], "Synthetic planning event")
        self.assertEqual(self.secrets.calls, [])
        self.assertEqual(self.transport.calls, [])

    def test_delete_has_no_mutation_implementation(self):
        req = request(CALENDAR_DELETE_ACTION, {"event_id":"evt_1","event_etag":"\"v1\""}, suffix="delete")
        with self.assertRaises(CalendarEffectError):
            self.adapter.invoke(req, lease=lease(req))
        self.assertEqual(self.secrets.calls, [])

    def test_create_resolves_opaque_secret_only_at_invoke_boundary(self):
        req = request(CALENDAR_CREATE_ACTION, event_args(), suffix="create")
        result = self.adapter.invoke(req, lease=lease(req))
        self.assertEqual(result.upstream_reference, "gcal:event:evt-create")
        self.assertEqual(self.secrets.calls, ["google-calendar:primary"])
        self.assertIs(self.factory.calls[0][1], self.secrets.secret)
        self.assertNotIn("credential", repr(result.to_record()).lower())

    def test_credential_shaped_provider_result_is_rejected(self):
        adapter = CalendarEffectAdapter(secret_provider=self.secrets, transport_factory=Factory(LeakyTransport()))
        req = request(CALENDAR_READ_ACTION, {"event_id":"evt_1"}, suffix="leak")
        with self.assertRaises(CalendarEffectError):
            adapter.invoke(req, lease=lease(req))

    def test_mutation_reconcile_does_not_repeat_mutation(self):
        req = request(CALENDAR_CREATE_ACTION, event_args(), suffix="reconcile")
        first = self.adapter.invoke(req, lease=lease(req))
        before = len([c for c in self.transport.calls if c[0] == "create"])
        reconciled = self.adapter.reconcile(req, lease=lease(req))
        after = len([c for c in self.transport.calls if c[0] == "create"])
        self.assertEqual((before, after), (1, 1))
        self.assertEqual(reconciled.upstream_reference, first.upstream_reference)

    def test_all_security_relevant_mutation_material_changes_canonical_hash(self):
        base = request(CALENDAR_CREATE_ACTION, event_args(), suffix="binding")
        variants = {
            "calendar": request(CALENDAR_CREATE_ACTION, event_args(), suffix="binding", resource="calendar:team"),
            "title": request(CALENDAR_CREATE_ACTION, event_args(title="Changed"), suffix="binding"),
            "start": request(CALENDAR_CREATE_ACTION, event_args(start="2026-10-01T13:30:00-04:00"), suffix="binding"),
            "end": request(CALENDAR_CREATE_ACTION, event_args(end="2026-10-01T14:30:00-04:00"), suffix="binding"),
            "timezone": request(CALENDAR_CREATE_ACTION, event_args(timezone="UTC"), suffix="binding"),
            "attendees": request(CALENDAR_CREATE_ACTION, event_args(attendees=["alpha@example.com"]), suffix="binding"),
            "location": request(CALENDAR_CREATE_ACTION, event_args(location="Elsewhere"), suffix="binding"),
            "recurrence": request(CALENDAR_CREATE_ACTION, event_args(recurrence=["RRULE:FREQ=DAILY;COUNT=2"]), suffix="binding"),
            "conference": request(CALENDAR_CREATE_ACTION, event_args(conference_settings={"enabled":True,"solution_type":"hangoutsMeet"}), suffix="binding"),
            "notifications": request(CALENDAR_CREATE_ACTION, event_args(send_updates="all"), suffix="binding"),
        }
        for field, mutated in variants.items():
            with self.subTest(field):
                self.assertNotEqual(base.canonical_hash, mutated.canonical_hash)

    def test_modify_and_cancel_bind_event_identity_etag_and_material(self):
        base = request(CALENDAR_MODIFY_ACTION, {"event_id":"evt_1","event_etag":"\"v1\"", **event_args()}, suffix="modify-bind")
        for mutated in (
            request(CALENDAR_MODIFY_ACTION, {"event_id":"evt_2","event_etag":"\"v1\"", **event_args()}, suffix="modify-bind"),
            request(CALENDAR_MODIFY_ACTION, {"event_id":"evt_1","event_etag":"\"v2\"", **event_args()}, suffix="modify-bind"),
            request(CALENDAR_MODIFY_ACTION, {"event_id":"evt_1","event_etag":"\"v1\"", **event_args(title="Changed")}, suffix="modify-bind"),
        ):
            self.assertNotEqual(base.canonical_hash, mutated.canonical_hash)

if __name__ == "__main__":
    unittest.main()
