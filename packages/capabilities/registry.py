from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from packages.state.store import SQLiteStateStore, StateStoreError

from .manifest import CapabilityManifest, CapabilityManifestError


CAPABILITY_REGISTRY_RECORD_SCHEMA = "lac.capability-registry-record/v1"
CAPABILITY_REGISTRY_POINTER_SCHEMA = "lac.capability-registry-pointer/v1"
CAPABILITY_REGISTRY_AUDIT_SCHEMA = "lac.capability-registry-audit/v1"

_LATEST_PREFIX = "capability_registry.latest."
_REVISION_PREFIX = "capability_registry.revision."
_AUDIT_PREFIX = "capability_registry.audit."


class CapabilityRegistryError(StateStoreError):
    """Base failure for durable capability registry operations."""


class CapabilityRegistryIntegrityError(CapabilityRegistryError):
    """Durable registry material is missing, non-canonical, or internally inconsistent."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CapabilityRegistryError("registry material must be canonical JSON") from exc


def _identity_digest(application_id: str, skill_id: str) -> str:
    return hashlib.sha256(f"{application_id}\0{skill_id}".encode("utf-8")).hexdigest()


def _latest_key(digest: str) -> str:
    return f"{_LATEST_PREFIX}{digest}"


def _revision_key(digest: str, revision: int) -> str:
    return f"{_REVISION_PREFIX}{digest}.{revision:020d}"


def _audit_key(digest: str, revision: int) -> str:
    return f"{_AUDIT_PREFIX}{digest}.{revision:020d}"


def _strict_record(raw_json: str, *, required: set[str], context: str) -> dict[str, Any]:
    try:
        parsed = json.loads(raw_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CapabilityRegistryIntegrityError(f"{context} contains invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise CapabilityRegistryIntegrityError(f"{context} must contain a JSON object")
    if set(parsed) != required:
        raise CapabilityRegistryIntegrityError(
            f"{context} fields invalid; observed={sorted(parsed)} expected={sorted(required)}"
        )
    if _json(parsed) != raw_json:
        raise CapabilityRegistryIntegrityError(f"{context} JSON is not canonical")
    return parsed


@dataclass(frozen=True)
class CapabilityRegistration:
    application_id: str
    skill_id: str
    revision: int
    manifest_hash: str
    security_hash: str
    manifest_json: str
    registered_at_utc: str

    @property
    def manifest(self) -> CapabilityManifest:
        try:
            manifest = CapabilityManifest.from_json(self.manifest_json, require_canonical=True)
        except CapabilityManifestError as exc:
            raise CapabilityRegistryIntegrityError(
                f"capability revision {self.application_id}/{self.skill_id}@{self.revision} "
                "contains an invalid persisted manifest"
            ) from exc
        if manifest.application_id != self.application_id or manifest.skill_id != self.skill_id:
            raise CapabilityRegistryIntegrityError("persisted manifest identity does not match registry record")
        if manifest.canonical_hash != self.manifest_hash:
            raise CapabilityRegistryIntegrityError("persisted manifest hash does not match registry record")
        if manifest.security_hash != self.security_hash:
            raise CapabilityRegistryIntegrityError("persisted security hash does not match registry record")
        return manifest

    def to_record(self) -> dict[str, Any]:
        return {
            "schema": CAPABILITY_REGISTRY_RECORD_SCHEMA,
            "application_id": self.application_id,
            "skill_id": self.skill_id,
            "revision": self.revision,
            "manifest_hash": self.manifest_hash,
            "security_hash": self.security_hash,
            "manifest_json": self.manifest_json,
            "registered_at_utc": self.registered_at_utc,
        }

    @classmethod
    def from_record(cls, raw_json: str) -> "CapabilityRegistration":
        record = _strict_record(
            raw_json,
            required={
                "schema",
                "application_id",
                "skill_id",
                "revision",
                "manifest_hash",
                "security_hash",
                "manifest_json",
                "registered_at_utc",
            },
            context="capability registry revision",
        )
        if record["schema"] != CAPABILITY_REGISTRY_RECORD_SCHEMA:
            raise CapabilityRegistryIntegrityError("unsupported capability registry record schema")
        revision = record["revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise CapabilityRegistryIntegrityError("capability registry revision must be a positive integer")
        registration = cls(
            application_id=record["application_id"],
            skill_id=record["skill_id"],
            revision=revision,
            manifest_hash=record["manifest_hash"],
            security_hash=record["security_hash"],
            manifest_json=record["manifest_json"],
            registered_at_utc=record["registered_at_utc"],
        )
        # Forces canonical manifest/hash/identity validation before the record can be trusted.
        registration.manifest
        return registration


class CapabilityRegistry:
    """Durable append-only capability registry.

    P001 intentionally exposes this class only as an internal controller component. The
    mutation method is named ``register_admin`` to make the intended boundary explicit;
    no runtime/agent adapter imports or exposes it. P004 will add the authenticated
    administrator transport around this internal mutation operation.
    """

    def __init__(self, store: SQLiteStateStore):
        self._store = store

    @staticmethod
    def _read_state_json(store: SQLiteStateStore, key: str) -> str | None:
        row = store._conn.execute(
            "SELECT value_json FROM system_state WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else str(row["value_json"])

    @staticmethod
    def _pointer_from_json(raw_json: str) -> dict[str, Any]:
        record = _strict_record(
            raw_json,
            required={"schema", "application_id", "skill_id", "revision", "manifest_hash"},
            context="capability registry latest pointer",
        )
        if record["schema"] != CAPABILITY_REGISTRY_POINTER_SCHEMA:
            raise CapabilityRegistryIntegrityError("unsupported capability registry pointer schema")
        revision = record["revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise CapabilityRegistryIntegrityError("capability registry pointer revision is invalid")
        return record

    def _revision_rows(self, digest: str) -> list[tuple[str, str]]:
        prefix = f"{_REVISION_PREFIX}{digest}."
        rows = self._store._conn.execute(
            "SELECT key, value_json FROM system_state WHERE key LIKE ? ORDER BY key",
            (prefix + "%",),
        ).fetchall()
        return [(str(row["key"]), str(row["value_json"])) for row in rows]

    def _audit_rows(self, digest: str) -> list[tuple[str, str]]:
        prefix = f"{_AUDIT_PREFIX}{digest}."
        rows = self._store._conn.execute(
            "SELECT key, value_json FROM system_state WHERE key LIKE ? ORDER BY key",
            (prefix + "%",),
        ).fetchall()
        return [(str(row["key"]), str(row["value_json"])) for row in rows]

    def history(self, application_id: str, skill_id: str) -> list[CapabilityRegistration]:
        digest = _identity_digest(application_id, skill_id)
        pointer_raw = self._read_state_json(self._store, _latest_key(digest))
        rows = self._revision_rows(digest)
        if pointer_raw is None:
            if rows or self._audit_rows(digest):
                raise CapabilityRegistryIntegrityError(
                    "orphaned capability registry rows exist without a latest pointer"
                )
            return []
        pointer = self._pointer_from_json(pointer_raw)
        if pointer["application_id"] != application_id or pointer["skill_id"] != skill_id:
            raise CapabilityRegistryIntegrityError("capability registry identity digest collision/inconsistency")

        registrations: list[CapabilityRegistration] = []
        for expected_revision, (key, raw_json) in enumerate(rows, start=1):
            expected_key = _revision_key(digest, expected_revision)
            if key != expected_key:
                raise CapabilityRegistryIntegrityError(
                    "capability registry revision history is not contiguous"
                )
            registration = CapabilityRegistration.from_record(raw_json)
            if (
                registration.application_id != application_id
                or registration.skill_id != skill_id
                or registration.revision != expected_revision
            ):
                raise CapabilityRegistryIntegrityError(
                    "capability registry revision identity/revision mismatch"
                )
            registrations.append(registration)

        if not registrations:
            raise CapabilityRegistryIntegrityError("latest pointer exists without revision rows")
        latest = registrations[-1]
        if pointer["revision"] != latest.revision or pointer["manifest_hash"] != latest.manifest_hash:
            raise CapabilityRegistryIntegrityError("latest pointer does not match latest capability revision")

        audits = self.audit_events(application_id, skill_id)
        if len(audits) != len(registrations):
            raise CapabilityRegistryIntegrityError(
                "capability registry audit history does not match revision history"
            )
        previous_security_hash: str | None = None
        for registration, event in zip(registrations, audits):
            expected_security_changed = previous_security_hash != registration.security_hash
            if (
                event["manifest_hash"] != registration.manifest_hash
                or event["security_hash"] != registration.security_hash
                or event["action_count"] != len(registration.manifest.actions)
                or event["security_changed"] is not expected_security_changed
            ):
                raise CapabilityRegistryIntegrityError(
                    "capability registry audit event does not match immutable revision"
                )
            previous_security_hash = registration.security_hash
        return registrations

    def get_latest(self, application_id: str, skill_id: str) -> CapabilityRegistration | None:
        history = self.history(application_id, skill_id)
        return history[-1] if history else None

    def get_revision(
        self, application_id: str, skill_id: str, revision: int
    ) -> CapabilityRegistration | None:
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise CapabilityRegistryError("revision must be a positive integer")
        history = self.history(application_id, skill_id)
        if revision > len(history):
            return None
        return history[revision - 1]

    def audit_events(self, application_id: str, skill_id: str) -> list[dict[str, Any]]:
        digest = _identity_digest(application_id, skill_id)
        rows = self._audit_rows(digest)
        result: list[dict[str, Any]] = []
        required = {
            "schema",
            "event_id",
            "event_type",
            "application_id",
            "skill_id",
            "revision",
            "manifest_hash",
            "security_hash",
            "security_changed",
            "action_count",
            "occurred_at_utc",
        }
        for expected_revision, (key, raw_json) in enumerate(rows, start=1):
            if key != _audit_key(digest, expected_revision):
                raise CapabilityRegistryIntegrityError("capability registry audit history is not contiguous")
            event = _strict_record(
                raw_json,
                required=required,
                context="capability registry audit event",
            )
            if event["schema"] != CAPABILITY_REGISTRY_AUDIT_SCHEMA:
                raise CapabilityRegistryIntegrityError("unsupported capability registry audit schema")
            if event["event_type"] != "REGISTER":
                raise CapabilityRegistryIntegrityError("unsupported capability registry audit event type")
            if (
                event["application_id"] != application_id
                or event["skill_id"] != skill_id
                or event["revision"] != expected_revision
            ):
                raise CapabilityRegistryIntegrityError("capability registry audit identity mismatch")
            result.append(event)
        return result

    def list_latest(self) -> list[CapabilityRegistration]:
        rows = self._store._conn.execute(
            "SELECT value_json FROM system_state WHERE key LIKE ? ORDER BY key",
            (_LATEST_PREFIX + "%",),
        ).fetchall()
        result: list[CapabilityRegistration] = []
        seen: set[tuple[str, str]] = set()
        for row in rows:
            pointer = self._pointer_from_json(str(row["value_json"]))
            identity = (pointer["application_id"], pointer["skill_id"])
            if identity in seen:
                raise CapabilityRegistryIntegrityError("duplicate capability registry identity pointer")
            seen.add(identity)
            latest = self.get_latest(*identity)
            if latest is None:
                raise CapabilityRegistryIntegrityError("registry pointer resolved to no registration")
            result.append(latest)
        return sorted(result, key=lambda item: (item.application_id, item.skill_id))

    def register_admin(self, manifest: CapabilityManifest) -> CapabilityRegistration:
        if not isinstance(manifest, CapabilityManifest):
            raise CapabilityRegistryError("register_admin requires a validated CapabilityManifest")

        # Validate the complete existing chain before appending to it. Corruption is never
        # repaired implicitly because doing so could silently change authority metadata.
        history = self.history(manifest.application_id, manifest.skill_id)
        if history and history[-1].manifest_hash == manifest.canonical_hash:
            return history[-1]

        revision = len(history) + 1
        digest = _identity_digest(manifest.application_id, manifest.skill_id)
        timestamp = _utc_now()
        registration = CapabilityRegistration(
            application_id=manifest.application_id,
            skill_id=manifest.skill_id,
            revision=revision,
            manifest_hash=manifest.canonical_hash,
            security_hash=manifest.security_hash,
            manifest_json=manifest.canonical_json(),
            registered_at_utc=timestamp,
        )
        # Force the exact object intended for persistence through the integrity validator.
        CapabilityRegistration.from_record(_json(registration.to_record()))

        previous_security_hash = history[-1].security_hash if history else None
        event = {
            "schema": CAPABILITY_REGISTRY_AUDIT_SCHEMA,
            "event_id": f"capreg:{digest}:{revision:020d}",
            "event_type": "REGISTER",
            "application_id": manifest.application_id,
            "skill_id": manifest.skill_id,
            "revision": revision,
            "manifest_hash": manifest.canonical_hash,
            "security_hash": manifest.security_hash,
            "security_changed": previous_security_hash != manifest.security_hash,
            "action_count": len(manifest.actions),
            "occurred_at_utc": timestamp,
        }
        pointer = {
            "schema": CAPABILITY_REGISTRY_POINTER_SCHEMA,
            "application_id": manifest.application_id,
            "skill_id": manifest.skill_id,
            "revision": revision,
            "manifest_hash": manifest.canonical_hash,
        }

        try:
            with self._store.transaction() as conn:
                conn.execute(
                    "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?)",
                    (_revision_key(digest, revision), _json(registration.to_record()), timestamp),
                )
                conn.execute(
                    "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?)",
                    (_audit_key(digest, revision), _json(event), timestamp),
                )
                conn.execute(
                    """
                    INSERT INTO system_state(key, value_json, updated_at_utc)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at_utc = excluded.updated_at_utc
                    """,
                    (_latest_key(digest), _json(pointer), timestamp),
                )
        except Exception as exc:
            # Preserve StateStoreError subclasses and convert raw SQLite failures to a
            # registry-domain error. The transaction context rolls back all three writes.
            if isinstance(exc, StateStoreError):
                raise
            raise CapabilityRegistryError("capability registry mutation failed atomically") from exc

        return registration
