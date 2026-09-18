from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from packages.core import canonical_json
from packages.state import SQLiteStateStore, StateStoreError

PI_V1_CONTINUATION_SCHEMA = "lac.pi-v1-workflow-continuation/v1"
PI_V1_CONTINUATION_QUEUE_SCHEMA = "lac.pi-v1-workflow-continuation-queue/v1"
PI_V1_CONTINUATION_STATUS_SCHEMA = "lac.pi-v1-workflow-continuation-status/v1"
PI_V1_CONTINUATION_RESUME_SCHEMA = "lac.pi-v1-workflow-continuation-resume/v1"
PI_V1_WORKFLOW_OUTCOME_SCHEMA = "lac.pi-v1-workflow-outcome/v1"

PI_V1_CONTINUATION_TTL_SECONDS = 3600
PI_V1_CONTINUATION_MAX_RECORDS = 16
PI_V1_CONTINUATION_MAX_QUEUE_BYTES = 4 * 1024 * 1024

_QUEUE_KEY = "pi_v1.workflow_continuations.v1"
_PENDING_ADMIN_PREFIX = "pending_permission.admin_resolution.v1."

_ALLOWED_STATES = frozenset(
    {
        "WAITING_PERMISSION",
        "FRESH_REQUEST_CLAIMED",
        "PENDING_APPROVAL",
        "COMPLETED",
        "CLOSED_NONAUTH",
        "EXPIRED",
    }
)
_TERMINAL_STATES = frozenset({"COMPLETED", "CLOSED_NONAUTH", "EXPIRED"})
_AUTHORIZING_RESOLUTIONS = frozenset(
    {"POLICY_UPDATED", "CAPABILITY_UPDATED", "POLICY_AND_CAPABILITY_UPDATED"}
)
_NONAUTHORIZING_RESOLUTIONS = frozenset({"NO_CHANGE", "DISMISSED"})


class PiWorkflowContinuationError(StateStoreError):
    """Base fail-closed workflow-continuation error."""


class PiWorkflowContinuationIntegrityError(PiWorkflowContinuationError):
    """Durable continuation state is malformed or inconsistent."""


