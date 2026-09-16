from __future__ import annotations

from typing import Any

from packages.capabilities import CAPABILITY_MANIFEST_SCHEMA, CapabilityRequestContext

from .adapter import (
    CALENDAR_CANCEL_ACTION,
    CALENDAR_CREATE_ACTION,
    CALENDAR_DELETE_ACTION,
    CALENDAR_MODIFY_ACTION,
    CALENDAR_PROPOSE_ACTION,
    CALENDAR_READ_ACTION,
    CALENDAR_SEARCH_ACTION,
)

CALENDAR_APPLICATION_ID = "lac-calendar-consumer"
CALENDAR_SKILL_ID = "google-calendar"
CALENDAR_RESOURCE_TYPE = "calendar.google"
CALENDAR_DEFAULT_RESOURCE = "calendar:primary"


def _string(maximum: int, *, minimum: int = 0, enum: list[str] | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {"type": "string", "maxLength": maximum}
    if minimum:
        result["minLength"] = minimum
    if enum is not None:
        result["enum"] = enum
    return result


def _event_properties() -> dict[str, Any]:
    return {
        "title": _string(1024),
        "start": _string(64, minimum=1),
        "end": _string(64, minimum=1),
        "timezone": _string(128, minimum=1),
        "attendees": {"type": "array", "items": _string(320, minimum=3), "maxItems": 100},
        "location": _string(2048),
        "recurrence": {"type": "array", "items": _string(2048, minimum=1), "maxItems": 25},
        "conference_settings": {
            "type": "object",
            "properties": {
                "enabled": {"type": "boolean"},
                "solution_type": _string(32, minimum=1, enum=["hangoutsMeet"]),
            },
            "required": ["enabled", "solution_type"],
            "additionalProperties": False,
        },
        "send_updates": _string(16, minimum=3, enum=["all", "externalOnly", "none"]),
    }


def _object(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
    return {
        "type": "object",
        "properties": properties,
        "required": required,
        "additionalProperties": False,
    }


def calendar_capability_manifest(
    *,
    application_id: str = CALENDAR_APPLICATION_ID,
    skill_id: str = CALENDAR_SKILL_ID,
    resource: str = CALENDAR_DEFAULT_RESOURCE,
) -> dict[str, Any]:
    resource_record = {"type": CALENDAR_RESOURCE_TYPE, "selectors": [resource]}
    event_props = _event_properties()
    event_required = list(event_props)
    actions = [
        {
            "action": CALENDAR_SEARCH_ACTION,
            "resource": resource_record,
            "arguments": _object(
                {
                    "time_min": _string(64, minimum=1),
                    "time_max": _string(64, minimum=1),
                    "query": _string(2048),
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 250},
                },
                ["time_min", "time_max", "query", "max_results"],
            ),
            "security_properties": ["credential_sensitive", "network_egress", "read_only"],
        },
        {
            "action": CALENDAR_READ_ACTION,
            "resource": resource_record,
            "arguments": _object({"event_id": _string(1024, minimum=1)}, ["event_id"]),
            "security_properties": ["credential_sensitive", "network_egress", "read_only"],
        },
        {
            "action": CALENDAR_PROPOSE_ACTION,
            "resource": resource_record,
            "arguments": _object(event_props, event_required),
            "security_properties": ["read_only"],
        },
        {
            "action": CALENDAR_CREATE_ACTION,
            "resource": resource_record,
            "arguments": _object(event_props, event_required),
            "security_properties": ["credential_sensitive", "external_communication", "external_mutation", "network_egress"],
        },
        {
            "action": CALENDAR_MODIFY_ACTION,
            "resource": resource_record,
            "arguments": _object(
                {"event_id": _string(1024, minimum=1), "event_etag": _string(1024, minimum=3), **event_props},
                ["event_id", "event_etag", *event_required],
            ),
            "security_properties": ["credential_sensitive", "external_communication", "external_mutation", "network_egress"],
        },
        {
            "action": CALENDAR_CANCEL_ACTION,
            "resource": resource_record,
            "arguments": _object(
                {
                    "event_id": _string(1024, minimum=1),
                    "event_etag": _string(1024, minimum=3),
                    "send_updates": _string(16, minimum=3, enum=["all", "externalOnly", "none"]),
                },
                ["event_id", "event_etag", "send_updates"],
            ),
            "security_properties": ["credential_sensitive", "destructive", "external_communication", "external_mutation", "network_egress"],
        },
        {
            "action": CALENDAR_DELETE_ACTION,
            "resource": resource_record,
            "arguments": _object(
                {"event_id": _string(1024, minimum=1), "event_etag": _string(1024, minimum=3)},
                ["event_id", "event_etag"],
            ),
            "security_properties": ["credential_sensitive", "destructive", "external_mutation", "network_egress"],
        },
    ]
    return {
        "schema": CAPABILITY_MANIFEST_SCHEMA,
        "manifest_version": 1,
        "application_id": application_id,
        "skill_id": skill_id,
        "actions": actions,
    }


def calendar_capability_context(*, revision: int, application_id: str = CALENDAR_APPLICATION_ID, skill_id: str = CALENDAR_SKILL_ID) -> CapabilityRequestContext:
    return CapabilityRequestContext(
        application_id=application_id,
        skill_id=skill_id,
        capability_revision=revision,
        manifest_version=1,
        resource_type=CALENDAR_RESOURCE_TYPE,
    )
