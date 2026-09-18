from __future__ import annotations

import json
import re
from typing import Any, Mapping

from .external_consumer import (
    EXTERNAL_CONSUMER_REQUEST_SCHEMA,
    EXTERNAL_CONSUMER_RESPONSE_SCHEMA,
    ExternalConsumerProtocolError,
    ExternalConsumerRequest,
)

NATIVE_LOCAL_CONSUMER_CONTRACT_SCHEMA = "lac.native-local-consumer-contract/v1"
NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA = "lac.native-local-consumer-result/v1"
NATIVE_LOCAL_CONSUMER_CONTINUATION_STATUS_SCHEMA = (
    "lac.native-local-consumer-continuation-status/v1"
)
NATIVE_LOCAL_CONSUMER_RESUME_SCHEMA = "lac.native-local-consumer-resume/v1"
NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA = (
    "lac.native-local-consumer-resume-result/v1"
)

# PI003 deliberately reuses the accepted B003 authority request schema. A new request schema
# would duplicate rather than stabilize the already-proven controller boundary.
NATIVE_LOCAL_CONSUMER_REQUEST_SCHEMA = EXTERNAL_CONSUMER_REQUEST_SCHEMA

_LEGACY_D001_STATUS_SCHEMA = "lac.pi-v1-workflow-continuation-status/v1"
_LEGACY_D001_WORKFLOW_OUTCOME_SCHEMA = "lac.pi-v1-workflow-outcome/v1"

_RESULT_FIELDS = {
    "schema",
    "request_id",
    "canonical_request_hash",
    "authority_outcome",
    "execution_state",
    "reason",
    "decision_id",
    "result",
    "receipt",
    "replayed",
    "permission_configuration",
    "workflow_continuation",
}
_RAW_EXTERNAL_RESULT_FIELDS = {
    "schema",
    "request_id",
    "canonical_request_hash",
    "authority_outcome",
    "execution_state",
    "reason",
    "decision_id",
    "result",
    "receipt",
    "replayed",
}
_CONTINUATION_STATUS_FIELDS = {
    "schema",
    "continuation_id",
    "original_request_id",
    "pending_id",
    "state",
    "expires_at_utc",
    "resume_budget_used",
    "fresh_request_id",
    "fresh_decision_id",
    "resolution_baseline_revision",
    "outcome",
    "owner_resolution",
}
_RESUME_FIELDS = {"schema", "continuation_id", "expected_request"}
_RESUME_RESULT_FIELDS = {
    "schema",
    "ok",
    "kind",
    "workflow_continuation",
    "result",
}
_ALLOWED_AUTHORITY = {"ALLOW", "REQUIRE_APPROVAL", "DENY"}
_ALLOWED_EXECUTION = {
    "SUCCEEDED",
    "FAILED",
    "PENDING_APPROVAL",
    "DENIED",
    "REJECTED",
    "NOT_EXECUTED",
}
_ALLOWED_CONTINUATION_STATES = {
    "WAITING_PERMISSION",
    "FRESH_REQUEST_CLAIMED",
    "PENDING_APPROVAL",
    "COMPLETED",
    "CLOSED_NONAUTH",
    "EXPIRED",
}
_CREDENTIAL_KEY = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|credential|authorization|cookie|private[_-]?key)",
    re.IGNORECASE,
)


class NativeLocalConsumerContractError(ValueError):
    """Fail-closed native local-consumer contract error."""


def _text(value: Any, field: str, *, maximum: int = 4096) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise NativeLocalConsumerContractError(f"{field} must be non-empty trimmed text")
    if len(value) > maximum:
        raise NativeLocalConsumerContractError(f"{field} exceeds maximum length {maximum}")
    return value


def _canonical_json_value(value: Any, field: str) -> Any:
    try:
        encoded = json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        return json.loads(encoded)
    except (TypeError, ValueError) as exc:
        raise NativeLocalConsumerContractError(
            f"{field} is outside the canonical JSON data model"
        ) from exc


