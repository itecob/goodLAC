from __future__ import annotations

import hashlib
import json
from typing import Any, Callable, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen

from .adapter import (
    CALENDAR_CANCEL_ACTION,
    CALENDAR_CREATE_ACTION,
    CALENDAR_MODIFY_ACTION,
    CalendarTransport,
)

CALENDAR_API_BASE = "https://www.googleapis.com/calendar/v3/calendars"


class GoogleCalendarTransportError(RuntimeError):
    """Google Calendar REST boundary failed closed without exposing credentials."""


def _event_id_for_request(request_id: str) -> str:
    # Google event IDs accept base32hex-compatible lowercase digits/letters. sha256 hex is a subset.
    return "lac" + hashlib.sha256(request_id.encode("utf-8")).hexdigest()[:40]


def _conference_request_id(request_id: str) -> str:
    return "lac-" + hashlib.sha256(("conference:" + request_id).encode("utf-8")).hexdigest()[:32]


def _normalize_event(raw: Mapping[str, Any]) -> dict[str, Any]:
    event_id = raw.get("id")
    if not isinstance(event_id, str) or not event_id:
        raise GoogleCalendarTransportError("Calendar event response lacks id")
    start = raw.get("start") if isinstance(raw.get("start"), Mapping) else {}
    end = raw.get("end") if isinstance(raw.get("end"), Mapping) else {}
    attendees = raw.get("attendees") if isinstance(raw.get("attendees"), list) else []
    private = raw.get("extendedProperties") if isinstance(raw.get("extendedProperties"), Mapping) else {}
    private = private.get("private") if isinstance(private.get("private"), Mapping) else {}
    return {
        "id": event_id,
        "etag": raw.get("etag") if isinstance(raw.get("etag"), str) else None,
        "status": raw.get("status") if isinstance(raw.get("status"), str) else None,
        "title": raw.get("summary") if isinstance(raw.get("summary"), str) else "",
        "start": start.get("dateTime") if isinstance(start.get("dateTime"), str) else None,
        "end": end.get("dateTime") if isinstance(end.get("dateTime"), str) else None,
        "timezone": start.get("timeZone") if isinstance(start.get("timeZone"), str) else None,
        "attendees": sorted(
            item["email"].lower()
            for item in attendees
            if isinstance(item, Mapping) and isinstance(item.get("email"), str)
        ),
        "location": raw.get("location") if isinstance(raw.get("location"), str) else "",
        "recurrence": raw.get("recurrence") if isinstance(raw.get("recurrence"), list) else [],
        "lac_request_id": private.get("lacRequestId") if isinstance(private.get("lacRequestId"), str) else None,
    }


class GoogleCalendarTransportFactory:
    """Creates a REST transport from an opaque OAuth bearer-token capability."""

    def __init__(
        self,
        *,
        opener: Callable[..., Any] | None = None,
        api_base: str = CALENDAR_API_BASE,
        timeout_seconds: float = 30.0,
    ) -> None:
        if not isinstance(api_base, str) or not api_base.startswith("https://"):
            raise GoogleCalendarTransportError("api_base must be an https URL")
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)) or timeout_seconds <= 0:
            raise GoogleCalendarTransportError("timeout_seconds must be positive")
        self._opener = opener or urlopen
        self._api_base = api_base.rstrip("/")
        self._timeout = float(timeout_seconds)

    def create(self, *, calendar_resource: str, secret: object) -> CalendarTransport:
        if not isinstance(calendar_resource, str) or not calendar_resource.startswith("calendar:"):
            raise GoogleCalendarTransportError("calendar_resource must be a canonical calendar selector")
        if not isinstance(secret, str) or not secret:
            raise GoogleCalendarTransportError("Calendar bearer-token capability is unavailable")
        calendar_id = calendar_resource.split(":", 1)[1]
        if not calendar_id:
            raise GoogleCalendarTransportError("calendar_resource lacks calendar identity")
        return GoogleCalendarTransport(
            access_token=secret,
            calendar_id=calendar_id,
            opener=self._opener,
            api_base=self._api_base,
            timeout_seconds=self._timeout,
        )