def _canonical(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise PiWorkflowContinuationIntegrityError(
            "workflow-continuation state must be canonical JSON"
        ) from exc


def _required_text(value: Any, field: str, *, maximum: int = 1024) -> str:
    if (
        not isinstance(value, str)
        or not value
        or value != value.strip()
        or len(value) > maximum
    ):
        raise PiWorkflowContinuationIntegrityError(
            f"{field} must be bounded non-empty trimmed text"
        )
    return value


def _utc(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PiWorkflowContinuationIntegrityError("continuation clock must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace(
        "+00:00", "Z"
    )


def _parse_utc(value: Any, field: str) -> datetime:
    raw = _required_text(value, field)
    candidate = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError as exc:
        raise PiWorkflowContinuationIntegrityError(f"{field} must be RFC3339") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PiWorkflowContinuationIntegrityError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc)


def _intent_hash(*, run_id: str, action: str, resource: str, arguments: Mapping[str, Any]) -> str:
    try:
        material = canonical_json(
            {
                "run_id": run_id,
                "action": action,
                "resource": resource,
                "arguments": dict(arguments),
            }
        )
    except Exception as exc:
        raise PiWorkflowContinuationIntegrityError(
            "continuation intent is outside canonical JSON"
        ) from exc
    return "sha256:" + hashlib.sha256(material.encode("utf-8")).hexdigest()


def _continuation_id(
    *, original_request_id: str, canonical_request_hash: str, pending_id: str, intent_hash: str
) -> str:
    material = "\0".join(
        (original_request_id, canonical_request_hash, pending_id, intent_hash)
    ).encode("utf-8")
    return "continuation:pi-v1:" + hashlib.sha256(material).hexdigest()


def _fresh_identity(continuation_id: str) -> tuple[str, str]:
    digest = hashlib.sha256(
        canonical_json({"continuation_id": continuation_id, "attempt": 1}).encode("utf-8")
    ).hexdigest()
    return (
        f"effect:pi-v1-cont:{digest[:40]}",
        f"idem:pi-v1-cont:{digest}",
    )


def _resolution_prefix(pending_id: str) -> str:
    digest = hashlib.sha256(pending_id.encode("utf-8")).hexdigest()
    return f"{_PENDING_ADMIN_PREFIX}{digest}."


@dataclass(frozen=True)
class ContinuationPreparation:
    state: str
    status: dict[str, Any]
    fresh_material: dict[str, Any] | None = None


class PiWorkflowContinuationStore:
    """Bounded, non-authoritative Pi workflow continuation state.

    This store never grants authority. It only captures immutable intent from a request that
    has already been terminally denied, observes the owner's append-only pending-permission
    disposition, and allocates at most one fresh request identity. All fresh requests still go
    through the ordinary authoritative ExternalConsumerRuntime.
    """

    def __init__(
        self,
        store: SQLiteStateStore,
        *,
        clock: Callable[[], datetime] | None = None,
        ttl_seconds: int = PI_V1_CONTINUATION_TTL_SECONDS,
    ) -> None:
        if not isinstance(store, SQLiteStateStore):
            raise PiWorkflowContinuationError("store must be SQLiteStateStore")
        if isinstance(ttl_seconds, bool) or not isinstance(ttl_seconds, int):
            raise PiWorkflowContinuationError("ttl_seconds must be an integer")
        if ttl_seconds < 30 or ttl_seconds > 86400:
            raise PiWorkflowContinuationError("ttl_seconds must be between 30 and 86400")
        self._store = store
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._ttl_seconds = ttl_seconds

    def _empty_queue(self) -> dict[str, Any]:
        return {
            "schema": PI_V1_CONTINUATION_QUEUE_SCHEMA,
            "max_records": PI_V1_CONTINUATION_MAX_RECORDS,
            "records": [],
        }

    def _validate_record(self, value: Any) -> dict[str, Any]:
        required = {
            "schema",
            "continuation_id",
            "original_request_id",
            "original_canonical_request_hash",
            "original_idempotency_key",
            "pending_id",
            "run_id",
            "action",
            "resource",
            "arguments",
            "intent_hash",
            "created_at_utc",
            "expires_at_utc",
            "state",
            "resume_budget_used",
            "fresh_request_id",
            "fresh_idempotency_key",
            "fresh_decision_id",
            "resolution_baseline_revision",
            "resolution_revision",
            "resolution_status",
            "resolution",
            "completed_at_utc",
            "outcome",
        }
        if not isinstance(value, dict) or set(value) != required:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation record fields are invalid"
            )
        if value.get("schema") != PI_V1_CONTINUATION_SCHEMA:
            raise PiWorkflowContinuationIntegrityError(
                "unsupported workflow-continuation schema"
            )
        for field in (
            "continuation_id",
            "original_request_id",
            "original_canonical_request_hash",
            "original_idempotency_key",
            "pending_id",
            "run_id",
            "action",
            "resource",
            "intent_hash",
        ):
            _required_text(value.get(field), field, maximum=4096)
        if not isinstance(value.get("arguments"), dict):
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation arguments must be an object"
            )
        _parse_utc(value.get("created_at_utc"), "created_at_utc")
        _parse_utc(value.get("expires_at_utc"), "expires_at_utc")
        state = _required_text(value.get("state"), "state", maximum=64)
        if state not in _ALLOWED_STATES:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation state is unsupported"
            )
        budget = value.get("resume_budget_used")
        if isinstance(budget, bool) or not isinstance(budget, int) or budget not in (0, 1):
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation resume budget is invalid"
            )
        optional_text_fields = (
            "fresh_request_id",
            "fresh_idempotency_key",
            "fresh_decision_id",
            "resolution_status",
            "resolution",
            "completed_at_utc",
            "outcome",
        )
        for field in optional_text_fields:
            item = value.get(field)
            if item is not None:
                _required_text(item, field, maximum=4096)
        baseline_revision = value.get("resolution_baseline_revision")
        if (
            isinstance(baseline_revision, bool)
            or not isinstance(baseline_revision, int)
            or baseline_revision < 0
        ):
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation resolution baseline revision is invalid"
            )
        revision = value.get("resolution_revision")
        if revision is not None and (
            isinstance(revision, bool) or not isinstance(revision, int) or revision < 1
        ):
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation resolution revision is invalid"
            )
        if revision is not None and revision <= baseline_revision:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation resolution must be newer than capture baseline"
            )
        observed_hash = _intent_hash(
            run_id=value["run_id"],
            action=value["action"],
            resource=value["resource"],
            arguments=value["arguments"],
        )
        if observed_hash != value["intent_hash"]:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation immutable intent hash mismatch"
            )
        expected_id = _continuation_id(
            original_request_id=value["original_request_id"],
            canonical_request_hash=value["original_canonical_request_hash"],
            pending_id=value["pending_id"],
            intent_hash=value["intent_hash"],
        )
        if expected_id != value["continuation_id"]:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation identity mismatch"
            )
        if budget == 0 and (
            value["fresh_request_id"] is not None
            or value["fresh_idempotency_key"] is not None
            or value["fresh_decision_id"] is not None
        ):
            raise PiWorkflowContinuationIntegrityError(
                "unused continuation budget cannot have fresh request state"
            )
        if budget == 1:
            if value["fresh_request_id"] is None or value["fresh_idempotency_key"] is None:
                raise PiWorkflowContinuationIntegrityError(
                    "used continuation budget must bind one fresh request identity"
                )
            expected_request, expected_idem = _fresh_identity(value["continuation_id"])
            if (
                value["fresh_request_id"] != expected_request
                or value["fresh_idempotency_key"] != expected_idem
            ):
                raise PiWorkflowContinuationIntegrityError(
                    "fresh continuation request identity mismatch"
                )
        if value["state"] in {"FRESH_REQUEST_CLAIMED", "PENDING_APPROVAL", "COMPLETED"} and budget != 1:
            raise PiWorkflowContinuationIntegrityError(
                "fresh-request continuation state requires consumed one-shot budget"
            )
        if value["state"] in {"CLOSED_NONAUTH", "EXPIRED"} and budget != 0:
            raise PiWorkflowContinuationIntegrityError(
                "non-authorizing closure cannot consume a fresh-request budget"
            )
        if value["state"] == "WAITING_PERMISSION":
            if any(
                value[field] is not None
                for field in (
                    "resolution_revision", "resolution_status", "resolution",
                    "completed_at_utc", "outcome",
                )
            ):
                raise PiWorkflowContinuationIntegrityError(
                    "waiting continuation cannot contain resolution or terminal state"
                )
        if value["state"] in {"FRESH_REQUEST_CLAIMED", "PENDING_APPROVAL", "COMPLETED"}:
            if (
                value["resolution_revision"] is None
                or value["resolution_status"] != "RESOLVED"
                or value["resolution"] not in _AUTHORIZING_RESOLUTIONS
            ):
                raise PiWorkflowContinuationIntegrityError(
                    "fresh-request continuation lacks authorizing administrative disposition"
                )
        if value["state"] == "PENDING_APPROVAL" and value["fresh_decision_id"] is None:
            raise PiWorkflowContinuationIntegrityError(
                "approval-pending continuation lacks exact decision identity"
            )
        if value["state"] == "CLOSED_NONAUTH":
            if (
                value["resolution_revision"] is None
                or value["resolution_status"] not in {"RESOLVED", "DISMISSED"}
                or value["resolution"] not in _NONAUTHORIZING_RESOLUTIONS
                or value["completed_at_utc"] is None
                or value["outcome"] is None
            ):
                raise PiWorkflowContinuationIntegrityError(
                    "non-authorizing continuation closure is incomplete"
                )
        if value["state"] == "EXPIRED" and (
            value["completed_at_utc"] is None or value["outcome"] is None
        ):
            raise PiWorkflowContinuationIntegrityError(
                "expired continuation closure is incomplete"
            )
        if value["state"] == "COMPLETED" and (
            value["completed_at_utc"] is None or value["outcome"] is None
        ):
            raise PiWorkflowContinuationIntegrityError(
                "completed continuation closure is incomplete"
            )
        if value["completed_at_utc"] is not None:
            _parse_utc(value["completed_at_utc"], "completed_at_utc")
        return json.loads(_canonical(value))

    def _validate_queue(self, value: Any) -> dict[str, Any]:
        if value is None:
            return self._empty_queue()
        if (
            not isinstance(value, dict)
            or set(value) != {"schema", "max_records", "records"}
            or value.get("schema") != PI_V1_CONTINUATION_QUEUE_SCHEMA
            or value.get("max_records") != PI_V1_CONTINUATION_MAX_RECORDS
            or not isinstance(value.get("records"), list)
            or len(value["records"]) > PI_V1_CONTINUATION_MAX_RECORDS
        ):
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation queue durable state is invalid"
            )
        records = [self._validate_record(item) for item in value["records"]]
        ids = [item["continuation_id"] for item in records]
        originals = [item["original_request_id"] for item in records]
        if len(ids) != len(set(ids)) or len(originals) != len(set(originals)):
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation queue contains duplicate identity"
            )
        queue = {
            "schema": PI_V1_CONTINUATION_QUEUE_SCHEMA,
            "max_records": PI_V1_CONTINUATION_MAX_RECORDS,
            "records": records,
        }
        if len(_canonical(queue).encode("utf-8")) > PI_V1_CONTINUATION_MAX_QUEUE_BYTES:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation queue exceeds bounded storage limit"
            )
        return queue

    def _queue(self) -> dict[str, Any]:
        row = self._store._conn.execute(
            "SELECT value_json FROM system_state WHERE key = ?", (_QUEUE_KEY,)
        ).fetchone()
        if row is None:
            return self._empty_queue()
        raw = str(row["value_json"])
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation queue contains invalid JSON"
            ) from exc
        if _canonical(value) != raw:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation queue JSON is not canonical"
            )
        return self._validate_queue(value)

    def _write_queue_in_transaction(self, conn, queue: Mapping[str, Any]) -> None:
        normalized = self._validate_queue(dict(queue))
        encoded = _canonical(normalized)
        if len(encoded.encode("utf-8")) > PI_V1_CONTINUATION_MAX_QUEUE_BYTES:
            raise PiWorkflowContinuationError(
                "workflow-continuation queue exceeds bounded storage limit"
            )
        conn.execute(
            "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value_json = excluded.value_json, "
            "updated_at_utc = excluded.updated_at_utc",
            (_QUEUE_KEY, encoded, self._store._utc_now()),
        )

    def _load_queue_in_transaction(self, conn) -> dict[str, Any]:
        row = conn.execute(
            "SELECT value_json FROM system_state WHERE key = ?", (_QUEUE_KEY,)
        ).fetchone()
        if row is None:
            return self._empty_queue()
        raw = str(row["value_json"])
        try:
            value = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation queue contains invalid JSON"
            ) from exc
        if _canonical(value) != raw:
            raise PiWorkflowContinuationIntegrityError(
                "workflow-continuation queue JSON is not canonical"
            )
        return self._validate_queue(value)

    @staticmethod
    def _find_index(queue: Mapping[str, Any], continuation_id: str) -> int | None:
        for index, record in enumerate(queue["records"]):
            if record.get("continuation_id") == continuation_id:
                return index
        return None

    def _record_by_id(self, continuation_id: str) -> dict[str, Any]:
        continuation_id = _required_text(continuation_id, "continuation_id")
        queue = self._queue()
        index = self._find_index(queue, continuation_id)
        if index is None:
            raise PiWorkflowContinuationError("workflow continuation was not found")
        return dict(queue["records"][index])

    def _owner_resolution_history(self, pending_id: str) -> list[dict[str, Any]]:
        pending_id = _required_text(pending_id, "pending_id")
        prefix = _resolution_prefix(pending_id)
        rows = self._store._conn.execute(
            "SELECT key, value_json FROM system_state "
            "WHERE substr(key, 1, ?) = ? ORDER BY key",
            (len(prefix), prefix),
        ).fetchall()
        history: list[dict[str, Any]] = []
        for expected_revision, row in enumerate(rows, start=1):
            if str(row["key"]) != f"{prefix}{expected_revision:020d}":
                raise PiWorkflowContinuationIntegrityError(
                    "pending-permission resolution history is not contiguous"
                )
            raw = str(row["value_json"])
            try:
                value = json.loads(raw)
            except json.JSONDecodeError as exc:
                raise PiWorkflowContinuationIntegrityError(
                    "pending-permission resolution contains invalid JSON"
                ) from exc
            if _canonical(value) != raw:
                raise PiWorkflowContinuationIntegrityError(
                    "pending-permission resolution JSON is not canonical"
                )
            required = {
                "schema",
                "pending_id",
                "revision",
                "status",
                "resolution",
                "resolved_by",
                "resolved_at_utc",
            }
            if not isinstance(value, dict) or set(value) != required:
                raise PiWorkflowContinuationIntegrityError(
                    "pending-permission resolution fields are invalid"
                )
            if value.get("schema") != "lac.pending-permission-resolution/v1":
                raise PiWorkflowContinuationIntegrityError(
                    "pending-permission resolution schema is unsupported"
                )
            if value.get("pending_id") != pending_id or value.get("revision") != expected_revision:
                raise PiWorkflowContinuationIntegrityError(
                    "pending-permission resolution identity mismatch"
                )
            status = _required_text(value.get("status"), "resolution.status", maximum=32)
            resolution = _required_text(
                value.get("resolution"), "resolution.resolution", maximum=64
            )
            _required_text(value.get("resolved_by"), "resolution.resolved_by", maximum=128)
            _parse_utc(value.get("resolved_at_utc"), "resolution.resolved_at_utc")
            if status not in {"RESOLVED", "DISMISSED"}:
                raise PiWorkflowContinuationIntegrityError(
                    "pending-permission resolution status is unsupported"
                )
            if resolution not in (_AUTHORIZING_RESOLUTIONS | _NONAUTHORIZING_RESOLUTIONS):
                raise PiWorkflowContinuationIntegrityError(
                    "pending-permission resolution value is unsupported"
                )
            if status == "DISMISSED" and resolution != "DISMISSED":
                raise PiWorkflowContinuationIntegrityError(
                    "dismissed pending-permission resolution is inconsistent"
                )
            if status == "RESOLVED" and resolution == "DISMISSED":
                raise PiWorkflowContinuationIntegrityError(
                    "resolved pending-permission item cannot use DISMISSED resolution"
                )
            history.append(dict(value))
        return history

    def _latest_owner_resolution_revision(self, pending_id: str) -> int:
        history = self._owner_resolution_history(pending_id)
        return 0 if not history else int(history[-1]["revision"])

    def _read_owner_resolution(
        self, pending_id: str, *, after_revision: int
    ) -> dict[str, Any] | None:
        if isinstance(after_revision, bool) or not isinstance(after_revision, int) or after_revision < 0:
            raise PiWorkflowContinuationIntegrityError(
                "resolution baseline revision is invalid"
            )
        for item in self._owner_resolution_history(pending_id):
            if int(item["revision"]) > after_revision:
                return item
        return None

    def _expired_wait(self, record: Mapping[str, Any]) -> bool:
        now = self._clock()
        _utc(now)  # validate the trusted clock before comparison
        return (
            record["state"] == "WAITING_PERMISSION"
            and now.astimezone(timezone.utc)
            >= _parse_utc(record["expires_at_utc"], "expires_at_utc")
        )

    def _status_from_record(self, record: Mapping[str, Any]) -> dict[str, Any]:
        resolution = self._read_owner_resolution(
            record["pending_id"],
            after_revision=record["resolution_baseline_revision"],
        )
        effective_state = "EXPIRED" if self._expired_wait(record) else record["state"]
        projection = {
            "schema": PI_V1_CONTINUATION_STATUS_SCHEMA,
            "continuation_id": record["continuation_id"],
            "original_request_id": record["original_request_id"],
            "pending_id": record["pending_id"],
            "state": effective_state,
            "expires_at_utc": record["expires_at_utc"],
            "resume_budget_used": record["resume_budget_used"],
            "fresh_request_id": record["fresh_request_id"],
            "fresh_decision_id": record["fresh_decision_id"],
            "resolution_baseline_revision": record["resolution_baseline_revision"],
            "outcome": record["outcome"],
            "owner_resolution": None,
        }
        if resolution is not None:
            projection["owner_resolution"] = {
                "revision": resolution["revision"],
                "status": resolution["status"],
                "resolution": resolution["resolution"],
                "resolved_at_utc": resolution["resolved_at_utc"],
            }
        return projection

    def capture(
        self,
        *,
        material: Mapping[str, Any],
        canonical_request_hash: str,
        pending_id: str,
    ) -> dict[str, Any]:
        required = {
            "schema",
            "request_id",
            "run_id",
            "action",
            "resource",
            "arguments",
            "idempotency_key",
        }
        if not isinstance(material, Mapping) or set(material) != required:
            raise PiWorkflowContinuationError(
                "continuation capture requires canonical external-consumer request material"
            )
        original_request_id = _required_text(material["request_id"], "request_id")
        original_idempotency_key = _required_text(
            material["idempotency_key"], "idempotency_key"
        )
        run_id = _required_text(material["run_id"], "run_id")
        action = _required_text(material["action"], "action")
        resource = _required_text(material["resource"], "resource")
        canonical_request_hash = _required_text(
            canonical_request_hash, "canonical_request_hash"
        )
        pending_id = _required_text(pending_id, "pending_id")
        if not isinstance(material["arguments"], Mapping):
            raise PiWorkflowContinuationError("continuation arguments must be an object")
        arguments = json.loads(_canonical(dict(material["arguments"])))
        intent_hash = _intent_hash(
            run_id=run_id, action=action, resource=resource, arguments=arguments
        )
        continuation_id = _continuation_id(
            original_request_id=original_request_id,
            canonical_request_hash=canonical_request_hash,
            pending_id=pending_id,
            intent_hash=intent_hash,
        )
        now = self._clock()
        created = _utc(now)
        expires = _utc(now + timedelta(seconds=self._ttl_seconds))
        candidate = {
            "schema": PI_V1_CONTINUATION_SCHEMA,
            "continuation_id": continuation_id,
            "original_request_id": original_request_id,
            "original_canonical_request_hash": canonical_request_hash,
            "original_idempotency_key": original_idempotency_key,
            "pending_id": pending_id,
            "run_id": run_id,
            "action": action,
            "resource": resource,
            "arguments": arguments,
            "intent_hash": intent_hash,
            "created_at_utc": created,
            "expires_at_utc": expires,
            "state": "WAITING_PERMISSION",
            "resume_budget_used": 0,
            "fresh_request_id": None,
            "fresh_idempotency_key": None,
            "fresh_decision_id": None,
            "resolution_baseline_revision": 0,
            "resolution_revision": None,
            "resolution_status": None,
            "resolution": None,
            "completed_at_utc": None,
            "outcome": None,
        }
        with self._store.transaction() as conn:
            queue = self._load_queue_in_transaction(conn)
            candidate["resolution_baseline_revision"] = self._latest_owner_resolution_revision(
                pending_id
            )
            self._validate_record(candidate)
            for existing in queue["records"]:
                if existing["original_request_id"] != original_request_id:
                    continue
                immutable = (
                    "continuation_id",
                    "original_request_id",
                    "original_canonical_request_hash",
                    "original_idempotency_key",
                    "pending_id",
                    "run_id",
                    "action",
                    "resource",
                    "arguments",
                    "intent_hash",
                )
                if any(existing[key] != candidate[key] for key in immutable):
                    raise PiWorkflowContinuationIntegrityError(
                        "closed request is already bound to different continuation intent"
                    )
                return self._status_from_record(existing)

            records = list(queue["records"])
            if len(records) >= PI_V1_CONTINUATION_MAX_RECORDS:
                terminal = [item for item in records if item["state"] in _TERMINAL_STATES]
                if terminal:
                    oldest = min(
                        terminal,
                        key=lambda item: (item["created_at_utc"], item["continuation_id"]),
                    )
                    records = [
                        item
                        for item in records
                        if item["continuation_id"] != oldest["continuation_id"]
                    ]
                else:
                    raise PiWorkflowContinuationError(
                        "workflow-continuation queue is full; fail closed"
                    )
            queue["records"] = records + [candidate]
            self._write_queue_in_transaction(conn, queue)
        return self._status_from_record(candidate)

    def status(self, continuation_id: str) -> dict[str, Any]:
        return self._status_from_record(self._record_by_id(continuation_id))

    def list_status(self, *, recoverable_only: bool = False) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for record in self._queue()["records"]:
            status = self._status_from_record(record)
            if recoverable_only and status["state"] in _TERMINAL_STATES:
                continue
            result.append(status)
        return result

    def assert_expected_intent(
        self, continuation_id: str, expected_material: Mapping[str, Any]
    ) -> None:
        record = self._record_by_id(continuation_id)
        required = {
            "schema",
            "request_id",
            "run_id",
            "action",
            "resource",
            "arguments",
            "idempotency_key",
        }
        if not isinstance(expected_material, Mapping) or set(expected_material) != required:
            raise PiWorkflowContinuationError(
                "continuation expected intent must be canonical request material"
            )
        try:
            expected_arguments = json.loads(_canonical(dict(expected_material["arguments"])))
        except Exception as exc:
            raise PiWorkflowContinuationError("expected continuation intent is malformed") from exc
        compared = {
            "original_request_id": expected_material["request_id"],
            "original_idempotency_key": expected_material["idempotency_key"],
            "run_id": expected_material["run_id"],
            "action": expected_material["action"],
            "resource": expected_material["resource"],
            "arguments": expected_arguments,
        }
        if any(record[key] != value for key, value in compared.items()):
            raise PiWorkflowContinuationError(
                "security-relevant mutation invalidates workflow continuation"
            )
        expected_hash = _intent_hash(
            run_id=compared["run_id"],
            action=compared["action"],
            resource=compared["resource"],
            arguments=compared["arguments"],
        )
        if expected_hash != record["intent_hash"]:
            raise PiWorkflowContinuationError(
                "security-relevant mutation invalidates workflow continuation"
            )

    def prepare_resume(self, continuation_id: str) -> ContinuationPreparation:
        continuation_id = _required_text(continuation_id, "continuation_id")
        resolution = None
        record_snapshot: dict[str, Any] | None = None
        with self._store.transaction() as conn:
            queue = self._load_queue_in_transaction(conn)
            index = self._find_index(queue, continuation_id)
            if index is None:
                raise PiWorkflowContinuationError("workflow continuation was not found")
            record = dict(queue["records"][index])
            if record["state"] == "WAITING_PERMISSION":
                if self._expired_wait(record):
                    record["state"] = "EXPIRED"
                    record["completed_at_utc"] = _utc(self._clock())
                    record["outcome"] = "CONTINUATION_EXPIRED"
                    queue["records"][index] = record
                    self._write_queue_in_transaction(conn, queue)
                    record_snapshot = record
                else:
                    resolution = self._read_owner_resolution(
                        record["pending_id"],
                        after_revision=record["resolution_baseline_revision"],
                    )
                    if resolution is None:
                        record_snapshot = record
                    elif resolution["resolution"] in _NONAUTHORIZING_RESOLUTIONS:
                        record["state"] = "CLOSED_NONAUTH"
                        record["resolution_revision"] = resolution["revision"]
                        record["resolution_status"] = resolution["status"]
                        record["resolution"] = resolution["resolution"]
                        record["completed_at_utc"] = _utc(self._clock())
                        record["outcome"] = (
                            "OWNER_DISMISSED"
                            if resolution["resolution"] == "DISMISSED"
                            else "OWNER_NO_CHANGE"
                        )
                        queue["records"][index] = record
                        self._write_queue_in_transaction(conn, queue)
                        record_snapshot = record
                    elif resolution["resolution"] in _AUTHORIZING_RESOLUTIONS:
                        fresh_request_id, fresh_idempotency_key = _fresh_identity(
                            record["continuation_id"]
                        )
                        record["state"] = "FRESH_REQUEST_CLAIMED"
                        record["resume_budget_used"] = 1
                        record["fresh_request_id"] = fresh_request_id
                        record["fresh_idempotency_key"] = fresh_idempotency_key
                        record["resolution_revision"] = resolution["revision"]
                        record["resolution_status"] = resolution["status"]
                        record["resolution"] = resolution["resolution"]
                        queue["records"][index] = record
                        self._write_queue_in_transaction(conn, queue)
                        record_snapshot = record
                    else:
                        raise PiWorkflowContinuationIntegrityError(
                            "owner resolution is not recognized"
                        )
            else:
                record_snapshot = record

        assert record_snapshot is not None
        status = self._status_from_record(record_snapshot)
        if record_snapshot["state"] in {"WAITING_PERMISSION", "CLOSED_NONAUTH", "EXPIRED", "COMPLETED"}:
            return ContinuationPreparation(state=record_snapshot["state"], status=status)
        if record_snapshot["state"] not in {"FRESH_REQUEST_CLAIMED", "PENDING_APPROVAL"}:
            raise PiWorkflowContinuationIntegrityError(
                "workflow continuation entered unsupported resumable state"
            )
        fresh_material = {
            "schema": "lac.external-consumer-request/v1",
            "request_id": record_snapshot["fresh_request_id"],
            "run_id": record_snapshot["run_id"],
            "action": record_snapshot["action"],
            "resource": record_snapshot["resource"],
            "arguments": record_snapshot["arguments"],
            "idempotency_key": record_snapshot["fresh_idempotency_key"],
        }
        return ContinuationPreparation(
            state=record_snapshot["state"], status=status, fresh_material=fresh_material
        )

    def record_fresh_result(
        self, continuation_id: str, response: Mapping[str, Any]
    ) -> dict[str, Any]:
        continuation_id = _required_text(continuation_id, "continuation_id")
        if not isinstance(response, Mapping):
            raise PiWorkflowContinuationError("fresh request result must be an object")
        with self._store.transaction() as conn:
            queue = self._load_queue_in_transaction(conn)
            index = self._find_index(queue, continuation_id)
            if index is None:
                raise PiWorkflowContinuationError("workflow continuation was not found")
            record = dict(queue["records"][index])
            if record["resume_budget_used"] != 1 or record["fresh_request_id"] is None:
                raise PiWorkflowContinuationIntegrityError(
                    "fresh result arrived before continuation request claim"
                )
            if response.get("request_id") != record["fresh_request_id"]:
                raise PiWorkflowContinuationIntegrityError(
                    "fresh result does not bind the continuation request identity"
                )
            authority = response.get("authority_outcome")
            execution = response.get("execution_state")
            if authority == "REQUIRE_APPROVAL" and execution == "PENDING_APPROVAL":
                decision_id = response.get("decision_id")
                record["state"] = "PENDING_APPROVAL"
                if isinstance(decision_id, str) and decision_id:
                    if record["fresh_decision_id"] is None:
                        record["fresh_decision_id"] = decision_id
                record["outcome"] = "REQUIRE_APPROVAL"
            else:
                record["state"] = "COMPLETED"
                record["completed_at_utc"] = _utc(self._clock())
                reason = response.get("reason")
                record["outcome"] = (
                    str(reason)
                    if isinstance(reason, str) and reason
                    else f"{authority or 'UNKNOWN'}:{execution or 'UNKNOWN'}"
                )
            queue["records"][index] = record
            self._write_queue_in_transaction(conn, queue)
        return self._status_from_record(record)

    def workflow_outcome(self, continuation_id: str) -> dict[str, Any]:
        record = self._record_by_id(continuation_id)
        if record["state"] not in {"CLOSED_NONAUTH", "EXPIRED"}:
            raise PiWorkflowContinuationError(
                "workflow outcome requested for non-terminal continuation"
            )
        reason = (
            "WORKFLOW_CONTINUATION_EXPIRED"
            if record["state"] == "EXPIRED"
            else "WORKFLOW_CONTINUATION_NON_AUTHORIZING"
        )
        return {
            "schema": PI_V1_WORKFLOW_OUTCOME_SCHEMA,
            "request_id": record["original_request_id"],
            "canonical_request_hash": record["original_canonical_request_hash"],
            "authority_outcome": "DENY",
            "execution_state": "NOT_EXECUTED",
            "reason": reason,
            "decision_id": None,
            "result": None,
            "receipt": None,
            "replayed": False,
            "permission_configuration": {"required": False},
            "workflow_continuation": self._status_from_record(record),
        }
