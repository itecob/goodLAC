from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence

from packages.capabilities import (
    SUPPORTED_SECURITY_PROPERTIES,
    CapabilityRequestContext,
    CapabilityValidation,
)
from packages.core import EffectRequest, POLICY_PRECEDENCE, PolicyDecision, PolicyDecisionValue
from packages.state.store import SQLiteStateStore, StateStoreError


STANDING_POLICY_SNAPSHOT_SCHEMA = "lac.standing-policy-snapshot/v1"
STANDING_POLICY_RULE_SCHEMA = "lac.standing-policy-rule/v1"
STANDING_POLICY_DEFAULT_SCHEMA = "lac.standing-policy-default/v1"
STANDING_POLICY_AUDIT_SCHEMA = "lac.standing-policy-audit/v1"
STANDING_POLICY_POINTER_SCHEMA = "lac.standing-policy-pointer/v1"

MAX_STANDING_POLICY_RULES = 512
MAX_STANDING_POLICY_DEFAULTS = 256
MAX_RULE_CONDITIONS = 32
MAX_REQUEST_ARGUMENT_POINTER_DEPTH = 16

_LATEST_KEY = "standing_policy.latest.v1"
_REVISION_PREFIX = "standing_policy.revision.v1."
_AUDIT_PREFIX = "standing_policy.audit.v1."

_SCOPE_FIELDS = (
    "principal_id",
    "application_id",
    "agent_id",
    "skill_id",
    "action",
    "resource_type",
    "resource_selector",
)
_ALLOWED_CONDITION_SOURCES = frozenset({"CAPABILITY", "RESOURCE", "REQUEST"})
_ALLOWED_REQUEST_FIELDS = frozenset({"request_id", "principal_id", "agent_id", "action", "resource", "arguments_hash"})
_MISSING = object()


class StandingPolicyError(StateStoreError):
    """Base error for P003 standing-permission policy operations."""


class StandingPolicyConfigurationError(StandingPolicyError):
    """A proposed standing-policy rule/snapshot is invalid."""


class StandingPolicyIntegrityError(StandingPolicyError):
    """Durable standing-policy material is malformed or inconsistent."""


