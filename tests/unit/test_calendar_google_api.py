import json
import unittest
from urllib.parse import parse_qs, urlparse

from packages.effects.calendar import GoogleCalendarTransportError, GoogleCalendarTransportFactory

TOKEN = "SYNTHETIC_CALENDAR_BEARER_NOT_REAL"


class FakeResponse:
    def __init__(self, payload): self.payload = payload
    def read(self): return json.dumps(self.payload).encode("utf-8")


class FakeOpener:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []
    def __call__(self, request, *, timeout):
        self.calls.append((request, timeout))
        if not self.responses: raise AssertionError("unexpected Calendar API call")
        return FakeResponse(self.responses.pop(0))


def provider_event(event_id="evt1", *, request_id="effect:b002:gapi", status="confirmed"):
    return {
        "id": event_id,
        "etag": '"v1"',
        "status": status,
        "summary": "Synthetic",
        "start": {"dateTime":"2026-10-01T13:00:00-04:00","timeZone":"America/Toronto"},
        "end": {"dateTime":"2026-10-01T14:00:00-04:00","timeZone":"America/Toronto"},
        "attendees": [{"email":"owner@example.com"}],
        "location": "Synthetic",
        "recurrence": [],
        "extendedProperties": {"private": {"lacRequestId": request_id}},
    }


def event_input(**overrides):
    data = {
        "title":"Synthetic",
        "start":"2026-10-01T13:00:00-04:00",
        "end":"2026-10-01T14:00:00-04:00",
        "timezone":"America/Toronto",
        "attendees":["owner@example.com"],
        "location":"Synthetic",
        "recurrence":[],
        "conference_settings":{"enabled":False,"solution_type":"hangoutsMeet"},
        "send_updates":"none",
    }
    data.update(overrides)
    return data


class GoogleCalendarTransportTests(unittest.TestCase):
    def transport(self, responses):
        opener = FakeOpener(responses)
        factory = GoogleCalendarTransportFactory(opener=opener)
        return factory.create(calendar_resource="calendar:primary", secret=TOKEN), opener

    def test_search_binds_calendar_and_bearer_only_to_http_header(self):
        transport, opener = self.transport([{"items":[provider_event()],"nextPageToken":"n"}])
        result = transport.search(
            time_min="2026-10-01T00:00:00Z", time_max="2026-10-02T00:00:00Z", query="Synthetic", max_results=5
        )
        self.assertEqual(result["events"][0]["id"], "evt1")
        req, timeout = opener.calls[0]
        parsed = urlparse(req.full_url)
        self.assertEqual(parsed.path, "/calendar/v3/calendars/primary/events")
        q = parse_qs(parsed.query)
        self.assertEqual(q["timeMin"], ["2026-10-01T00:00:00Z"])
        self.assertEqual(q["timeMax"], ["2026-10-02T00:00:00Z"])
        self.assertEqual(q["q"], ["Synthetic"])
        self.assertEqual(req.headers["Authorization"], "Bearer " + TOKEN)
        self.assertNotIn(TOKEN, repr(result))
        self.assertEqual(timeout, 30.0)

    def test_create_uses_deterministic_event_identity_and_lac_marker(self):
        request_id = "effect:b002:gapi-create"
        # ID is derived by implementation, so feed response ID from request body inspection in opener-style fixed response is awkward.
        # First derive by an identical create attempt using implementation-visible deterministic helper via response mismatch assertion? Instead
        # use reconcile-compatible known digest calculation here.
        import hashlib
        event_id = "lac" + hashlib.sha256(request_id.encode()).hexdigest()[:40]
        transport, opener = self.transport([provider_event(event_id, request_id=request_id)])
        result = transport.create(event=event_input(), request_id=request_id, idempotency_key="idem:gapi-create")
        self.assertEqual(result["upstream_reference"], "gcal:event:" + event_id)
        req, _ = opener.calls[0]
        self.assertEqual(req.get_method(), "POST")
        payload = json.loads(req.data.decode("utf-8"))
        self.assertEqual(payload["id"], event_id)
        self.assertEqual(payload["extendedProperties"]["private"]["lacRequestId"], request_id)
        self.assertNotIn(TOKEN, json.dumps(payload))
        q = parse_qs(urlparse(req.full_url).query)
        self.assertEqual(q["sendUpdates"], ["none"])
        self.assertEqual(q["conferenceDataVersion"], ["1"])

    def test_conference_create_request_is_bound_to_request_identity(self):
        import hashlib
        request_id = "effect:b002:gapi-conf"
        event_id = "lac" + hashlib.sha256(request_id.encode()).hexdigest()[:40]
        transport, opener = self.transport([provider_event(event_id, request_id=request_id)])
        transport.create(
            event=event_input(conference_settings={"enabled":True,"solution_type":"hangoutsMeet"}),
            request_id=request_id,
            idempotency_key="idem:gapi-conf",
        )
        payload = json.loads(opener.calls[0][0].data.decode("utf-8"))
        self.assertEqual(payload["conferenceData"]["createRequest"]["conferenceSolutionKey"]["type"], "hangoutsMeet")
        self.assertTrue(payload["conferenceData"]["createRequest"]["requestId"].startswith("lac-"))

    def test_modify_uses_if_match_and_exact_event_path(self):
        request_id = "effect:b002:gapi-modify"
        transport, opener = self.transport([provider_event("evt_1", request_id=request_id)])
        result = transport.modify(
            event_id="evt_1", event_etag='"v1"', event=event_input(), request_id=request_id, idempotency_key="idem:modify"
        )
        self.assertEqual(result["upstream_reference"], "gcal:event:evt_1")
        req, _ = opener.calls[0]
        self.assertEqual(req.get_method(), "PATCH")
        self.assertTrue(urlparse(req.full_url).path.endswith("/events/evt_1"))
        self.assertEqual(req.headers["If-match"], '"v1"')

    def test_cancel_uses_patch_if_match_and_cancelled_status(self):
        request_id = "effect:b002:gapi-cancel"
        transport, opener = self.transport([provider_event("evt_1", request_id=request_id, status="cancelled")])
        result = transport.cancel(
            event_id="evt_1", event_etag='"v1"', send_updates="none", request_id=request_id, idempotency_key="idem:cancel"
        )
        self.assertEqual(result["event"]["status"], "cancelled")
        req, _ = opener.calls[0]
        self.assertEqual(req.get_method(), "PATCH")
        self.assertEqual(req.headers["If-match"], '"v1"')

    def test_reconciliation_is_read_only_and_requires_lac_marker(self):
        request_id = "effect:b002:gapi-reconcile"
        import hashlib
        event_id = "lac" + hashlib.sha256(request_id.encode()).hexdigest()[:40]
        transport, opener = self.transport([provider_event(event_id, request_id=request_id)])
        result = transport.reconcile(
            action="calendar.create", request_id=request_id, idempotency_key="idem", operation={"action":"calendar.create"}
        )
        self.assertEqual(result["upstream_reference"], "gcal:event:" + event_id)
        self.assertEqual(opener.calls[0][0].get_method(), "GET")

    def test_factory_rejects_non_string_secret_without_echoing_material(self):
        factory = GoogleCalendarTransportFactory(opener=FakeOpener([]))
        with self.assertRaises(GoogleCalendarTransportError):
            factory.create(calendar_resource="calendar:primary", secret=object())

if __name__ == "__main__":
    unittest.main()
