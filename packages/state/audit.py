from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from packages.core import canonical_json
from .effect_requests import EffectRequestRepository
from .store import SQLiteStateStore, StateStoreError


AUDIT_EVENT_SCHEMA = "lac.audit-event/v1"


class AuditStateError(StateStoreError):
    """Persisted audit state is malformed. Audit state never authorizes effects."""


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise AuditStateError(f"{field} must be a non-empty trimmed string")
    return value


def _normalize_timestamp(value: Any, field: str) -> str:
    value = _required_text(value, field)
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise AuditStateError(f"{field} must be RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise AuditStateError(f"{field} must include timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    schema: str
    event_id: str
    request_id: str
    event_type: str
    occurred_at: str
    details_json: str

    @classmethod
    def from_row(cls, row: sqlite3.Row) -> "AuditEvent":
        sequence = row["sequence"]
        if not isinstance(sequence, int) or sequence <= 0:
            raise AuditStateError("audit sequence is invalid")
        if row["schema"] != AUDIT_EVENT_SCHEMA:
            raise AuditStateError("unsupported audit event schema")
        details_json = row["details_json"]
        try:
            parsed = json.loads(details_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise AuditStateError("audit details_json is invalid") from exc
        if canonical_json(parsed) != details_json:
            raise AuditStateError("audit details_json is not canonical")
        return cls(
            sequence=sequence,
            schema=AUDIT_EVENT_SCHEMA,
            event_id=_required_text(row["event_id"], "event_id"),
            request_id=_required_text(row["request_id"], "request_id"),
            event_type=_required_text(row["event_type"], "event_type"),
            occurred_at=_normalize_timestamp(row["occurred_at"], "occurred_at"),
            details_json=details_json,
        )

    @property
    def details(self) -> Any:
        return json.loads(self.details_json)


class AuditRepository:
    """Append-only material lifecycle evidence. This repository has no authority API."""

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    def _append_in_transaction(
        self,
        conn: sqlite3.Connection,
        *,
        request_id: str,
        event_type: str,
        occurred_at: str,
        details: Any,
    ) -> AuditEvent:
        if conn is not self._store._conn or not conn.in_transaction:
            raise AuditStateError("audit append requires the active StateStore transaction")
        request_id = _required_text(request_id, "request_id")
        if EffectRequestRepository(self._store).get(request_id) is None:
            raise AuditStateError("audit event requires a durable canonical request")
        event_type = _required_text(event_type, "event_type")
        occurred_at = _normalize_timestamp(occurred_at, "occurred_at")
        details_json = canonical_json(details)
        ordinal = int(
            conn.execute(
                "SELECT COUNT(*) FROM audit_events WHERE request_id = ? AND event_type = ?",
                (request_id, event_type),
            ).fetchone()[0]
        ) + 1
        identity_material = canonical_json(
            {
                "request_id": request_id,
                "event_type": event_type,
                "occurred_at": occurred_at,
                "details": json.loads(details_json),
                "ordinal": ordinal,
            }
        )
        digest = hashlib.sha256(identity_material.encode("utf-8")).hexdigest()
        event_id = f"audit:{digest}"
        try:
            cursor = conn.execute(
                """
                INSERT INTO audit_events(
                    schema, event_id, request_id, event_type, occurred_at, details_json
                ) VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    AUDIT_EVENT_SCHEMA,
                    event_id,
                    request_id,
                    event_type,
                    occurred_at,
                    details_json,
                ),
            )
        except sqlite3.IntegrityError as exc:
            raise AuditStateError("audit event append failed integrity constraints") from exc
        row = conn.execute(
            """
            SELECT sequence, schema, event_id, request_id, event_type,
                   occurred_at, details_json
            FROM audit_events WHERE sequence = ?
            """,
            (cursor.lastrowid,),
        ).fetchone()
        if row is None:
            raise AuditStateError("appended audit event could not be reloaded")
        return AuditEvent.from_row(row)

    def list_for_request(self, request_id: str) -> tuple[AuditEvent, ...]:
        request_id = _required_text(request_id, "request_id")
        rows = self._store._conn.execute(
            """
            SELECT sequence, schema, event_id, request_id, event_type,
                   occurred_at, details_json
            FROM audit_events WHERE request_id = ? ORDER BY sequence
            """,
            (request_id,),
        ).fetchall()
        return tuple(AuditEvent.from_row(row) for row in rows)
