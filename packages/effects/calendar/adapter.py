from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Mapping, Protocol, runtime_checkable
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from packages.core import EffectRequest, EffectRequestError, ExecutionLease, ExecutionLeaseError
from packages.core.effect_request import canonical_json
from packages.credentials import SecretProvider, SecretProviderError, validate_credential_ref

CALENDAR_ADAPTER_ID = "calendar:v1"
CALENDAR_RESULT_SCHEMA = "lac.calendar-effect-result/v1"
CALENDAR_SEARCH_ACTION = "calendar.search"
CALENDAR_READ_ACTION = "calendar.read"
CALENDAR_PROPOSE_ACTION = "calendar.propose"
CALENDAR_CREATE_ACTION = "calendar.create"
CALENDAR_MODIFY_ACTION = "calendar.modify"
CALENDAR_CANCEL_ACTION = "calendar.cancel"
CALENDAR_DELETE_ACTION = "calendar.delete"
CALENDAR_ACTIONS = frozenset({
    CALENDAR_SEARCH_ACTION,
    CALENDAR_READ_ACTION,
    CALENDAR_PROPOSE_ACTION,
    CALENDAR_CREATE_ACTION,
    CALENDAR_MODIFY_ACTION,
    CALENDAR_CANCEL_ACTION,
    CALENDAR_DELETE_ACTION,
})

_EMAIL_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_EVENT_ID_RE = re.compile(r"^[A-Za-z0-9_-]{1,1024}$")
_ETAG_RE = re.compile(r'^"[^"\r\n]{1,1022}"$')
_RECURRENCE_PREFIXES = ("RRULE:", "RDATE:", "EXRULE:", "EXDATE:")
_FORBIDDEN_RESULT_KEYS = frozenset({
    "access_token", "authorization", "client_secret", "credential", "credential_ref",
    "credentials", "refresh_token", "secret", "token",
})


class CalendarEffectError(ValueError):
    """Calendar typed-effect/provider boundary failed closed."""