class GoogleCalendarTransport:
    __slots__ = ("_access_token", "_calendar_id", "_opener", "_api_base", "_timeout")

    def __init__(self, *, access_token: str, calendar_id: str, opener: Callable[..., Any], api_base: str, timeout_seconds: float) -> None:
        self._access_token = access_token
        self._calendar_id = calendar_id
        self._opener = opener
        self._api_base = api_base
        self._timeout = timeout_seconds

    @property
    def _events_path(self) -> str:
        return "/" + quote(self._calendar_id, safe="") + "/events"

    def _request_json(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: Mapping[str, Any] | None = None,
        if_match: str | None = None,
    ) -> dict[str, Any]:
        url = self._api_base + path
        if query:
            url += "?" + urlencode(query, doseq=True)
        data = None if body is None else json.dumps(body, separators=(",", ":")).encode("utf-8")
        headers = {
            "Accept": "application/json",
            "Authorization": "Bearer " + self._access_token,
            "Content-Type": "application/json",
        }
        if if_match is not None:
            headers["If-Match"] = if_match
        request = Request(url, data=data, method=method, headers=headers)
        try:
            response = self._opener(request, timeout=self._timeout)
            raw = response.read()
        except HTTPError as exc:
            raise GoogleCalendarTransportError(f"Calendar API returned HTTP {exc.code}") from None
        except (URLError, TimeoutError, OSError):
            raise GoogleCalendarTransportError("Calendar API request failed") from None
        try:
            parsed = json.loads(raw.decode("utf-8")) if raw else {}
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise GoogleCalendarTransportError("Calendar API returned invalid JSON") from exc
        if not isinstance(parsed, dict):
            raise GoogleCalendarTransportError("Calendar API response must be an object")
        return parsed

    @staticmethod
    def _event_body(event: Mapping[str, Any], *, request_id: str, event_id: str | None = None) -> dict[str, Any]:
        conference = event.get("conference_settings")
        if not isinstance(conference, Mapping):
            raise GoogleCalendarTransportError("Calendar event lacks canonical conference settings")
        body: dict[str, Any] = {
            "summary": event.get("title", ""),
            "start": {"dateTime": event.get("start"), "timeZone": event.get("timezone")},
            "end": {"dateTime": event.get("end"), "timeZone": event.get("timezone")},
            "attendees": [{"email": email} for email in event.get("attendees", [])],
            "location": event.get("location", ""),
            "recurrence": list(event.get("recurrence", [])),
            "extendedProperties": {"private": {"lacRequestId": request_id}},
        }
        if event_id is not None:
            body["id"] = event_id
        if conference.get("enabled") is True:
            body["conferenceData"] = {
                "createRequest": {
                    "requestId": _conference_request_id(request_id),
                    "conferenceSolutionKey": {"type": conference.get("solution_type")},
                }
            }
        return body

    def search(self, *, time_min: str, time_max: str, query: str, max_results: int) -> Mapping[str, Any]:
        raw = self._request_json(
            "GET",
            self._events_path,
            query={
                "timeMin": time_min,
                "timeMax": time_max,
                "q": query,
                "maxResults": max_results,
                "singleEvents": "true",
                "orderBy": "startTime",
            },
        )
        items = raw.get("items") if isinstance(raw.get("items"), list) else []
        return {
            "events": [_normalize_event(item) for item in items if isinstance(item, Mapping)],
            "next_page_token": raw.get("nextPageToken") if isinstance(raw.get("nextPageToken"), str) else None,
        }

    def read(self, *, event_id: str) -> Mapping[str, Any]:
        raw = self._request_json("GET", self._events_path + "/" + quote(event_id, safe=""))
        return {"event": _normalize_event(raw)}

    def create(self, *, event: Mapping[str, Any], request_id: str, idempotency_key: str) -> Mapping[str, Any]:
        event_id = _event_id_for_request(request_id)
        raw = self._request_json(
            "POST",
            self._events_path,
            query={"sendUpdates": event.get("send_updates"), "conferenceDataVersion": 1},
            body=self._event_body(event, request_id=request_id, event_id=event_id),
        )
        normalized = _normalize_event(raw)
        if normalized["id"] != event_id:
            raise GoogleCalendarTransportError("Calendar create response binds a different event id")
        return {"event": normalized, "upstream_reference": "gcal:event:" + event_id}

    def modify(self, *, event_id: str, event_etag: str, event: Mapping[str, Any], request_id: str, idempotency_key: str) -> Mapping[str, Any]:
        raw = self._request_json(
            "PATCH",
            self._events_path + "/" + quote(event_id, safe=""),
            query={"sendUpdates": event.get("send_updates"), "conferenceDataVersion": 1},
            body=self._event_body(event, request_id=request_id),
            if_match=event_etag,
        )
        normalized = _normalize_event(raw)
        if normalized["id"] != event_id:
            raise GoogleCalendarTransportError("Calendar modify response binds a different event")
        return {"event": normalized, "upstream_reference": "gcal:event:" + event_id}

    def cancel(self, *, event_id: str, event_etag: str, send_updates: str, request_id: str, idempotency_key: str) -> Mapping[str, Any]:
        raw = self._request_json(
            "PATCH",
            self._events_path + "/" + quote(event_id, safe=""),
            query={"sendUpdates": send_updates},
            body={
                "status": "cancelled",
                "extendedProperties": {"private": {"lacRequestId": request_id}},
            },
            if_match=event_etag,
        )
        normalized = _normalize_event(raw)
        if normalized["id"] != event_id or normalized["status"] != "cancelled":
            raise GoogleCalendarTransportError("Calendar cancel response is not a cancelled bound event")
        return {"event": normalized, "upstream_reference": "gcal:event:" + event_id}

    def reconcile(self, *, action: str, request_id: str, idempotency_key: str, operation: Mapping[str, Any]) -> Mapping[str, Any] | None:
        if action == CALENDAR_CREATE_ACTION:
            event_id = _event_id_for_request(request_id)
        else:
            event_id = operation.get("event_id")
            if not isinstance(event_id, str) or not event_id:
                raise GoogleCalendarTransportError("Calendar reconciliation lacks event identity")
        raw = self._request_json("GET", self._events_path + "/" + quote(event_id, safe=""))
        normalized = _normalize_event(raw)
        if normalized["lac_request_id"] != request_id:
            return None
        if action == CALENDAR_CANCEL_ACTION and normalized["status"] != "cancelled":
            return None
        if action not in {CALENDAR_CREATE_ACTION, CALENDAR_MODIFY_ACTION, CALENDAR_CANCEL_ACTION}:
            raise GoogleCalendarTransportError("unsupported Calendar mutation reconciliation action")
        return {"event": normalized, "upstream_reference": "gcal:event:" + event_id}
