from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


CAPABILITY_MANIFEST_SCHEMA = "lac.capability-manifest/v1"
CAPABILITY_MANIFEST_VERSION = 1

SUPPORTED_SECURITY_PROPERTIES = frozenset(
    {
        "read_only",
        "local_mutation",
        "external_mutation",
        "destructive",
        "external_communication",
        "credential_sensitive",
        "security_sensitive",
        "permission_change",
        "network_egress",
        "privilege_change",
    }
)

MAX_ACTIONS = 128
MAX_SELECTORS_PER_ACTION = 128
MAX_SCHEMA_DEPTH = 8
MAX_SCHEMA_NODES = 256
MAX_STRING_LENGTH_BOUND = 1_048_576
MAX_ARRAY_ITEMS_BOUND = 4096

_ID_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_ACTION_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,159}$")
_RESOURCE_TYPE_RE = re.compile(r"^[a-z0-9][a-z0-9._-]{0,127}$")
_SELECTOR_RE = re.compile(r"^[a-z0-9][a-z0-9._:/@-]{0,255}$")
_ARGUMENT_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.-]{0,127}$")


class CapabilityManifestError(ValueError):
    """Base error for invalid or non-canonical capability manifests."""


class UnsupportedCapabilityManifestVersion(CapabilityManifestError):
    """Raised when the manifest schema/version is unsupported."""


class DuplicateManifestKey(CapabilityManifestError):
    """Raised when raw JSON contains duplicate object keys."""


def _canonical_json(value: Any) -> str:
    _validate_json_value(value)
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise CapabilityManifestError("value cannot be encoded as canonical JSON") from exc