def _required_text(value: object, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value:
        raise CalendarEffectError(f"{field} must be non-empty text")
    if value != value.strip():
        raise CalendarEffectError(f"{field} must not have leading/trailing whitespace")
    if len(value) > maximum or any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise CalendarEffectError(f"{field} is not bounded canonical text")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CalendarEffectError(f"{field} must be valid UTF-8") from exc
    return value


def _optional_text(value: object, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str):
        raise CalendarEffectError(f"{field} must be text")
    if len(value) > maximum or "\r" in value or "\n" in value:
        raise CalendarEffectError(f"{field} is not bounded canonical text")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise CalendarEffectError(f"{field} must be valid UTF-8") from exc
    return value


def _canonical_request(request: EffectRequest) -> EffectRequest:
    if not isinstance(request, EffectRequest):
        raise CalendarEffectError("request must be a canonical EffectRequest")
    try:
        canonical = EffectRequest.from_record(request.to_record())
    except (EffectRequestError, TypeError, AttributeError) as exc:
        raise CalendarEffectError("request failed canonical integrity validation") from exc
    if canonical != request:
        raise CalendarEffectError("request is not canonical")
    return canonical


def _canonical_lease(lease: ExecutionLease) -> ExecutionLease:
    if not isinstance(lease, ExecutionLease):
        raise CalendarEffectError("lease must be a canonical ExecutionLease")
    try:
        canonical = ExecutionLease.from_record(lease.to_record())
    except (ExecutionLeaseError, TypeError, AttributeError) as exc:
        raise CalendarEffectError("lease failed canonical integrity validation") from exc
    if canonical != lease:
        raise CalendarEffectError("lease is not canonical")
    return canonical


def _rfc3339(value: object, field: str) -> str:
    value = _required_text(value, field, maximum=64)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise CalendarEffectError(f"{field} must be RFC3339 date-time") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise CalendarEffectError(f"{field} must contain an explicit UTC offset")
    return value


def _timezone(value: object) -> str:
    value = _required_text(value, "timezone", maximum=128)
    try:
        ZoneInfo(value)
    except ZoneInfoNotFoundError as exc:
        raise CalendarEffectError("timezone must be a known IANA timezone") from exc
    return value


def _email(value: object) -> str:
    value = _required_text(value, "attendee", maximum=320)
    if not _EMAIL_RE.fullmatch(value):
        raise CalendarEffectError("attendee must be a canonical mailbox address")
    if value != value.lower():
        raise CalendarEffectError("attendee must use lowercase canonical mailbox form")
    return value


def _attendees(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 100:
        raise CalendarEffectError("attendees must be a bounded JSON array")
    normalized = tuple(_email(item) for item in value)
    if tuple(sorted(normalized)) != normalized or len(set(normalized)) != len(normalized):
        raise CalendarEffectError("attendees must be sorted and unique")
    return normalized


def _recurrence(value: object) -> tuple[str, ...]:
    if not isinstance(value, list) or len(value) > 25:
        raise CalendarEffectError("recurrence must be a bounded JSON array")
    result: list[str] = []
    for item in value:
        item = _required_text(item, "recurrence[]", maximum=2048)
        if not item.startswith(_RECURRENCE_PREFIXES):
            raise CalendarEffectError("recurrence entries must be RRULE/RDATE/EXRULE/EXDATE")
        result.append(item)
    normalized = tuple(result)
    if tuple(sorted(normalized)) != normalized or len(set(normalized)) != len(normalized):
        raise CalendarEffectError("recurrence must be sorted and unique")
    return normalized


def _conference(value: object) -> dict[str, Any]:
    if not isinstance(value, Mapping) or set(value) != {"enabled", "solution_type"}:
        raise CalendarEffectError("conference_settings must contain exactly enabled and solution_type")
    enabled = value["enabled"]
    solution = value["solution_type"]
    if not isinstance(enabled, bool):
        raise CalendarEffectError("conference_settings.enabled must be boolean")
    if solution != "hangoutsMeet":
        raise CalendarEffectError("conference_settings.solution_type must be hangoutsMeet")
    return {"enabled": enabled, "solution_type": solution}


def _event_id(value: object) -> str:
    value = _required_text(value, "event_id", maximum=1024)
    if not _EVENT_ID_RE.fullmatch(value):
        raise CalendarEffectError("event_id must be bounded opaque event identity")
    return value


def _etag(value: object) -> str:
    if not isinstance(value, str) or not _ETAG_RE.fullmatch(value):
        raise CalendarEffectError("event_etag must be a quoted canonical entity tag")
    return value


def _send_updates(value: object) -> str:
    if value not in {"all", "externalOnly", "none"}:
        raise CalendarEffectError("send_updates must be all, externalOnly, or none")
    return str(value)


@dataclass(frozen=True)
class CalendarEventInput:
    title: str
    start: str
    end: str
    timezone: str
    attendees: tuple[str, ...]
    location: str
    recurrence: tuple[str, ...]
    conference_settings: dict[str, Any]
    send_updates: str

    def to_transport_record(self) -> dict[str, Any]:
        return {
            "title": self.title,
            "start": self.start,
            "end": self.end,
            "timezone": self.timezone,
            "attendees": list(self.attendees),
            "location": self.location,
            "recurrence": list(self.recurrence),
            "conference_settings": dict(self.conference_settings),
            "send_updates": self.send_updates,
        }


@dataclass(frozen=True)
class _CalendarOperation:
    action: str
    event_id: str | None = None
    event_etag: str | None = None
    event: CalendarEventInput | None = None
    time_min: str | None = None
    time_max: str | None = None
    query: str | None = None
    max_results: int | None = None
    send_updates: str | None = None


def _event_input(arguments: Mapping[str, Any]) -> CalendarEventInput:
    required = {
        "title", "start", "end", "timezone", "attendees", "location",
        "recurrence", "conference_settings", "send_updates",
    }
    if set(arguments) != required:
        raise CalendarEffectError("event arguments do not match the canonical Calendar event shape")
    title = _optional_text(arguments["title"], "title", maximum=1024)
    start = _rfc3339(arguments["start"], "start")
    end = _rfc3339(arguments["end"], "end")
    start_dt = datetime.fromisoformat(start[:-1] + "+00:00" if start.endswith("Z") else start)
    end_dt = datetime.fromisoformat(end[:-1] + "+00:00" if end.endswith("Z") else end)
    if end_dt <= start_dt:
        raise CalendarEffectError("event end must be after start")
    return CalendarEventInput(
        title=title,
        start=start,
        end=end,
        timezone=_timezone(arguments["timezone"]),
        attendees=_attendees(arguments["attendees"]),
        location=_optional_text(arguments["location"], "location", maximum=2048),
        recurrence=_recurrence(arguments["recurrence"]),
        conference_settings=_conference(arguments["conference_settings"]),
        send_updates=_send_updates(arguments["send_updates"]),
    )


def _parse_operation(request: EffectRequest, *, resource: str) -> _CalendarOperation:
    canonical = _canonical_request(request)
    if canonical.resource != resource:
        raise CalendarEffectError("Calendar request targets a different configured calendar resource")
    if canonical.action not in CALENDAR_ACTIONS:
        raise CalendarEffectError(f"unsupported Calendar action: {canonical.action!r}")
    a = canonical.arguments
    if canonical.action == CALENDAR_SEARCH_ACTION:
        if set(a) != {"time_min", "time_max", "query", "max_results"}:
            raise CalendarEffectError("calendar.search arguments are invalid")
        time_min = _rfc3339(a["time_min"], "time_min")
        time_max = _rfc3339(a["time_max"], "time_max")
        lo = datetime.fromisoformat(time_min[:-1] + "+00:00" if time_min.endswith("Z") else time_min)
        hi = datetime.fromisoformat(time_max[:-1] + "+00:00" if time_max.endswith("Z") else time_max)
        if hi <= lo:
            raise CalendarEffectError("calendar.search time_max must be after time_min")
        max_results = a["max_results"]
        if isinstance(max_results, bool) or not isinstance(max_results, int) or not 1 <= max_results <= 250:
            raise CalendarEffectError("max_results must be an integer from 1 through 250")
        return _CalendarOperation(
            action=canonical.action,
            time_min=time_min,
            time_max=time_max,
            query=_optional_text(a["query"], "query", maximum=2048),
            max_results=max_results,
        )
    if canonical.action == CALENDAR_READ_ACTION:
        if set(a) != {"event_id"}:
            raise CalendarEffectError("calendar.read arguments must contain exactly event_id")
        return _CalendarOperation(action=canonical.action, event_id=_event_id(a["event_id"]))
    if canonical.action in {CALENDAR_PROPOSE_ACTION, CALENDAR_CREATE_ACTION}:
        return _CalendarOperation(action=canonical.action, event=_event_input(a))
    if canonical.action == CALENDAR_MODIFY_ACTION:
        if set(a) != {"event_id", "event_etag", "title", "start", "end", "timezone", "attendees", "location", "recurrence", "conference_settings", "send_updates"}:
            raise CalendarEffectError("calendar.modify arguments are invalid")
        event_material = {k: v for k, v in a.items() if k not in {"event_id", "event_etag"}}
        return _CalendarOperation(
            action=canonical.action,
            event_id=_event_id(a["event_id"]),
            event_etag=_etag(a["event_etag"]),
            event=_event_input(event_material),
        )
    if canonical.action == CALENDAR_CANCEL_ACTION:
        if set(a) != {"event_id", "event_etag", "send_updates"}:
            raise CalendarEffectError("calendar.cancel arguments are invalid")
        return _CalendarOperation(
            action=canonical.action,
            event_id=_event_id(a["event_id"]),
            event_etag=_etag(a["event_etag"]),
            send_updates=_send_updates(a["send_updates"]),
        )
    if canonical.action == CALENDAR_DELETE_ACTION:
        if set(a) != {"event_id", "event_etag"}:
            raise CalendarEffectError("calendar.delete arguments are invalid")
        return _CalendarOperation(
            action=canonical.action,
            event_id=_event_id(a["event_id"]),
            event_etag=_etag(a["event_etag"]),
        )
    raise CalendarEffectError("unknown Calendar action fails closed")


def _validate_result_value(value: Any, *, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int, float)):
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_result_value(item, path=f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CalendarEffectError("Calendar provider result contains a non-string key")
            if key.lower() in _FORBIDDEN_RESULT_KEYS:
                raise CalendarEffectError("Calendar provider result contains credential-shaped material")
            _validate_result_value(item, path=f"{path}.{key}")
        return
    raise CalendarEffectError(f"Calendar provider result contains unsupported value at {path}")


def _safe_result_record(value: object) -> tuple[dict[str, Any], str | None]:
    if not isinstance(value, Mapping):
        raise CalendarEffectError("Calendar provider result must be a JSON object")
    raw = dict(value)
    _validate_result_value(raw)
    try:
        normalized = json.loads(canonical_json(raw))
    except Exception as exc:
        raise CalendarEffectError("Calendar provider result is not canonical JSON") from exc
    upstream_reference = normalized.pop("upstream_reference", None)
    if upstream_reference is not None:
        upstream_reference = _required_text(upstream_reference, "upstream_reference", maximum=2048)
    return normalized, upstream_reference


@dataclass(frozen=True)
class CalendarEffectResult:
    schema: str
    adapter_id: str
    request_id: str
    canonical_request_hash: str
    lease_id: str
    action: str
    resource: str
    data: dict[str, Any]
    upstream_reference: str | None = None

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "adapter_id": self.adapter_id,
            "request_id": self.request_id,
            "canonical_request_hash": self.canonical_request_hash,
            "lease_id": self.lease_id,
            "action": self.action,
            "resource": self.resource,
            "data": self.data,
            "upstream_reference": self.upstream_reference,
        }


@runtime_checkable
class CalendarTransport(Protocol):
    def search(self, *, time_min: str, time_max: str, query: str, max_results: int) -> Mapping[str, Any]: ...
    def read(self, *, event_id: str) -> Mapping[str, Any]: ...
    def create(self, *, event: Mapping[str, Any], request_id: str, idempotency_key: str) -> Mapping[str, Any]: ...
    def modify(self, *, event_id: str, event_etag: str, event: Mapping[str, Any], request_id: str, idempotency_key: str) -> Mapping[str, Any]: ...
    def cancel(self, *, event_id: str, event_etag: str, send_updates: str, request_id: str, idempotency_key: str) -> Mapping[str, Any]: ...
    def reconcile(self, *, action: str, request_id: str, idempotency_key: str, operation: Mapping[str, Any]) -> Mapping[str, Any] | None: ...


@runtime_checkable
class CalendarTransportFactory(Protocol):
    def create(self, *, calendar_resource: str, secret: object) -> CalendarTransport: ...


class CalendarEffectAdapter:
    """Typed Calendar effect boundary reached only after LAC authorization."""

    def __init__(
        self,
        *,
        secret_provider: SecretProvider,
        transport_factory: CalendarTransportFactory,
        resource: str = "calendar:primary",
        credential_ref: str = "google-calendar:primary",
    ) -> None:
        if not isinstance(secret_provider, SecretProvider):
            raise CalendarEffectError("secret_provider must implement SecretProvider")
        if not isinstance(transport_factory, CalendarTransportFactory):
            raise CalendarEffectError("transport_factory must implement CalendarTransportFactory")
        self._resource = _required_text(resource, "resource", maximum=256)
        try:
            self._credential_ref = validate_credential_ref(credential_ref)
        except SecretProviderError as exc:
            raise CalendarEffectError("credential reference failed validation") from exc
        self._secret_provider = secret_provider
        self._transport_factory = transport_factory

    @property
    def adapter_id(self) -> str:
        return CALENDAR_ADAPTER_ID

    @property
    def resource(self) -> str:
        return self._resource

    def supports(self, request: EffectRequest) -> bool:
        try:
            _parse_operation(request, resource=self._resource)
        except CalendarEffectError:
            return False
        return True

    def _transport(self) -> CalendarTransport:
        try:
            secret = self._secret_provider.resolve(self._credential_ref)
        except Exception:
            raise CalendarEffectError("Calendar credential resolution failed closed") from None
        if secret is None:
            raise CalendarEffectError("Calendar credential resolution returned no capability")
        try:
            transport = self._transport_factory.create(calendar_resource=self._resource, secret=secret)
        except Exception:
            raise CalendarEffectError("Calendar transport creation failed closed") from None
        if not isinstance(transport, CalendarTransport):
            raise CalendarEffectError("Calendar transport does not implement the required contract")
        return transport

    def _result(self, request: EffectRequest, lease: ExecutionLease, raw: object, *, mutation: bool) -> CalendarEffectResult:
        data, upstream_reference = _safe_result_record(raw)
        if mutation and upstream_reference is None:
            raise CalendarEffectError("Calendar mutation result lacks stable upstream_reference")
        return CalendarEffectResult(
            schema=CALENDAR_RESULT_SCHEMA,
            adapter_id=CALENDAR_ADAPTER_ID,
            request_id=request.request_id,
            canonical_request_hash=request.canonical_hash,
            lease_id=lease.lease_id,
            action=request.action,
            resource=request.resource,
            data=data,
            upstream_reference=upstream_reference,
        )

    def invoke(self, request: EffectRequest, *, lease: ExecutionLease) -> CalendarEffectResult:
        req = _canonical_request(request)
        lease = _canonical_lease(lease)
        if lease.request_id != req.request_id:
            raise CalendarEffectError("execution lease binds a different request")
        operation = _parse_operation(req, resource=self._resource)
        if operation.action == CALENDAR_DELETE_ACTION:
            raise CalendarEffectError("calendar.delete is prohibited and has no adapter implementation")
        if operation.action == CALENDAR_PROPOSE_ACTION:
            assert operation.event is not None
            return self._result(
                req,
                lease,
                {"proposal": operation.event.to_transport_record(), "synthetic": True},
                mutation=False,
            )
        transport = self._transport()
        try:
            if operation.action == CALENDAR_SEARCH_ACTION:
                return self._result(req, lease, transport.search(
                    time_min=operation.time_min or "",
                    time_max=operation.time_max or "",
                    query=operation.query or "",
                    max_results=operation.max_results or 1,
                ), mutation=False)
            if operation.action == CALENDAR_READ_ACTION:
                return self._result(req, lease, transport.read(event_id=operation.event_id or ""), mutation=False)
            if operation.action == CALENDAR_CREATE_ACTION:
                assert operation.event is not None
                return self._result(req, lease, transport.create(
                    event=operation.event.to_transport_record(), request_id=req.request_id,
                    idempotency_key=req.idempotency_key,
                ), mutation=True)
            if operation.action == CALENDAR_MODIFY_ACTION:
                assert operation.event is not None and operation.event_id and operation.event_etag
                return self._result(req, lease, transport.modify(
                    event_id=operation.event_id, event_etag=operation.event_etag,
                    event=operation.event.to_transport_record(), request_id=req.request_id,
                    idempotency_key=req.idempotency_key,
                ), mutation=True)
            if operation.action == CALENDAR_CANCEL_ACTION:
                assert operation.event_id and operation.event_etag and operation.send_updates
                return self._result(req, lease, transport.cancel(
                    event_id=operation.event_id, event_etag=operation.event_etag,
                    send_updates=operation.send_updates, request_id=req.request_id,
                    idempotency_key=req.idempotency_key,
                ), mutation=True)
        except CalendarEffectError:
            raise
        except Exception as exc:
            raise CalendarEffectError("Calendar provider invocation failed closed") from exc
        raise CalendarEffectError("unknown Calendar action fails closed")

    def reconcile(self, request: EffectRequest, *, lease: ExecutionLease) -> CalendarEffectResult | None:
        req = _canonical_request(request)
        lease = _canonical_lease(lease)
        if lease.request_id != req.request_id:
            raise CalendarEffectError("execution lease binds a different request")
        operation = _parse_operation(req, resource=self._resource)
        if operation.action == CALENDAR_DELETE_ACTION:
            raise CalendarEffectError("calendar.delete is prohibited and cannot reconcile")
        if operation.action in {CALENDAR_SEARCH_ACTION, CALENDAR_READ_ACTION, CALENDAR_PROPOSE_ACTION}:
            return self.invoke(req, lease=lease)
        transport = self._transport()
        material: dict[str, Any] = {"action": operation.action}
        if operation.event_id is not None:
            material["event_id"] = operation.event_id
        if operation.event_etag is not None:
            material["event_etag"] = operation.event_etag
        if operation.event is not None:
            material["event"] = operation.event.to_transport_record()
        if operation.send_updates is not None:
            material["send_updates"] = operation.send_updates
        try:
            raw = transport.reconcile(
                action=operation.action,
                request_id=req.request_id,
                idempotency_key=req.idempotency_key,
                operation=material,
            )
        except Exception as exc:
            raise CalendarEffectError("Calendar reconciliation failed closed") from exc
        if raw is None:
            return None
        return self._result(req, lease, raw, mutation=True)