def _public_output(value: Any, *, path: str = "$") -> Any:
    value = _canonical_json_value(value, path)
    if isinstance(value, list):
        return [_public_output(item, path=f"{path}[]") for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if _CREDENTIAL_KEY.search(key):
                raise NativeLocalConsumerContractError(
                    f"credential-shaped public output is prohibited at {path}.{key}"
                )
            result[key] = _public_output(item, path=f"{path}.{key}")
        return result
    return value


def validate_native_request(material: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the exact accepted B003 request as the PI003 native request contract."""

    try:
        parsed = ExternalConsumerRequest.parse(material)
    except ExternalConsumerProtocolError:
        raise
    return {
        "schema": NATIVE_LOCAL_CONSUMER_REQUEST_SCHEMA,
        "request_id": parsed.request_id,
        "run_id": parsed.run_id,
        "action": parsed.action,
        "resource": parsed.resource,
        "arguments": _canonical_json_value(parsed.arguments, "arguments"),
        "idempotency_key": parsed.idempotency_key,
    }


def normalize_permission_configuration(material: Any) -> dict[str, Any]:
    if material is None:
        return {"required": False}
    if not isinstance(material, Mapping):
        raise NativeLocalConsumerContractError(
            "permission_configuration must be an object"
        )
    material = dict(material)
    required = material.get("required")
    if not isinstance(required, bool):
        raise NativeLocalConsumerContractError(
            "permission_configuration.required must be boolean"
        )
    if required:
        if set(material) != {"required", "pending_id", "reason"}:
            raise NativeLocalConsumerContractError(
                "required permission configuration fields are invalid"
            )
        return {
            "required": True,
            "pending_id": _text(material["pending_id"], "pending_id"),
            "reason": _text(material["reason"], "permission reason", maximum=256),
        }
    if set(material) not in ({"required"}, {"required", "reason"}):
        raise NativeLocalConsumerContractError(
            "non-required permission configuration fields are invalid"
        )
    result: dict[str, Any] = {"required": False}
    if "reason" in material:
        result["reason"] = _text(
            material["reason"], "permission reason", maximum=256
        )
    return result


def normalize_continuation_status(material: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(material, Mapping):
        raise NativeLocalConsumerContractError("continuation status must be an object")
    material = dict(material)
    if set(material) != _CONTINUATION_STATUS_FIELDS:
        extra = sorted(set(material) - _CONTINUATION_STATUS_FIELDS)
        missing = sorted(_CONTINUATION_STATUS_FIELDS - set(material))
        raise NativeLocalConsumerContractError(
            f"continuation status fields invalid; missing={missing} extra={extra}"
        )
    if material.get("schema") not in {
        NATIVE_LOCAL_CONSUMER_CONTINUATION_STATUS_SCHEMA,
        _LEGACY_D001_STATUS_SCHEMA,
    }:
        raise NativeLocalConsumerContractError(
            "unsupported continuation status schema"
        )
    state = _text(material["state"], "continuation state", maximum=64)
    if state not in _ALLOWED_CONTINUATION_STATES:
        raise NativeLocalConsumerContractError("unsupported continuation state")
    budget = material["resume_budget_used"]
    if isinstance(budget, bool) or not isinstance(budget, int) or budget not in (0, 1):
        raise NativeLocalConsumerContractError("continuation resume budget is invalid")
    fresh_request_id = material["fresh_request_id"]
    if fresh_request_id is not None:
        fresh_request_id = _text(fresh_request_id, "fresh_request_id")
    fresh_decision_id = material["fresh_decision_id"]
    if fresh_decision_id is not None:
        fresh_decision_id = _text(fresh_decision_id, "fresh_decision_id")
    if budget == 0 and (fresh_request_id is not None or fresh_decision_id is not None):
        raise NativeLocalConsumerContractError(
            "unused continuation budget cannot expose fresh request state"
        )
    if state in {"FRESH_REQUEST_CLAIMED", "PENDING_APPROVAL", "COMPLETED"} and budget != 1:
        raise NativeLocalConsumerContractError(
            "fresh-request continuation state requires consumed one-shot budget"
        )
    if state in {"CLOSED_NONAUTH", "EXPIRED"} and budget != 0:
        raise NativeLocalConsumerContractError(
            "non-authorizing continuation closure cannot consume fresh request budget"
        )
    baseline = material["resolution_baseline_revision"]
    if isinstance(baseline, bool) or not isinstance(baseline, int) or baseline < 0:
        raise NativeLocalConsumerContractError(
            "resolution_baseline_revision is invalid"
        )
    owner = material["owner_resolution"]
    if owner is not None:
        if not isinstance(owner, Mapping):
            raise NativeLocalConsumerContractError("owner_resolution must be an object")
        owner = dict(owner)
        if set(owner) != {"revision", "status", "resolution", "resolved_at_utc"}:
            raise NativeLocalConsumerContractError("owner_resolution fields are invalid")
        revision = owner["revision"]
        if isinstance(revision, bool) or not isinstance(revision, int) or revision <= baseline:
            raise NativeLocalConsumerContractError("owner resolution revision is stale or invalid")
        owner = {
            "revision": revision,
            "status": _text(owner["status"], "owner resolution status", maximum=64),
            "resolution": _text(owner["resolution"], "owner resolution", maximum=64),
            "resolved_at_utc": _text(owner["resolved_at_utc"], "resolved_at_utc", maximum=128),
        }
    outcome = material["outcome"]
    if outcome is not None:
        outcome = _text(outcome, "continuation outcome", maximum=512)
    return {
        "schema": NATIVE_LOCAL_CONSUMER_CONTINUATION_STATUS_SCHEMA,
        "continuation_id": _text(material["continuation_id"], "continuation_id"),
        "original_request_id": _text(material["original_request_id"], "original_request_id"),
        "pending_id": _text(material["pending_id"], "pending_id"),
        "state": state,
        "expires_at_utc": _text(material["expires_at_utc"], "expires_at_utc", maximum=128),
        "resume_budget_used": budget,
        "fresh_request_id": fresh_request_id,
        "fresh_decision_id": fresh_decision_id,
        "resolution_baseline_revision": baseline,
        "outcome": outcome,
        "owner_resolution": owner,
    }


def normalize_native_result(material: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(material, Mapping):
        raise NativeLocalConsumerContractError("native result must be an object")
    material = dict(material)
    schema = material.get("schema")
    if schema == EXTERNAL_CONSUMER_RESPONSE_SCHEMA:
        allowed = _RAW_EXTERNAL_RESULT_FIELDS | {
            "permission_configuration",
            "workflow_continuation",
        }
        if set(material) - allowed:
            raise NativeLocalConsumerContractError(
                "external runtime result contains unsupported extension fields"
            )
        missing = _RAW_EXTERNAL_RESULT_FIELDS - set(material)
        if missing:
            raise NativeLocalConsumerContractError(
                f"external runtime result missing fields: {sorted(missing)}"
            )
    elif schema in {NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA, _LEGACY_D001_WORKFLOW_OUTCOME_SCHEMA}:
        if set(material) != _RESULT_FIELDS:
            extra = sorted(set(material) - _RESULT_FIELDS)
            missing = sorted(_RESULT_FIELDS - set(material))
            raise NativeLocalConsumerContractError(
                f"native result fields invalid; missing={missing} extra={extra}"
            )
    else:
        raise NativeLocalConsumerContractError("unsupported native result schema")

    authority = _text(material["authority_outcome"], "authority_outcome", maximum=64)
    if authority not in _ALLOWED_AUTHORITY:
        raise NativeLocalConsumerContractError("unsupported authority outcome")
    execution = _text(material["execution_state"], "execution_state", maximum=64)
    if execution not in _ALLOWED_EXECUTION:
        raise NativeLocalConsumerContractError("unsupported execution state")
    decision_id = material["decision_id"]
    if decision_id is not None:
        decision_id = _text(decision_id, "decision_id")
    receipt = material["receipt"]
    if receipt is not None:
        if not isinstance(receipt, Mapping):
            raise NativeLocalConsumerContractError("receipt must be an object or null")
        receipt = _public_output(dict(receipt), path="$.receipt")
    result = material["result"]
    if result is not None:
        result = _public_output(result, path="$.result")
    replayed = material["replayed"]
    if not isinstance(replayed, bool):
        raise NativeLocalConsumerContractError("replayed must be boolean")
    permission = normalize_permission_configuration(
        material.get("permission_configuration")
    )
    continuation = material.get("workflow_continuation")
    if continuation is not None:
        continuation = normalize_continuation_status(continuation)

    return {
        "schema": NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA,
        "request_id": _text(material["request_id"], "request_id"),
        "canonical_request_hash": _text(
            material["canonical_request_hash"], "canonical_request_hash"
        ),
        "authority_outcome": authority,
        "execution_state": execution,
        "reason": _text(material["reason"], "reason", maximum=512),
        "decision_id": decision_id,
        "result": result,
        "receipt": receipt,
        "replayed": replayed,
        "permission_configuration": permission,
        "workflow_continuation": continuation,
    }


def parse_native_resume_request(material: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(material, Mapping) or set(material) != _RESUME_FIELDS:
        raise NativeLocalConsumerContractError(
            "resume request fields must be exactly schema, continuation_id, expected_request"
        )
    if material.get("schema") != NATIVE_LOCAL_CONSUMER_RESUME_SCHEMA:
        raise NativeLocalConsumerContractError("unsupported resume request schema")
    expected = material["expected_request"]
    if expected is not None:
        if not isinstance(expected, Mapping):
            raise NativeLocalConsumerContractError(
                "expected_request must be an object or null"
            )
        expected = validate_native_request(expected)
    return {
        "schema": NATIVE_LOCAL_CONSUMER_RESUME_SCHEMA,
        "continuation_id": _text(material["continuation_id"], "continuation_id"),
        "expected_request": expected,
    }


def normalize_resume_result(material: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(material, Mapping):
        raise NativeLocalConsumerContractError("resume result must be an object")
    material = dict(material)
    if material.get("schema") == NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA:
        if set(material) != _RESUME_RESULT_FIELDS:
            raise NativeLocalConsumerContractError("resume result fields are invalid")
    else:
        # Legacy D001/Pi return shape is accepted only for migration/conformance normalization.
        if set(material) != {"ok", "kind", "workflow_continuation", "result"}:
            raise NativeLocalConsumerContractError("legacy resume result fields are invalid")
    if material.get("ok") is not True:
        raise NativeLocalConsumerContractError("resume result must represent a successful host operation")
    status = normalize_continuation_status(material["workflow_continuation"])
    result = material["result"]
    if result is not None:
        result = normalize_native_result(result)
    return {
        "schema": NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA,
        "ok": True,
        "kind": _text(material["kind"], "resume kind", maximum=64),
        "workflow_continuation": status,
        "result": result,
    }


NATIVE_LOCAL_CONSUMER_CONTRACT = {
    "schema": NATIVE_LOCAL_CONSUMER_CONTRACT_SCHEMA,
    "request_schema": NATIVE_LOCAL_CONSUMER_REQUEST_SCHEMA,
    "result_schema": NATIVE_LOCAL_CONSUMER_RESULT_SCHEMA,
    "continuation_status_schema": NATIVE_LOCAL_CONSUMER_CONTINUATION_STATUS_SCHEMA,
    "resume_schema": NATIVE_LOCAL_CONSUMER_RESUME_SCHEMA,
    "resume_result_schema": NATIVE_LOCAL_CONSUMER_RESUME_RESULT_SCHEMA,
    "authority_outcomes": sorted(_ALLOWED_AUTHORITY),
}