def _validate_json_value(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise CapabilityManifestError(f"{path} contains a non-finite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise CapabilityManifestError(f"{path} contains a non-string object key")
            _validate_json_value(item, f"{path}.{key}")
        return
    raise CapabilityManifestError(f"{path} contains a value outside canonical JSON")


def _strict_object_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateManifestKey(f"duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def _required_text(value: Any, field: str, pattern: re.Pattern[str]) -> str:
    if not isinstance(value, str) or not value:
        raise CapabilityManifestError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise CapabilityManifestError(f"{field} must not contain leading/trailing whitespace")
    if any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value):
        raise CapabilityManifestError(f"{field} contains a control character")
    if pattern.fullmatch(value) is None:
        raise CapabilityManifestError(f"{field} is not a canonical identifier")
    return value


def _bounded_display_text(value: Any, field: str, maximum: int) -> str:
    if not isinstance(value, str) or not value:
        raise CapabilityManifestError(f"{field} must be a non-empty string")
    if value != value.strip():
        raise CapabilityManifestError(f"{field} must not contain leading/trailing whitespace")
    if len(value) > maximum:
        raise CapabilityManifestError(f"{field} exceeds maximum length {maximum}")
    if any((ord(ch) < 0x20 and ch not in "\n\t") or ord(ch) == 0x7F for ch in value):
        raise CapabilityManifestError(f"{field} contains a forbidden control character")
    return value


def _require_exact_fields(
    value: Mapping[str, Any], *, required: set[str], optional: set[str], path: str
) -> None:
    observed = set(value)
    missing = required - observed
    unknown = observed - required - optional
    if missing or unknown:
        raise CapabilityManifestError(
            f"{path} fields invalid; missing={sorted(missing)} unknown={sorted(unknown)}"
        )


def _normalize_display(value: Any) -> dict[str, str] | None:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise CapabilityManifestError("display must be an object when present")
    raw = dict(value)
    _require_exact_fields(raw, required={"name"}, optional={"description"}, path="display")
    result = {"name": _bounded_display_text(raw["name"], "display.name", 160)}
    if "description" in raw:
        result["description"] = _bounded_display_text(
            raw["description"], "display.description", 1000
        )
    return result


def _number(value: Any, field: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise CapabilityManifestError(f"{field} must be a finite JSON number")
    if isinstance(value, float) and not math.isfinite(value):
        raise CapabilityManifestError(f"{field} must be finite")
    return value


def _normalize_enum(values: Any, *, path: str, expected_type: str) -> list[Any]:
    if not isinstance(values, list) or not values:
        raise CapabilityManifestError(f"{path}.enum must be a non-empty array")
    normalized: list[Any] = []
    seen: set[str] = set()
    for index, item in enumerate(values):
        if expected_type == "string" and not isinstance(item, str):
            raise CapabilityManifestError(f"{path}.enum[{index}] must be a string")
        if expected_type == "integer" and (isinstance(item, bool) or not isinstance(item, int)):
            raise CapabilityManifestError(f"{path}.enum[{index}] must be an integer")
        if expected_type == "number" and (
            isinstance(item, bool) or not isinstance(item, (int, float))
        ):
            raise CapabilityManifestError(f"{path}.enum[{index}] must be a number")
        if expected_type == "boolean" and not isinstance(item, bool):
            raise CapabilityManifestError(f"{path}.enum[{index}] must be boolean")
        _validate_json_value(item, f"{path}.enum[{index}]")
        encoded = _canonical_json(item)
        if encoded in seen:
            raise CapabilityManifestError(f"{path}.enum contains a duplicate value")
        seen.add(encoded)
        normalized.append(item)
    return sorted(normalized, key=_canonical_json)


def _normalize_argument_schema(
    value: Any,
    *,
    path: str = "arguments",
    depth: int = 0,
    node_counter: list[int] | None = None,
) -> dict[str, Any]:
    if node_counter is None:
        node_counter = [0]
    node_counter[0] += 1
    if node_counter[0] > MAX_SCHEMA_NODES:
        raise CapabilityManifestError(
            f"argument schema exceeds maximum node count {MAX_SCHEMA_NODES}"
        )
    if depth > MAX_SCHEMA_DEPTH:
        raise CapabilityManifestError(
            f"argument schema exceeds maximum depth {MAX_SCHEMA_DEPTH}"
        )
    if not isinstance(value, Mapping):
        raise CapabilityManifestError(f"{path} must be an object")
    raw = dict(value)
    if "type" not in raw:
        raise CapabilityManifestError(f"{path}.type is required")
    schema_type = raw["type"]
    if schema_type not in {"object", "array", "string", "integer", "number", "boolean", "null"}:
        raise CapabilityManifestError(f"{path}.type is unsupported: {schema_type!r}")

    if schema_type == "object":
        _require_exact_fields(
            raw,
            required={"type", "properties", "required", "additionalProperties"},
            optional=set(),
            path=path,
        )
        if raw["additionalProperties"] is not False:
            raise CapabilityManifestError(
                f"{path}.additionalProperties must be false for a bounded object schema"
            )
        if not isinstance(raw["properties"], Mapping):
            raise CapabilityManifestError(f"{path}.properties must be an object")
        if len(raw["properties"]) > 128:
            raise CapabilityManifestError(f"{path}.properties exceeds 128 fields")
        properties: dict[str, Any] = {}
        for name, child in raw["properties"].items():
            if not isinstance(name, str) or _ARGUMENT_NAME_RE.fullmatch(name) is None:
                raise CapabilityManifestError(
                    f"{path}.properties contains a non-canonical property name: {name!r}"
                )
            properties[name] = _normalize_argument_schema(
                child,
                path=f"{path}.properties.{name}",
                depth=depth + 1,
                node_counter=node_counter,
            )
        required = raw["required"]
        if not isinstance(required, list):
            raise CapabilityManifestError(f"{path}.required must be an array")
        seen_required: set[str] = set()
        for name in required:
            if not isinstance(name, str):
                raise CapabilityManifestError(f"{path}.required entries must be strings")
            if name in seen_required:
                raise CapabilityManifestError(f"{path}.required contains duplicates")
            seen_required.add(name)
            if name not in properties:
                raise CapabilityManifestError(
                    f"{path}.required references an undeclared property: {name!r}"
                )
        return {
            "type": "object",
            "properties": properties,
            "required": sorted(required),
            "additionalProperties": False,
        }

    if schema_type == "array":
        _require_exact_fields(
            raw,
            required={"type", "items", "maxItems"},
            optional={"minItems"},
            path=path,
        )
        max_items = raw["maxItems"]
        min_items = raw.get("minItems", 0)
        if isinstance(max_items, bool) or not isinstance(max_items, int):
            raise CapabilityManifestError(f"{path}.maxItems must be an integer")
        if isinstance(min_items, bool) or not isinstance(min_items, int):
            raise CapabilityManifestError(f"{path}.minItems must be an integer")
        if not (0 <= min_items <= max_items <= MAX_ARRAY_ITEMS_BOUND):
            raise CapabilityManifestError(
                f"{path} requires 0 <= minItems <= maxItems <= {MAX_ARRAY_ITEMS_BOUND}"
            )
        normalized = {
            "type": "array",
            "items": _normalize_argument_schema(
                raw["items"],
                path=f"{path}.items",
                depth=depth + 1,
                node_counter=node_counter,
            ),
            "maxItems": max_items,
        }
        if "minItems" in raw:
            normalized["minItems"] = min_items
        return normalized

    if schema_type == "string":
        _require_exact_fields(
            raw,
            required={"type", "maxLength"},
            optional={"minLength", "enum"},
            path=path,
        )
        max_length = raw["maxLength"]
        min_length = raw.get("minLength", 0)
        if isinstance(max_length, bool) or not isinstance(max_length, int):
            raise CapabilityManifestError(f"{path}.maxLength must be an integer")
        if isinstance(min_length, bool) or not isinstance(min_length, int):
            raise CapabilityManifestError(f"{path}.minLength must be an integer")
        if not (0 <= min_length <= max_length <= MAX_STRING_LENGTH_BOUND):
            raise CapabilityManifestError(
                f"{path} requires 0 <= minLength <= maxLength <= {MAX_STRING_LENGTH_BOUND}"
            )
        normalized: dict[str, Any] = {"type": "string", "maxLength": max_length}
        if "minLength" in raw:
            normalized["minLength"] = min_length
        if "enum" in raw:
            values = _normalize_enum(raw["enum"], path=path, expected_type="string")
            for item in values:
                if not (min_length <= len(item) <= max_length):
                    raise CapabilityManifestError(
                        f"{path}.enum value violates declared string length bounds"
                    )
            normalized["enum"] = values
        return normalized

    if schema_type in {"integer", "number"}:
        _require_exact_fields(
            raw,
            required={"type", "minimum", "maximum"},
            optional={"enum"},
            path=path,
        )
        minimum = _number(raw["minimum"], f"{path}.minimum")
        maximum = _number(raw["maximum"], f"{path}.maximum")
        if schema_type == "integer" and (
            not isinstance(minimum, int)
            or isinstance(minimum, bool)
            or not isinstance(maximum, int)
            or isinstance(maximum, bool)
        ):
            raise CapabilityManifestError(
                f"{path}.minimum and maximum must be integers for integer schemas"
            )
        if minimum > maximum:
            raise CapabilityManifestError(f"{path}.minimum must not exceed maximum")
        normalized = {"type": schema_type, "minimum": minimum, "maximum": maximum}
        if "enum" in raw:
            values = _normalize_enum(raw["enum"], path=path, expected_type=schema_type)
            for item in values:
                if item < minimum or item > maximum:
                    raise CapabilityManifestError(
                        f"{path}.enum value violates numeric bounds"
                    )
            normalized["enum"] = values
        return normalized

    if schema_type == "boolean":
        _require_exact_fields(raw, required={"type"}, optional={"enum"}, path=path)
        normalized = {"type": "boolean"}
        if "enum" in raw:
            normalized["enum"] = _normalize_enum(
                raw["enum"], path=path, expected_type="boolean"
            )
        return normalized

    _require_exact_fields(raw, required={"type"}, optional=set(), path=path)
    return {"type": "null"}


def _normalize_resource(value: Any, *, path: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CapabilityManifestError(f"{path} must be an object")
    raw = dict(value)
    _require_exact_fields(raw, required={"type", "selectors"}, optional=set(), path=path)
    resource_type = _required_text(raw["type"], f"{path}.type", _RESOURCE_TYPE_RE)
    selectors = raw["selectors"]
    if not isinstance(selectors, list) or not selectors:
        raise CapabilityManifestError(f"{path}.selectors must be a non-empty array")
    if len(selectors) > MAX_SELECTORS_PER_ACTION:
        raise CapabilityManifestError(
            f"{path}.selectors exceeds {MAX_SELECTORS_PER_ACTION} entries"
        )
    normalized: list[str] = []
    seen: set[str] = set()
    for index, selector in enumerate(selectors):
        canonical = _required_text(selector, f"{path}.selectors[{index}]", _SELECTOR_RE)
        if "*" in canonical or "?" in canonical or "[" in canonical or "]" in canonical:
            raise CapabilityManifestError(
                f"{path}.selectors[{index}] must be an exact selector, not a wildcard/glob"
            )
        if canonical in seen:
            raise CapabilityManifestError(f"{path}.selectors contains a duplicate selector")
        seen.add(canonical)
        normalized.append(canonical)
    return {"type": resource_type, "selectors": sorted(normalized)}


def _normalize_action(value: Any, *, index: int) -> dict[str, Any]:
    path = f"actions[{index}]"
    if not isinstance(value, Mapping):
        raise CapabilityManifestError(f"{path} must be an object")
    raw = dict(value)
    _require_exact_fields(
        raw,
        required={"action", "resource", "arguments", "security_properties"},
        optional=set(),
        path=path,
    )
    action = _required_text(raw["action"], f"{path}.action", _ACTION_RE)
    properties = raw["security_properties"]
    if not isinstance(properties, list) or not properties:
        raise CapabilityManifestError(f"{path}.security_properties must be a non-empty array")
    normalized_properties: list[str] = []
    seen_properties: set[str] = set()
    for prop in properties:
        if not isinstance(prop, str):
            raise CapabilityManifestError(
                f"{path}.security_properties entries must be strings"
            )
        if prop in seen_properties:
            raise CapabilityManifestError(f"{path}.security_properties contains duplicates")
        seen_properties.add(prop)
        if prop not in SUPPORTED_SECURITY_PROPERTIES:
            raise CapabilityManifestError(
                f"{path}.security_properties contains unsupported property: {prop!r}"
            )
        normalized_properties.append(prop)
    arguments = _normalize_argument_schema(raw["arguments"], path=f"{path}.arguments")
    if arguments["type"] != "object":
        raise CapabilityManifestError(f"{path}.arguments root type must be object")
    return {
        "action": action,
        "resource": _normalize_resource(raw["resource"], path=f"{path}.resource"),
        "arguments": arguments,
        "security_properties": sorted(normalized_properties),
    }


@dataclass(frozen=True)
class CapabilityManifest:
    schema: str
    manifest_version: int
    application_id: str
    skill_id: str
    actions_json: str
    display_json: str | None
    canonical_hash: str
    security_hash: str

    @classmethod
    def create(cls, value: Mapping[str, Any]) -> "CapabilityManifest":
        if not isinstance(value, Mapping):
            raise CapabilityManifestError("capability manifest must be an object")
        raw = dict(value)
        _require_exact_fields(
            raw,
            required={"schema", "manifest_version", "application_id", "skill_id", "actions"},
            optional={"display"},
            path="manifest",
        )
        schema = raw["schema"]
        version = raw["manifest_version"]
        if (
            schema != CAPABILITY_MANIFEST_SCHEMA
            or isinstance(version, bool)
            or not isinstance(version, int)
            or version != CAPABILITY_MANIFEST_VERSION
        ):
            raise UnsupportedCapabilityManifestVersion(
                f"unsupported capability manifest schema/version: {schema!r}/{version!r}"
            )
        application_id = _required_text(raw["application_id"], "application_id", _ID_RE)
        skill_id = _required_text(raw["skill_id"], "skill_id", _ID_RE)
        actions = raw["actions"]
        if not isinstance(actions, list) or not actions:
            raise CapabilityManifestError("actions must be a non-empty array")
        if len(actions) > MAX_ACTIONS:
            raise CapabilityManifestError(f"actions exceeds maximum {MAX_ACTIONS}")
        normalized_actions = [_normalize_action(action, index=i) for i, action in enumerate(actions)]
        action_ids = [action["action"] for action in normalized_actions]
        if len(action_ids) != len(set(action_ids)):
            raise CapabilityManifestError("actions contains duplicate action identities")
        normalized_actions.sort(key=lambda action: action["action"])
        display = _normalize_display(raw.get("display"))

        security_material = {
            "schema": schema,
            "manifest_version": version,
            "application_id": application_id,
            "skill_id": skill_id,
            "actions": normalized_actions,
        }
        full_material = dict(security_material)
        if display is not None:
            full_material["display"] = display

        canonical = _canonical_json(full_material)
        security_canonical = _canonical_json(security_material)
        return cls(
            schema=schema,
            manifest_version=version,
            application_id=application_id,
            skill_id=skill_id,
            actions_json=_canonical_json(normalized_actions),
            display_json=None if display is None else _canonical_json(display),
            canonical_hash="sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest(),
            security_hash="sha256:"
            + hashlib.sha256(security_canonical.encode("utf-8")).hexdigest(),
        )

    @classmethod
    def from_json(cls, text: str, *, require_canonical: bool = False) -> "CapabilityManifest":
        if not isinstance(text, str) or not text:
            raise CapabilityManifestError("manifest JSON must be a non-empty string")
        try:
            parsed = json.loads(text, object_pairs_hook=_strict_object_pairs)
        except DuplicateManifestKey:
            raise
        except json.JSONDecodeError as exc:
            raise CapabilityManifestError("manifest JSON is invalid") from exc
        manifest = cls.create(parsed)
        if require_canonical and manifest.canonical_json() != text:
            raise CapabilityManifestError("persisted manifest JSON is not canonical")
        return manifest

    @property
    def actions(self) -> list[dict[str, Any]]:
        return json.loads(self.actions_json)

    @property
    def display(self) -> dict[str, str] | None:
        return None if self.display_json is None else json.loads(self.display_json)

    def security_material(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "manifest_version": self.manifest_version,
            "application_id": self.application_id,
            "skill_id": self.skill_id,
            "actions": self.actions,
        }

    def canonical_material(self) -> dict[str, Any]:
        material = self.security_material()
        if self.display is not None:
            material["display"] = self.display
        return material

    def canonical_json(self) -> str:
        return _canonical_json(self.canonical_material())

    def action(self, action_id: str) -> dict[str, Any] | None:
        for action in self.actions:
            if action["action"] == action_id:
                return action
        return None
