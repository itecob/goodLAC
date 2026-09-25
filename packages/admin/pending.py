from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

from packages.state.store import SQLiteStateStore, StateStoreError


PENDING_ADMIN_RESOLUTION_SCHEMA = "lac.pending-permission-resolution/v1"
_PENDING_ADMIN_PREFIX = "pending_permission.admin_resolution.v1."
_ALLOWED_STATUSES = frozenset({"RESOLVED", "DISMISSED"})
_ALLOWED_RESOLUTIONS = frozenset(
    {"POLICY_UPDATED", "CAPABILITY_UPDATED", "POLICY_AND_CAPABILITY_UPDATED", "NO_CHANGE", "DISMISSED"}
)


class PendingAdminError(StateStoreError):
    """Administrator-side pending-permission resolution state is invalid."""


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise PendingAdminError("pending administrator state must be canonical JSON") from exc


def _required_text(value: Any, field: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or value != value.strip() or len(value) > maximum:
        raise PendingAdminError(f"{field} must be a bounded non-empty trimmed string")
    return value


def _normalize_timestamp(value: Any, field: str) -> str:
    value = _required_text(value, field)
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise PendingAdminError(f"{field} must be RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PendingAdminError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _digest(pending_id: str) -> str:
    return hashlib.sha256(pending_id.encode("utf-8")).hexdigest()


def _prefix(pending_id: str) -> str:
    return f"{_PENDING_ADMIN_PREFIX}{_digest(pending_id)}."


def _key(pending_id: str, revision: int) -> str:
    return f"{_prefix(pending_id)}{revision:020d}"


@dataclass(frozen=True)
class PendingAdminResolution:
    schema: str
    pending_id: str
    revision: int
    status: str
    resolution: str
    resolved_by: str
    resolved_at_utc: str

    def to_material(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "pending_id": self.pending_id,
            "revision": self.revision,
            "status": self.status,
            "resolution": self.resolution,
            "resolved_by": self.resolved_by,
            "resolved_at_utc": self.resolved_at_utc,
        }

    @classmethod
    def create(
        cls,
        *,
        pending_id: str,
        revision: int,
        status: str,
        resolution: str,
        resolved_by: str,
        resolved_at_utc: str,
    ) -> "PendingAdminResolution":
        pending_id = _required_text(pending_id, "pending_id")
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise PendingAdminError("pending resolution revision must be positive")
        status = _required_text(status, "status", maximum=32).upper()
        resolution = _required_text(resolution, "resolution", maximum=64).upper()
        if status not in _ALLOWED_STATUSES or resolution not in _ALLOWED_RESOLUTIONS:
            raise PendingAdminError("pending resolution status/resolution is unsupported")
        if status == "DISMISSED" and resolution != "DISMISSED":
            raise PendingAdminError("DISMISSED status requires DISMISSED resolution")
        if status == "RESOLVED" and resolution == "DISMISSED":
            raise PendingAdminError("RESOLVED status cannot use DISMISSED resolution")
        return cls(
            schema=PENDING_ADMIN_RESOLUTION_SCHEMA,
            pending_id=pending_id,
            revision=revision,
            status=status,
            resolution=resolution,
            resolved_by=_required_text(resolved_by, "resolved_by", maximum=128),
            resolved_at_utc=_normalize_timestamp(resolved_at_utc, "resolved_at_utc"),
        )

    @classmethod
    def from_json(cls, raw_json: str) -> "PendingAdminResolution":
        try:
            value = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise PendingAdminError("pending resolution contains invalid JSON") from exc
        if not isinstance(value, dict) or set(value) != {
            "schema", "pending_id", "revision", "status", "resolution", "resolved_by", "resolved_at_utc"
        }:
            raise PendingAdminError("pending resolution fields are invalid")
        if value["schema"] != PENDING_ADMIN_RESOLUTION_SCHEMA:
            raise PendingAdminError("unsupported pending resolution schema")
        record = cls.create(
            pending_id=value["pending_id"],
            revision=value["revision"],
            status=value["status"],
            resolution=value["resolution"],
            resolved_by=value["resolved_by"],
            resolved_at_utc=value["resolved_at_utc"],
        )
        if _canonical_json(record.to_material()) != raw_json:
            raise PendingAdminError("pending resolution JSON is not canonical")
        return record


class PendingAdminRepository:
    """Append-only administration overlay for P002 pending items.

    This repository never mutates the P002 queue or capability-denial closure. It records
    only the owner's administrative disposition of an informational pending item.
    """

    def __init__(self, store: SQLiteStateStore):
        if not isinstance(store, SQLiteStateStore):
            raise PendingAdminError("store must be a SQLiteStateStore")
        self._store = store

    def history(self, pending_id: str) -> list[PendingAdminResolution]:
        pending_id = _required_text(pending_id, "pending_id")
        rows = self._store._conn.execute(
            "SELECT key, value_json FROM system_state WHERE key LIKE ? ORDER BY key",
            (_prefix(pending_id) + "%",),
        ).fetchall()
        result: list[PendingAdminResolution] = []
        for expected_revision, row in enumerate(rows, start=1):
            if str(row["key"]) != _key(pending_id, expected_revision):
                raise PendingAdminError("pending resolution history is not contiguous")
            record = PendingAdminResolution.from_json(str(row["value_json"]))
            if record.pending_id != pending_id or record.revision != expected_revision:
                raise PendingAdminError("pending resolution history identity mismatch")
            result.append(record)
        return result

    def current(self, pending_id: str) -> PendingAdminResolution | None:
        history = self.history(pending_id)
        return history[-1] if history else None

    def record(
        self,
        *,
        pending_id: str,
        status: str,
        resolution: str,
        resolved_by: str,
        resolved_at_utc: str,
        force_new_revision: bool = False,
    ) -> PendingAdminResolution:
        if not isinstance(force_new_revision, bool):
            raise PendingAdminError("force_new_revision must be boolean")
        history = self.history(pending_id)
        normalized = PendingAdminResolution.create(
            pending_id=pending_id,
            revision=len(history) + 1,
            status=status,
            resolution=resolution,
            resolved_by=resolved_by,
            resolved_at_utc=resolved_at_utc,
        )
        if history and not force_new_revision:
            latest = history[-1]
            if (
                latest.status == normalized.status
                and latest.resolution == normalized.resolution
                and latest.resolved_by == normalized.resolved_by
            ):
                return latest
        raw = _canonical_json(normalized.to_material())
        try:
            with self._store.transaction() as conn:
                conn.execute(
                    "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?)",
                    (_key(pending_id, normalized.revision), raw, normalized.resolved_at_utc),
                )
        except Exception as exc:
            if isinstance(exc, StateStoreError):
                raise
            raise PendingAdminError("pending resolution append failed atomically") from exc
        return normalized