def _required_text(value: Any, field: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise StandingPolicyConfigurationError(f"{field} must be a non-empty trimmed string")
    if len(value) > maximum:
        raise StandingPolicyConfigurationError(f"{field} exceeds maximum length {maximum}")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise StandingPolicyConfigurationError(f"{field} contains a control character")
    return value


def _optional_text(value: Any, field: str) -> str | None:
    if value is None:
        return None
    return _required_text(value, field)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise StandingPolicyConfigurationError("standing-policy material must be canonical JSON") from exc


def _scalar(value: Any, field: str) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise StandingPolicyConfigurationError(f"{field} must be a finite JSON scalar")


def _normalize_timestamp(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise StandingPolicyConfigurationError(f"{field} must be an RFC3339 timestamp")
    raw = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(raw)
    except ValueError as exc:
        raise StandingPolicyConfigurationError(f"{field} must be an RFC3339 timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise StandingPolicyConfigurationError(f"{field} must include a timezone")
    return parsed.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _parse_decision(value: PolicyDecisionValue | str, field: str) -> PolicyDecisionValue:
    try:
        return value if isinstance(value, PolicyDecisionValue) else PolicyDecisionValue(value)
    except (TypeError, ValueError) as exc:
        raise StandingPolicyConfigurationError(f"{field} has unsupported decision {value!r}") from exc


def _validate_json_pointer(pointer: str) -> str:
    if not pointer.startswith("/"):
        raise StandingPolicyConfigurationError("REQUEST argument condition key must use JSON pointer syntax")
    parts = pointer[1:].split("/")
    if not parts or len(parts) > MAX_REQUEST_ARGUMENT_POINTER_DEPTH:
        raise StandingPolicyConfigurationError("REQUEST argument pointer depth is invalid")
    for raw in parts:
        if raw == "":
            raise StandingPolicyConfigurationError("REQUEST argument pointer contains an empty segment")
        i = 0
        while i < len(raw):
            if raw[i] == "~":
                if i + 1 >= len(raw) or raw[i + 1] not in "01":
                    raise StandingPolicyConfigurationError("REQUEST argument pointer has invalid escape")
                i += 2
            else:
                i += 1
    return pointer


def _decode_pointer_segment(value: str) -> str:
    return value.replace("~1", "/").replace("~0", "~")


def _request_pointer_value(arguments: Any, pointer: str) -> Any:
    current = arguments
    for raw in pointer[1:].split("/"):
        segment = _decode_pointer_segment(raw)
        if isinstance(current, Mapping):
            if segment not in current:
                return _MISSING
            current = current[segment]
            continue
        if isinstance(current, list):
            if not segment.isdigit():
                return _MISSING
            index = int(segment)
            if index < 0 or index >= len(current):
                return _MISSING
            current = current[index]
            continue
        return _MISSING
    return current


@dataclass(frozen=True)
class StandingPolicyCondition:
    source: str
    key: str
    equals_json: str

    @classmethod
    def create(cls, *, source: str, key: str, equals: Any) -> "StandingPolicyCondition":
        normalized_source = _required_text(source, "condition.source", maximum=32).upper()
        if normalized_source not in _ALLOWED_CONDITION_SOURCES:
            raise StandingPolicyConfigurationError(
                f"unsupported condition source: {normalized_source!r}"
            )
        normalized_key = _required_text(key, "condition.key", maximum=512)
        normalized_equals = _scalar(equals, "condition.equals")

        if normalized_source == "CAPABILITY":
            if normalized_key not in SUPPORTED_SECURITY_PROPERTIES:
                raise StandingPolicyConfigurationError(
                    f"CAPABILITY condition key is not a supported security property: {normalized_key!r}"
                )
            if not isinstance(normalized_equals, bool):
                raise StandingPolicyConfigurationError(
                    "CAPABILITY security-property conditions require boolean equals"
                )
        elif normalized_source == "RESOURCE":
            if normalized_key not in {"type", "selector"}:
                raise StandingPolicyConfigurationError(
                    "RESOURCE condition key must be 'type' or 'selector'"
                )
            if not isinstance(normalized_equals, str):
                raise StandingPolicyConfigurationError("RESOURCE conditions require string equals")
        else:
            if normalized_key not in _ALLOWED_REQUEST_FIELDS:
                if not normalized_key.startswith("arguments:"):
                    raise StandingPolicyConfigurationError(
                        "REQUEST condition key must be a canonical request field or arguments:/pointer"
                    )
                _validate_json_pointer(normalized_key[len("arguments:") :])

        return cls(
            source=normalized_source,
            key=normalized_key,
            equals_json=_canonical_json(normalized_equals),
        )

    @property
    def equals(self) -> Any:
        return json.loads(self.equals_json)

    def to_material(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "key": self.key,
            "operator": "EQUALS",
            "equals": self.equals,
        }

    @classmethod
    def from_material(cls, value: Mapping[str, Any]) -> "StandingPolicyCondition":
        if not isinstance(value, Mapping) or set(value) != {"source", "key", "operator", "equals"}:
            raise StandingPolicyConfigurationError("standing-policy condition fields are invalid")
        if value["operator"] != "EQUALS":
            raise StandingPolicyConfigurationError("standing-policy v1 supports only EQUALS conditions")
        return cls.create(source=value["source"], key=value["key"], equals=value["equals"])

    def matches(
        self,
        request: EffectRequest,
        *,
        validation: CapabilityValidation,
    ) -> bool:
        expected = self.equals
        if self.source == "CAPABILITY":
            observed: Any = self.key in set(validation.security_properties)
        elif self.source == "RESOURCE":
            observed = validation.resource_type if self.key == "type" else request.resource
        else:
            if self.key == "arguments_hash":
                observed = "sha256:" + hashlib.sha256(
                    _canonical_json(request.arguments).encode("utf-8")
                ).hexdigest()
            elif self.key in _ALLOWED_REQUEST_FIELDS:
                observed = getattr(request, self.key)
            else:
                observed = _request_pointer_value(
                    request.arguments,
                    self.key[len("arguments:") :],
                )
                if observed is _MISSING:
                    return False
        return type(observed) is type(expected) and observed == expected


@dataclass(frozen=True)
class StandingPolicyRule:
    rule_id: str
    decision: PolicyDecisionValue
    principal_id: str | None = None
    application_id: str | None = None
    agent_id: str | None = None
    skill_id: str | None = None
    action: str | None = None
    resource_type: str | None = None
    resource_selector: str | None = None
    conditions: tuple[StandingPolicyCondition, ...] = ()

    @classmethod
    def create(
        cls,
        *,
        rule_id: str,
        decision: PolicyDecisionValue | str,
        principal_id: str | None = None,
        application_id: str | None = None,
        agent_id: str | None = None,
        skill_id: str | None = None,
        action: str | None = None,
        resource_type: str | None = None,
        resource_selector: str | None = None,
        conditions: Iterable[StandingPolicyCondition] = (),
    ) -> "StandingPolicyRule":
        try:
            normalized_conditions = tuple(conditions)
        except TypeError as exc:
            raise StandingPolicyConfigurationError("conditions must be iterable") from exc
        if len(normalized_conditions) > MAX_RULE_CONDITIONS:
            raise StandingPolicyConfigurationError(
                f"rule conditions exceed maximum {MAX_RULE_CONDITIONS}"
            )
        for condition in normalized_conditions:
            if not isinstance(condition, StandingPolicyCondition):
                raise StandingPolicyConfigurationError(
                    "conditions must contain StandingPolicyCondition values"
                )
        normalized_conditions = tuple(
            sorted(normalized_conditions, key=lambda item: _canonical_json(item.to_material()))
        )
        condition_material = [_canonical_json(item.to_material()) for item in normalized_conditions]
        if len(condition_material) != len(set(condition_material)):
            raise StandingPolicyConfigurationError("rule contains a duplicate condition")

        return cls(
            rule_id=_required_text(rule_id, "rule_id", maximum=256),
            decision=_parse_decision(decision, "rule.decision"),
            principal_id=_optional_text(principal_id, "principal_id"),
            application_id=_optional_text(application_id, "application_id"),
            agent_id=_optional_text(agent_id, "agent_id"),
            skill_id=_optional_text(skill_id, "skill_id"),
            action=_optional_text(action, "action"),
            resource_type=_optional_text(resource_type, "resource_type"),
            resource_selector=_optional_text(resource_selector, "resource_selector"),
            conditions=normalized_conditions,
        )

    @property
    def specificity(self) -> int:
        scope_count = sum(getattr(self, field) is not None for field in _SCOPE_FIELDS)
        return scope_count + len(self.conditions)

    def to_material(self) -> dict[str, Any]:
        scope = {field: getattr(self, field) for field in _SCOPE_FIELDS if getattr(self, field) is not None}
        return {
            "schema": STANDING_POLICY_RULE_SCHEMA,
            "rule_id": self.rule_id,
            "decision": self.decision.value,
            "scope": scope,
            "conditions": [condition.to_material() for condition in self.conditions],
        }

    @classmethod
    def from_material(cls, value: Mapping[str, Any]) -> "StandingPolicyRule":
        if not isinstance(value, Mapping) or set(value) != {
            "schema", "rule_id", "decision", "scope", "conditions"
        }:
            raise StandingPolicyConfigurationError("standing-policy rule fields are invalid")
        if value["schema"] != STANDING_POLICY_RULE_SCHEMA:
            raise StandingPolicyConfigurationError("unsupported standing-policy rule schema")
        if not isinstance(value["scope"], Mapping) or set(value["scope"]) - set(_SCOPE_FIELDS):
            raise StandingPolicyConfigurationError("standing-policy rule scope is invalid")
        if not isinstance(value["conditions"], list):
            raise StandingPolicyConfigurationError("standing-policy rule conditions must be an array")
        conditions = [StandingPolicyCondition.from_material(item) for item in value["conditions"]]
        return cls.create(
            rule_id=value["rule_id"],
            decision=value["decision"],
            conditions=conditions,
            **dict(value["scope"]),
        )

    def matches(
        self,
        request: EffectRequest,
        *,
        context: CapabilityRequestContext,
        validation: CapabilityValidation,
    ) -> bool:
        actual = {
            "principal_id": request.principal_id,
            "application_id": context.application_id,
            "agent_id": request.agent_id,
            "skill_id": context.skill_id,
            "action": request.action,
            "resource_type": validation.resource_type,
            "resource_selector": request.resource,
        }
        for field in _SCOPE_FIELDS:
            expected = getattr(self, field)
            if expected is not None and actual[field] != expected:
                return False
        return all(condition.matches(request, validation=validation) for condition in self.conditions)


@dataclass(frozen=True)
class StandingPolicyDefault:
    default_id: str
    application_id: str
    skill_id: str | None
    decision: PolicyDecisionValue

    @classmethod
    def create(
        cls,
        *,
        default_id: str,
        application_id: str,
        decision: PolicyDecisionValue | str,
        skill_id: str | None = None,
    ) -> "StandingPolicyDefault":
        return cls(
            default_id=_required_text(default_id, "default_id", maximum=256),
            application_id=_required_text(application_id, "application_id"),
            skill_id=_optional_text(skill_id, "skill_id"),
            decision=_parse_decision(decision, "default.decision"),
        )

    @property
    def specificity(self) -> int:
        return 2 if self.skill_id is not None else 1

    def matches(self, context: CapabilityRequestContext) -> bool:
        return self.application_id == context.application_id and (
            self.skill_id is None or self.skill_id == context.skill_id
        )

    def to_material(self) -> dict[str, Any]:
        material = {
            "schema": STANDING_POLICY_DEFAULT_SCHEMA,
            "default_id": self.default_id,
            "application_id": self.application_id,
            "decision": self.decision.value,
        }
        if self.skill_id is not None:
            material["skill_id"] = self.skill_id
        return material

    @classmethod
    def from_material(cls, value: Mapping[str, Any]) -> "StandingPolicyDefault":
        if not isinstance(value, Mapping):
            raise StandingPolicyConfigurationError("standing-policy default must be an object")
        allowed = {"schema", "default_id", "application_id", "skill_id", "decision"}
        required = {"schema", "default_id", "application_id", "decision"}
        if set(value) - allowed or not required.issubset(value):
            raise StandingPolicyConfigurationError("standing-policy default fields are invalid")
        if value["schema"] != STANDING_POLICY_DEFAULT_SCHEMA:
            raise StandingPolicyConfigurationError("unsupported standing-policy default schema")
        return cls.create(
            default_id=value["default_id"],
            application_id=value["application_id"],
            skill_id=value.get("skill_id"),
            decision=value["decision"],
        )


@dataclass(frozen=True)
class StandingPolicySnapshot:
    schema: str
    revision: int
    policy_hash: str
    rules: tuple[StandingPolicyRule, ...]
    defaults: tuple[StandingPolicyDefault, ...]

    @classmethod
    def create(
        cls,
        *,
        revision: int,
        rules: Iterable[StandingPolicyRule],
        defaults: Iterable[StandingPolicyDefault] = (),
    ) -> "StandingPolicySnapshot":
        if isinstance(revision, bool) or not isinstance(revision, int) or revision < 1:
            raise StandingPolicyConfigurationError("standing-policy revision must be a positive integer")
        try:
            normalized_rules = tuple(rules)
            normalized_defaults = tuple(defaults)
        except TypeError as exc:
            raise StandingPolicyConfigurationError("rules/defaults must be iterable") from exc
        if len(normalized_rules) > MAX_STANDING_POLICY_RULES:
            raise StandingPolicyConfigurationError(
                f"standing-policy rules exceed maximum {MAX_STANDING_POLICY_RULES}"
            )
        if len(normalized_defaults) > MAX_STANDING_POLICY_DEFAULTS:
            raise StandingPolicyConfigurationError(
                f"standing-policy defaults exceed maximum {MAX_STANDING_POLICY_DEFAULTS}"
            )
        if any(not isinstance(rule, StandingPolicyRule) for rule in normalized_rules):
            raise StandingPolicyConfigurationError("rules must contain StandingPolicyRule values")
        if any(not isinstance(item, StandingPolicyDefault) for item in normalized_defaults):
            raise StandingPolicyConfigurationError(
                "defaults must contain StandingPolicyDefault values"
            )
        normalized_rules = tuple(sorted(normalized_rules, key=lambda item: item.rule_id))
        normalized_defaults = tuple(sorted(normalized_defaults, key=lambda item: item.default_id))
        rule_ids = [item.rule_id for item in normalized_rules]
        default_ids = [item.default_id for item in normalized_defaults]
        if len(rule_ids) != len(set(rule_ids)):
            raise StandingPolicyConfigurationError("standing-policy contains duplicate rule_id")
        if len(default_ids) != len(set(default_ids)):
            raise StandingPolicyConfigurationError("standing-policy contains duplicate default_id")
        default_scopes = [(item.application_id, item.skill_id) for item in normalized_defaults]
        if len(default_scopes) != len(set(default_scopes)):
            raise StandingPolicyConfigurationError(
                "standing-policy contains duplicate application/skill default scope"
            )
        body = {
            "rules": [item.to_material() for item in normalized_rules],
            "defaults": [item.to_material() for item in normalized_defaults],
        }
        policy_hash = "sha256:" + hashlib.sha256(_canonical_json(body).encode("utf-8")).hexdigest()
        return cls(
            schema=STANDING_POLICY_SNAPSHOT_SCHEMA,
            revision=revision,
            policy_hash=policy_hash,
            rules=normalized_rules,
            defaults=normalized_defaults,
        )

    @property
    def revision_id(self) -> str:
        return f"standing-policy:{self.revision}:{self.policy_hash}"

    @property
    def snapshot_hash(self) -> str:
        return "sha256:" + hashlib.sha256(self.canonical_json().encode("utf-8")).hexdigest()

    def to_material(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "revision": self.revision,
            "policy_hash": self.policy_hash,
            "rules": [item.to_material() for item in self.rules],
            "defaults": [item.to_material() for item in self.defaults],
        }

    def canonical_json(self) -> str:
        return _canonical_json(self.to_material())

    @classmethod
    def from_canonical_json(cls, raw_json: str) -> "StandingPolicySnapshot":
        try:
            value = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise StandingPolicyIntegrityError("standing-policy snapshot contains invalid JSON") from exc
        if not isinstance(value, Mapping) or set(value) != {
            "schema", "revision", "policy_hash", "rules", "defaults"
        }:
            raise StandingPolicyIntegrityError("standing-policy snapshot fields are invalid")
        if value["schema"] != STANDING_POLICY_SNAPSHOT_SCHEMA:
            raise StandingPolicyIntegrityError("unsupported standing-policy snapshot schema")
        try:
            snapshot = cls.create(
                revision=value["revision"],
                rules=[StandingPolicyRule.from_material(item) for item in value["rules"]],
                defaults=[StandingPolicyDefault.from_material(item) for item in value["defaults"]],
            )
        except (StandingPolicyConfigurationError, TypeError) as exc:
            raise StandingPolicyIntegrityError("standing-policy snapshot failed canonical validation") from exc
        if snapshot.policy_hash != value["policy_hash"]:
            raise StandingPolicyIntegrityError("standing-policy snapshot policy_hash mismatch")
        if snapshot.canonical_json() != raw_json:
            raise StandingPolicyIntegrityError("standing-policy snapshot JSON is not canonical")
        return snapshot


class StandingPolicyRepository:
    """Internal/controller-only atomic revisioned standing-policy repository."""

    def __init__(self, store: SQLiteStateStore):
        if not isinstance(store, SQLiteStateStore):
            raise StandingPolicyError("store must be a SQLiteStateStore")
        self._store = store

    @staticmethod
    def _revision_key(revision: int) -> str:
        return f"{_REVISION_PREFIX}{revision:020d}"

    @staticmethod
    def _audit_key(revision: int) -> str:
        return f"{_AUDIT_PREFIX}{revision:020d}"

    def _raw(self, key: str) -> str | None:
        row = self._store._conn.execute(
            "SELECT value_json FROM system_state WHERE key = ?", (key,)
        ).fetchone()
        return None if row is None else str(row["value_json"])

    def _rows(self, prefix: str) -> list[tuple[str, str]]:
        rows = self._store._conn.execute(
            "SELECT key, value_json FROM system_state WHERE key LIKE ? ORDER BY key",
            (prefix + "%",),
        ).fetchall()
        return [(str(row["key"]), str(row["value_json"])) for row in rows]

    @staticmethod
    def _strict_object(raw_json: str, *, required: set[str], context: str) -> dict[str, Any]:
        try:
            value = json.loads(raw_json)
        except (TypeError, json.JSONDecodeError) as exc:
            raise StandingPolicyIntegrityError(f"{context} contains invalid JSON") from exc
        if not isinstance(value, dict) or set(value) != required:
            raise StandingPolicyIntegrityError(f"{context} fields are invalid")
        if _canonical_json(value) != raw_json:
            raise StandingPolicyIntegrityError(f"{context} JSON is not canonical")
        return value

    def history(self) -> list[StandingPolicySnapshot]:
        pointer_raw = self._raw(_LATEST_KEY)
        rows = self._rows(_REVISION_PREFIX)
        audits = self._rows(_AUDIT_PREFIX)
        if pointer_raw is None:
            if rows or audits:
                raise StandingPolicyIntegrityError(
                    "orphaned standing-policy rows exist without a latest pointer"
                )
            return []
        pointer = self._strict_object(
            pointer_raw,
            required={"schema", "revision", "policy_hash", "snapshot_hash"},
            context="standing-policy pointer",
        )
        if pointer["schema"] != STANDING_POLICY_POINTER_SCHEMA:
            raise StandingPolicyIntegrityError("unsupported standing-policy pointer schema")
        pointer_revision = pointer["revision"]
        if (
            isinstance(pointer_revision, bool)
            or not isinstance(pointer_revision, int)
            or pointer_revision < 1
        ):
            raise StandingPolicyIntegrityError("standing-policy pointer revision is invalid")
        snapshots: list[StandingPolicySnapshot] = []
        for expected_revision, (key, raw_json) in enumerate(rows, start=1):
            if key != self._revision_key(expected_revision):
                raise StandingPolicyIntegrityError("standing-policy revision history is not contiguous")
            snapshot = StandingPolicySnapshot.from_canonical_json(raw_json)
            if snapshot.revision != expected_revision:
                raise StandingPolicyIntegrityError("standing-policy revision/key mismatch")
            snapshots.append(snapshot)
        if not snapshots:
            raise StandingPolicyIntegrityError("standing-policy pointer exists without revisions")
        latest = snapshots[-1]
        if (
            pointer["revision"] != latest.revision
            or pointer["policy_hash"] != latest.policy_hash
            or pointer["snapshot_hash"] != latest.snapshot_hash
        ):
            raise StandingPolicyIntegrityError("standing-policy pointer does not bind latest revision")
        if len(audits) != len(snapshots):
            raise StandingPolicyIntegrityError("standing-policy audit history is incomplete")
        previous_hash: str | None = None
        for expected_revision, ((key, raw_json), snapshot) in enumerate(zip(audits, snapshots), start=1):
            if key != self._audit_key(expected_revision):
                raise StandingPolicyIntegrityError("standing-policy audit history is not contiguous")
            event = self._strict_object(
                raw_json,
                required={
                    "schema", "event_type", "revision", "policy_hash", "previous_policy_hash",
                    "rule_count", "default_count", "changed_at_utc"
                },
                context="standing-policy audit event",
            )
            event_revision = event["revision"]
            rule_count = event["rule_count"]
            default_count = event["default_count"]
            if (
                isinstance(event_revision, bool)
                or not isinstance(event_revision, int)
                or isinstance(rule_count, bool)
                or not isinstance(rule_count, int)
                or rule_count < 0
                or isinstance(default_count, bool)
                or not isinstance(default_count, int)
                or default_count < 0
            ):
                raise StandingPolicyIntegrityError(
                    "standing-policy audit numeric fields are invalid"
                )
            try:
                normalized_changed_at = _normalize_timestamp(
                    event["changed_at_utc"], "audit.changed_at_utc"
                )
            except StandingPolicyConfigurationError as exc:
                raise StandingPolicyIntegrityError(
                    "standing-policy audit timestamp is invalid"
                ) from exc
            if normalized_changed_at != event["changed_at_utc"]:
                raise StandingPolicyIntegrityError(
                    "standing-policy audit timestamp is non-canonical"
                )
            if (
                event["schema"] != STANDING_POLICY_AUDIT_SCHEMA
                or event["event_type"] != "REPLACE"
                or event_revision != expected_revision
                or event["policy_hash"] != snapshot.policy_hash
                or event["previous_policy_hash"] != previous_hash
                or rule_count != len(snapshot.rules)
                or default_count != len(snapshot.defaults)
            ):
                raise StandingPolicyIntegrityError("standing-policy audit event is inconsistent")
            previous_hash = snapshot.policy_hash
        return snapshots

    def current(self) -> StandingPolicySnapshot | None:
        history = self.history()
        return history[-1] if history else None

    def replace_admin(
        self,
        *,
        rules: Iterable[StandingPolicyRule],
        defaults: Iterable[StandingPolicyDefault] = (),
        changed_at_utc: str | None = None,
    ) -> StandingPolicySnapshot:
        history = self.history()
        revision = len(history) + 1
        candidate = StandingPolicySnapshot.create(
            revision=revision,
            rules=rules,
            defaults=defaults,
        )
        if history and history[-1].policy_hash == candidate.policy_hash:
            return history[-1]
        timestamp = _normalize_timestamp(
            changed_at_utc or self._store._utc_now(),
            "changed_at_utc",
        )
        previous_hash = history[-1].policy_hash if history else None
        pointer = {
            "schema": STANDING_POLICY_POINTER_SCHEMA,
            "revision": candidate.revision,
            "policy_hash": candidate.policy_hash,
            "snapshot_hash": candidate.snapshot_hash,
        }
        event = {
            "schema": STANDING_POLICY_AUDIT_SCHEMA,
            "event_type": "REPLACE",
            "revision": candidate.revision,
            "policy_hash": candidate.policy_hash,
            "previous_policy_hash": previous_hash,
            "rule_count": len(candidate.rules),
            "default_count": len(candidate.defaults),
            "changed_at_utc": timestamp,
        }
        try:
            with self._store.transaction() as conn:
                conn.execute(
                    "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?)",
                    (self._revision_key(candidate.revision), candidate.canonical_json(), timestamp),
                )
                conn.execute(
                    "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?)",
                    (self._audit_key(candidate.revision), _canonical_json(event), timestamp),
                )
                conn.execute(
                    """
                    INSERT INTO system_state(key, value_json, updated_at_utc)
                    VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value_json = excluded.value_json,
                        updated_at_utc = excluded.updated_at_utc
                    """,
                    (_LATEST_KEY, _canonical_json(pointer), timestamp),
                )
        except Exception as exc:
            if isinstance(exc, StateStoreError):
                raise
            raise StandingPolicyError("standing-policy mutation failed atomically") from exc
        return candidate


class StandingPolicyDecisionProvider:
    """Capability-aware standing-policy evaluator over P002-validated trusted metadata."""

    def __init__(self, store: SQLiteStateStore):
        if not isinstance(store, SQLiteStateStore):
            raise StandingPolicyError("store must be a SQLiteStateStore")
        self._repository = StandingPolicyRepository(store)

    @property
    def policy_revision(self) -> str:
        snapshot = self._repository.current()
        return "standing-policy:none" if snapshot is None else snapshot.revision_id

    @staticmethod
    def _decision(
        request: EffectRequest,
        *,
        decision_id: str,
        evaluated_at: str,
        policy_revision: str,
        decision: PolicyDecisionValue,
        reason_codes: Sequence[str],
    ) -> PolicyDecision:
        return PolicyDecision.create(
            decision_id=decision_id,
            request_id=request.request_id,
            decision=decision,
            policy_revision=policy_revision,
            reason_codes=reason_codes,
            evaluated_at=evaluated_at,
            canonical_request_hash=request.canonical_hash,
        )

    def evaluate(
        self,
        request: EffectRequest,
        *,
        decision_id: str,
        evaluated_at: str,
    ) -> PolicyDecision:
        if not isinstance(request, EffectRequest):
            raise StandingPolicyConfigurationError("request must be a canonical EffectRequest")
        revision = self.policy_revision
        return self._decision(
            request,
            decision_id=decision_id,
            evaluated_at=evaluated_at,
            policy_revision=revision,
            decision=PolicyDecisionValue.DENY,
            reason_codes=("STANDING_POLICY_REQUIRES_VALIDATED_CAPABILITY_CONTEXT",),
        )

    @staticmethod
    def _validate_trusted_context(
        request: EffectRequest,
        context: CapabilityRequestContext,
        validation: CapabilityValidation,
    ) -> None:
        if not isinstance(context, CapabilityRequestContext):
            raise StandingPolicyConfigurationError("capability_context is required")
        if not isinstance(validation, CapabilityValidation):
            raise StandingPolicyConfigurationError("capability_validation is required")
        if (
            validation.application_id != context.application_id
            or validation.skill_id != context.skill_id
            or validation.capability_revision != context.capability_revision
            or validation.manifest_version != context.manifest_version
            or validation.resource_type != context.resource_type
            or validation.action != request.action
            or validation.resource != request.resource
        ):
            raise StandingPolicyIntegrityError(
                "validated capability context does not bind the canonical request"
            )
        properties = tuple(validation.security_properties)
        if tuple(sorted(set(properties))) != properties:
            raise StandingPolicyIntegrityError("capability security properties are non-canonical")
        if any(prop not in SUPPORTED_SECURITY_PROPERTIES for prop in properties):
            raise StandingPolicyIntegrityError("capability validation contains unknown security property")

    def evaluate_capability(
        self,
        request: EffectRequest,
        *,
        capability_context: CapabilityRequestContext,
        capability_validation: CapabilityValidation,
        decision_id: str,
        evaluated_at: str,
    ) -> PolicyDecision:
        if not isinstance(request, EffectRequest):
            raise StandingPolicyConfigurationError("request must be a canonical EffectRequest")
        self._validate_trusted_context(request, capability_context, capability_validation)
        snapshot = self._repository.current()
        revision = "standing-policy:none" if snapshot is None else snapshot.revision_id
        if snapshot is None:
            return self._decision(
                request,
                decision_id=decision_id,
                evaluated_at=evaluated_at,
                policy_revision=revision,
                decision=PolicyDecisionValue.DENY,
                reason_codes=("NO_STANDING_POLICY",),
            )

        matching = [
            rule
            for rule in snapshot.rules
            if rule.matches(
                request,
                context=capability_context,
                validation=capability_validation,
            )
        ]
        if matching:
            max_specificity = max(rule.specificity for rule in matching)
            finalists = sorted(
                (rule for rule in matching if rule.specificity == max_specificity),
                key=lambda item: item.rule_id,
            )
            strongest = max(
                (rule.decision for rule in finalists),
                key=lambda decision: POLICY_PRECEDENCE[decision],
            )
            reasons = [f"MATCHED_STANDING_RULE:{rule.rule_id}" for rule in finalists]
            reasons.extend((f"SPECIFICITY:{max_specificity}", f"DECISION:{strongest.value}"))
            if len({rule.decision for rule in finalists}) > 1:
                if strongest is PolicyDecisionValue.DENY:
                    reasons.append("DENY_PRECEDENCE_APPLIED")
                elif strongest is PolicyDecisionValue.REQUIRE_APPROVAL:
                    reasons.append("APPROVAL_PRECEDENCE_APPLIED")
            return self._decision(
                request,
                decision_id=decision_id,
                evaluated_at=evaluated_at,
                policy_revision=revision,
                decision=strongest,
                reason_codes=reasons,
            )

        defaults = [item for item in snapshot.defaults if item.matches(capability_context)]
        if defaults:
            max_specificity = max(item.specificity for item in defaults)
            finalists = [item for item in defaults if item.specificity == max_specificity]
            if len(finalists) != 1:
                raise StandingPolicyIntegrityError(
                    "standing-policy contains ambiguous equal-scope defaults"
                )
            chosen = finalists[0]
            return self._decision(
                request,
                decision_id=decision_id,
                evaluated_at=evaluated_at,
                policy_revision=revision,
                decision=chosen.decision,
                reason_codes=(
                    f"MATCHED_STANDING_DEFAULT:{chosen.default_id}",
                    f"DECISION:{chosen.decision.value}",
                ),
            )

        return self._decision(
            request,
            decision_id=decision_id,
            evaluated_at=evaluated_at,
            policy_revision=revision,
            decision=PolicyDecisionValue.DENY,
            reason_codes=("NO_MATCHING_RULE_OR_DEFAULT",),
        )
