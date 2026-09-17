from __future__ import annotations

import hashlib
import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from packages.capabilities import (
    CAPABILITY_MANIFEST_VERSION,
    CapabilityManifest,
    CapabilityManifestError,
    CapabilityRegistry,
    CapabilityRequestContext,
)
from packages.core import ApprovalDecision, EffectRequest, EffectRequestError, canonical_json
from packages.dispatcher import (
    DispatchApprovalRequired,
    DispatchCapabilityDenied,
    DispatchDenied,
    DispatchDuplicateEffect,
    Dispatcher,
    EffectAdapter,
)
from packages.policy import StandingPolicyDecisionProvider
from packages.state import (
    ApprovalRepository,
    EffectReceiptRepository,
    EffectRequestRepository,
    SQLiteStateStore,
    StateStoreError,
)

EXTERNAL_CONSUMER_REQUEST_SCHEMA = "lac.external-consumer-request/v1"
EXTERNAL_CONSUMER_RESPONSE_SCHEMA = "lac.external-consumer-response/v1"
EXTERNAL_CONSUMER_BINDING_SCHEMA = "lac.external-consumer-request-binding/v1"
_EXTERNAL_CONSUMER_BINDING_KEY_PREFIX = "external-consumer/request-binding/v1/"

_ALLOWED_REQUEST_FIELDS = {
    "schema",
    "request_id",
    "run_id",
    "action",
    "resource",
    "arguments",
    "idempotency_key",
}

_FORBIDDEN_PUBLIC_KEY = re.compile(
    r"(password|passwd|secret|token|api[_-]?key|credential|authorization|cookie|private[_-]?key)",
    re.IGNORECASE,
)


class ExternalConsumerError(ValueError):
    """Base fail-closed external-consumer boundary error."""


class ExternalConsumerProtocolError(ExternalConsumerError):
    """Consumer request material is malformed or attempts to cross an authority boundary."""


class ExternalConsumerConfigurationError(ExternalConsumerError):
    """Controller-side consumer binding is invalid or inconsistent with canonical state."""


class ExternalConsumerRuntimeError(ExternalConsumerError):
    """Controller runtime state failed closed while serving the external consumer."""


def _required_text(value: Any, field: str, *, maximum: int = 512) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise ExternalConsumerProtocolError(f"{field} must be a non-empty trimmed string")
    if len(value) > maximum:
        raise ExternalConsumerProtocolError(f"{field} exceeds maximum length {maximum}")
    return value


def _rfc3339(value: datetime) -> str:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ExternalConsumerConfigurationError("trusted runtime clock must be timezone-aware")
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _json_object(value: Any, field: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ExternalConsumerProtocolError(f"{field} must be a JSON object")
    try:
        normalized = json.loads(canonical_json(dict(value)))
    except Exception as exc:
        raise ExternalConsumerProtocolError(f"{field} is outside the canonical JSON data model") from exc
    if not isinstance(normalized, dict):
        raise ExternalConsumerProtocolError(f"{field} must be a JSON object")
    return normalized


def _public_safe(value: Any, *, path: str = "$") -> Any:
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    if isinstance(value, list):
        return [_public_safe(item, path=f"{path}[]") for item in value]
    if isinstance(value, dict):
        result: dict[str, Any] = {}
        for key, item in value.items():
            if not isinstance(key, str):
                raise ExternalConsumerRuntimeError("runtime result contains a non-string key")
            if _FORBIDDEN_PUBLIC_KEY.search(key):
                raise ExternalConsumerRuntimeError(
                    f"runtime result contains credential-shaped material at {path}.{key}"
                )
            result[key] = _public_safe(item, path=f"{path}.{key}")
        return result
    raise ExternalConsumerRuntimeError("runtime result is outside the public JSON data model")


def _result_material(result: Any) -> Any:
    if hasattr(result, "to_record") and callable(getattr(result, "to_record")):
        result = result.to_record()
    if isinstance(result, Mapping):
        result = dict(result)
    try:
        normalized = json.loads(canonical_json(result))
    except Exception as exc:
        raise ExternalConsumerRuntimeError("adapter result is not canonical public JSON") from exc
    return _public_safe(normalized)


def _receipt_projection(receipt: Any) -> dict[str, Any]:
    record = receipt.to_record()
    allowed = {
        "schema",
        "receipt_id",
        "request_id",
        "canonical_request_hash",
        "idempotency_key",
        "approval_id",
        "adapter_id",
        "lease_id",
        "input_hash",
        "started_at",
        "completed_at",
        "outcome",
        "result_hash",
        "upstream_reference",
    }
    projected = {key: record.get(key) for key in allowed}
    return _public_safe(projected)


@dataclass(frozen=True)
class ExternalConsumerDeclaration:
    application_id: str
    skill_id: str
    manifest_version: int
    manifest_hash: str
    manifest_json: str

    @classmethod
    def create(cls, manifest_material: Mapping[str, Any]) -> "ExternalConsumerDeclaration":
        try:
            manifest = CapabilityManifest.create(dict(manifest_material))
        except (CapabilityManifestError, TypeError) as exc:
            raise ExternalConsumerProtocolError("consumer declaration is not a valid capability manifest") from exc
        return cls(
            application_id=manifest.application_id,
            skill_id=manifest.skill_id,
            manifest_version=manifest.manifest_version,
            manifest_hash=manifest.canonical_hash,
            manifest_json=manifest.canonical_json(),
        )

    @property
    def manifest(self) -> CapabilityManifest:
        try:
            return CapabilityManifest.from_json(self.manifest_json, require_canonical=True)
        except CapabilityManifestError as exc:
            raise ExternalConsumerConfigurationError("consumer declaration lost canonical integrity") from exc


@dataclass(frozen=True)
class ExternalConsumerRequest:
    request_id: str
    run_id: str
    action: str
    resource: str
    arguments: dict[str, Any]
    idempotency_key: str

    @classmethod
    def parse(cls, material: Mapping[str, Any]) -> "ExternalConsumerRequest":
        if not isinstance(material, Mapping):
            raise ExternalConsumerProtocolError("external-consumer request must be a JSON object")
        observed = set(material)
        if observed != _ALLOWED_REQUEST_FIELDS:
            extra = sorted(observed - _ALLOWED_REQUEST_FIELDS)
            missing = sorted(_ALLOWED_REQUEST_FIELDS - observed)
            raise ExternalConsumerProtocolError(
                f"external-consumer request fields invalid; missing={missing} extra={extra}"
            )
        if material.get("schema") != EXTERNAL_CONSUMER_REQUEST_SCHEMA:
            raise ExternalConsumerProtocolError("unsupported external-consumer request schema")
        return cls(
            request_id=_required_text(material["request_id"], "request_id"),
            run_id=_required_text(material["run_id"], "run_id"),
            action=_required_text(material["action"], "action"),
            resource=_required_text(material["resource"], "resource"),
            arguments=_json_object(material["arguments"], "arguments"),
            idempotency_key=_required_text(material["idempotency_key"], "idempotency_key"),
        )


class ExternalConsumerRuntime:
    """Controller-owned runtime boundary for one bound external application/skill.

    The external consumer supplies only typed request material. Principal/agent identity,
    application/skill identity, capability revision, policy, exact approvals, leases,
    executor identity, registry mutation and administration remain controller-owned.
    """

    def __init__(
        self,
        *,
        store: SQLiteStateStore,
        declaration: ExternalConsumerDeclaration,
        principal_id: str,
        agent_id: str,
        application_id: str,
        skill_id: str,
        adapter: EffectAdapter,
        clock: Callable[[], datetime] | None = None,
        request_ttl_seconds: int = 900,
    ) -> None:
        if not isinstance(store, SQLiteStateStore):
            raise ExternalConsumerConfigurationError("store must be SQLiteStateStore")
        if not isinstance(declaration, ExternalConsumerDeclaration):
            raise ExternalConsumerConfigurationError("declaration must be ExternalConsumerDeclaration")
        if not isinstance(adapter, EffectAdapter):
            raise ExternalConsumerConfigurationError("adapter must implement EffectAdapter")
        if isinstance(request_ttl_seconds, bool) or not isinstance(request_ttl_seconds, int):
            raise ExternalConsumerConfigurationError("request_ttl_seconds must be an integer")
        if request_ttl_seconds < 30 or request_ttl_seconds > 3600:
            raise ExternalConsumerConfigurationError("request_ttl_seconds must be between 30 and 3600")
        self._store = store
        self._declaration = declaration
        self._principal_id = _required_text(principal_id, "principal_id")
        self._agent_id = _required_text(agent_id, "agent_id")
        self._application_id = _required_text(application_id, "application_id")
        self._skill_id = _required_text(skill_id, "skill_id")
        if (
            declaration.application_id != self._application_id
            or declaration.skill_id != self._skill_id
        ):
            raise ExternalConsumerConfigurationError(
                "consumer declaration application/skill identity does not match "
                "controller-owned binding"
            )
        self._adapter = adapter
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._request_ttl_seconds = request_ttl_seconds
        self._dispatcher = Dispatcher(
            store=store,
            policy_provider=StandingPolicyDecisionProvider(store),
            clock=self._clock,
        )

    @property
    def application_id(self) -> str:
        return self._application_id

    @property
    def skill_id(self) -> str:
        return self._skill_id

    @property
    def declared_manifest_hash(self) -> str:
        return self._declaration.manifest_hash

    def _new_internal_id(self, kind: str, request: EffectRequest) -> str:
        entropy = uuid.uuid4().hex
        digest = hashlib.sha256(
            f"{kind}\0{request.request_id}\0{request.canonical_hash}\0{entropy}".encode("utf-8")
        ).hexdigest()
        return f"{kind}:external-consumer:{digest}"

    def _request_binding_key(self, request_id: str) -> str:
        digest = hashlib.sha256(request_id.encode("utf-8")).hexdigest()
        return _EXTERNAL_CONSUMER_BINDING_KEY_PREFIX + digest

    def _expected_request_binding(self, request_id: str) -> dict[str, str]:
        return {
            "schema": EXTERNAL_CONSUMER_BINDING_SCHEMA,
            "request_id": request_id,
            "principal_id": self._principal_id,
            "agent_id": self._agent_id,
            "application_id": self._application_id,
            "skill_id": self._skill_id,
        }

    def _decode_request_binding(self, raw: Any, *, request_id: str) -> dict[str, str]:
        if not isinstance(raw, str):
            raise ExternalConsumerRuntimeError("external-consumer request binding is malformed")
        try:
            observed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ExternalConsumerRuntimeError(
                "external-consumer request binding is malformed"
            ) from exc
        required = {
            "schema",
            "request_id",
            "principal_id",
            "agent_id",
            "application_id",
            "skill_id",
        }
        if not isinstance(observed, dict) or set(observed) != required:
            raise ExternalConsumerRuntimeError(
                "external-consumer request binding fields are malformed"
            )
        if observed.get("schema") != EXTERNAL_CONSUMER_BINDING_SCHEMA:
            raise ExternalConsumerRuntimeError(
                "external-consumer request binding schema is unsupported"
            )
        try:
            if canonical_json(observed) != raw:
                raise ExternalConsumerRuntimeError(
                    "external-consumer request binding is not canonical"
                )
        except EffectRequestError as exc:
            raise ExternalConsumerRuntimeError(
                "external-consumer request binding is outside canonical JSON"
            ) from exc
        for field in (
            "request_id",
            "principal_id",
            "agent_id",
            "application_id",
            "skill_id",
        ):
            value = observed.get(field)
            if not isinstance(value, str) or not value or value != value.strip():
                raise ExternalConsumerRuntimeError(
                    f"external-consumer request binding {field} is malformed"
                )
        if observed["request_id"] != request_id:
            raise ExternalConsumerRuntimeError(
                "external-consumer request binding key does not bind request_id"
            )
        return observed

    def _read_request_binding(self, request_id: str) -> dict[str, str] | None:
        key = self._request_binding_key(request_id)
        try:
            row = self._store._conn.execute(
                "SELECT value_json FROM system_state WHERE key = ?",
                (key,),
            ).fetchone()
        except Exception as exc:
            raise ExternalConsumerRuntimeError(
                "external-consumer request binding lookup failed closed"
            ) from exc
        if row is None:
            return None
        return self._decode_request_binding(row["value_json"], request_id=request_id)

    def _require_request_binding(self, request_id: str) -> None:
        observed = self._read_request_binding(request_id)
        if observed is None:
            raise ExternalConsumerRuntimeError(
                "durable request lacks four-dimensional external-consumer binding"
            )
        if observed != self._expected_request_binding(request_id):
            raise ExternalConsumerProtocolError(
                "request_id is outside this consumer binding"
            )

    def _claim_new_request_binding(self, request_id: str) -> None:
        key = self._request_binding_key(request_id)
        expected = self._expected_request_binding(request_id)
        encoded = canonical_json(expected)
        try:
            with self._store.transaction() as conn:
                row = conn.execute(
                    "SELECT value_json FROM system_state WHERE key = ?",
                    (key,),
                ).fetchone()
                if row is None:
                    conn.execute(
                        "INSERT INTO system_state(key, value_json, updated_at_utc) VALUES (?, ?, ?)",
                        (key, encoded, self._store._utc_now()),
                    )
                    return
                observed = self._decode_request_binding(
                    row["value_json"],
                    request_id=request_id,
                )
                if observed != expected:
                    raise ExternalConsumerProtocolError(
                        "request_id is outside this consumer binding"
                    )
        except ExternalConsumerError:
            raise
        except Exception as exc:
            raise ExternalConsumerRuntimeError(
                "external-consumer request binding persistence failed closed"
            ) from exc

    def _assert_existing_request_material(
        self,
        existing: EffectRequest,
        incoming: ExternalConsumerRequest,
    ) -> None:
        if (
            existing.principal_id != self._principal_id
            or existing.agent_id != self._agent_id
            or existing.run_id != incoming.run_id
            or existing.action != incoming.action
            or existing.resource != incoming.resource
            or existing.arguments != incoming.arguments
            or existing.idempotency_key != incoming.idempotency_key
        ):
            raise ExternalConsumerProtocolError(
                "request_id is already bound to different canonical controller-owned material"
            )

    def _load_or_create_request(self, incoming: ExternalConsumerRequest) -> EffectRequest:
        repository = EffectRequestRepository(self._store)
        existing = repository.get(incoming.request_id)
        if existing is not None:
            self._require_request_binding(existing.request_id)
            self._assert_existing_request_material(existing, incoming)
            return existing

        self._claim_new_request_binding(incoming.request_id)

        existing = repository.get(incoming.request_id)
        if existing is not None:
            self._require_request_binding(existing.request_id)
            self._assert_existing_request_material(existing, incoming)
            return existing

        try:
            now = self._clock()
            created_at = _rfc3339(now)
            expires_at = _rfc3339(now + timedelta(seconds=self._request_ttl_seconds))
            request = EffectRequest.create(
                request_id=incoming.request_id,
                run_id=incoming.run_id,
                principal_id=self._principal_id,
                agent_id=self._agent_id,
                action=incoming.action,
                resource=incoming.resource,
                arguments=incoming.arguments,
                idempotency_key=incoming.idempotency_key,
                created_at=created_at,
                expires_at=expires_at,
            )
            return repository.put(request)
        except (EffectRequestError, StateStoreError) as exc:
            raise ExternalConsumerRuntimeError("canonical request persistence failed closed") from exc

    def _capability_context(self, request: EffectRequest) -> CapabilityRequestContext:
        registry = CapabilityRegistry(self._store)
        try:
            registration = registry.get_latest(self.application_id, self.skill_id)
        except Exception as exc:
            raise ExternalConsumerRuntimeError("capability registry failed closed") from exc
        declared_manifest = self._declaration.manifest
        if registration is None:
            # This intentionally enters P002 as an unknown capability/revision. The declaration
            # is descriptive only and does not create canonical registration or authority.
            revision = 1
            manifest_version = declared_manifest.manifest_version
            action = declared_manifest.action(request.action)
            resource_type = "unknown" if action is None else str(action["resource"]["type"])
            return CapabilityRequestContext(
                application_id=self.application_id,
                skill_id=self.skill_id,
                capability_revision=revision,
                manifest_version=manifest_version,
                resource_type=resource_type,
            )
        if registration.manifest_hash != self._declaration.manifest_hash:
            raise ExternalConsumerConfigurationError(
                "consumer declaration does not match the current owner-registered capability revision"
            )
        manifest = registration.manifest
        action = manifest.action(request.action)
        resource_type = "unknown" if action is None else str(action["resource"]["type"])
        return CapabilityRequestContext(
            application_id=self.application_id,
            skill_id=self.skill_id,
            capability_revision=registration.revision,
            manifest_version=manifest.manifest_version,
            resource_type=resource_type,
        )

    def _approval_state(self, request: EffectRequest) -> tuple[str, str | None]:
        try:
            rows = self._store._conn.execute(
                """
                SELECT approval_id
                FROM approvals
                WHERE request_id = ? AND canonical_request_hash = ?
                ORDER BY created_at, approval_id
                """,
                (request.request_id, request.canonical_hash),
            ).fetchall()
            approvals = [ApprovalRepository(self._store).get(str(row["approval_id"])) for row in rows]
        except Exception as exc:
            raise ExternalConsumerRuntimeError("exact approval state failed closed") from exc
        approvals = [item for item in approvals if item is not None]
        if any(item.decision is ApprovalDecision.REJECT for item in approvals):
            return "REJECTED", None
        available = [
            item for item in approvals
            if item.decision is ApprovalDecision.APPROVE and item.consumed_at is None
        ]
        if len(available) > 1:
            raise ExternalConsumerRuntimeError("multiple unconsumed exact approvals fail closed")
        return ("APPROVED", available[0].approval_id) if available else ("NONE", None)

    def _response(
        self,
        request: EffectRequest,
        *,
        authority_outcome: str,
        execution_state: str,
        reason: str,
        decision_id: str | None = None,
        result: Any = None,
        receipt: dict[str, Any] | None = None,
        replayed: bool = False,
    ) -> dict[str, Any]:
        material = {
            "schema": EXTERNAL_CONSUMER_RESPONSE_SCHEMA,
            "request_id": request.request_id,
            "canonical_request_hash": request.canonical_hash,
            "authority_outcome": authority_outcome,
            "execution_state": execution_state,
            "reason": reason,
            "decision_id": decision_id,
            "result": result,
            "receipt": receipt,
            "replayed": replayed,
        }
        return _public_safe(material)

    def _terminal_receipt_response(self, request: EffectRequest, *, replayed: bool) -> dict[str, Any] | None:
        try:
            receipt = EffectReceiptRepository(self._store).get_receipt_for_request(request.request_id)
        except StateStoreError as exc:
            raise ExternalConsumerRuntimeError("terminal receipt state failed closed") from exc
        if receipt is None:
            return None
        record = receipt.to_record()
        result = json.loads(record["result_json"])
        return self._response(
            request,
            authority_outcome="ALLOW" if record["outcome"] == "SUCCEEDED" else "DENY",
            execution_state=record["outcome"],
            reason="TERMINAL_RECEIPT",
            result=_public_safe(result),
            receipt=_receipt_projection(receipt),
            replayed=replayed,
        )

    def submit(self, material: Mapping[str, Any]) -> dict[str, Any]:
        incoming = ExternalConsumerRequest.parse(material)
        request = self._load_or_create_request(incoming)

        existing = self._terminal_receipt_response(request, replayed=True)
        if existing is not None:
            return existing

        approval_state, approval_id = self._approval_state(request)
        if approval_state == "REJECTED":
            return self._response(
                request,
                authority_outcome="DENY",
                execution_state="REJECTED",
                reason="EXACT_APPROVAL_REJECTED",
            )

        try:
            context = self._capability_context(request)
        except ExternalConsumerConfigurationError:
            return self._response(
                request,
                authority_outcome="DENY",
                execution_state="DENIED",
                reason="CAPABILITY_DECLARATION_MISMATCH",
            )

        decision_id = self._new_internal_id("decision", request)
        lease_id = self._new_internal_id("lease", request)
        executor_id = f"external-consumer:{self.application_id}:{self.skill_id}"
        try:
            result = self._dispatcher.dispatch_capability(
                request,
                capability_context=context,
                adapter=self._adapter,
                decision_id=decision_id,
                lease_id=lease_id,
                executor_id=executor_id,
                approval_id=approval_id,
            )
        except DispatchApprovalRequired:
            return self._response(
                request,
                authority_outcome="REQUIRE_APPROVAL",
                execution_state="PENDING_APPROVAL",
                reason="EXACT_APPROVAL_REQUIRED",
                decision_id=decision_id,
            )
        except DispatchCapabilityDenied:
            return self._response(
                request,
                authority_outcome="DENY",
                execution_state="DENIED",
                reason="CAPABILITY_DENY",
            )
        except DispatchDenied:
            return self._response(
                request,
                authority_outcome="DENY",
                execution_state="DENIED",
                reason="POLICY_DENY",
            )
        except DispatchDuplicateEffect:
            replay = self._terminal_receipt_response(request, replayed=True)
            if replay is None:
                raise ExternalConsumerRuntimeError(
                    "duplicate effect has no terminal receipt; fail closed"
                )
            return replay
        except Exception as exc:
            raise ExternalConsumerRuntimeError("governed runtime dispatch failed closed") from exc

        try:
            receipt = EffectReceiptRepository(self._store).get_receipt_for_request(request.request_id)
        except StateStoreError as exc:
            raise ExternalConsumerRuntimeError("successful dispatch lost terminal receipt") from exc
        if receipt is None:
            raise ExternalConsumerRuntimeError("successful dispatch produced no terminal receipt")
        return self._response(
            request,
            authority_outcome="ALLOW",
            execution_state="SUCCEEDED",
            reason="AUTHORIZED_EFFECT_SUCCEEDED",
            decision_id=decision_id,
            result=_result_material(result),
            receipt=_receipt_projection(receipt),
            replayed=False,
        )

    def status(self, request_id: str) -> dict[str, Any]:
        request_id = _required_text(request_id, "request_id")
        try:
            request = EffectRequestRepository(self._store).get(request_id)
        except StateStoreError as exc:
            raise ExternalConsumerRuntimeError("request status lookup failed closed") from exc
        if request is None:
            raise ExternalConsumerProtocolError("request_id is unknown")
        if request.principal_id != self._principal_id or request.agent_id != self._agent_id:
            raise ExternalConsumerProtocolError("request_id is outside this consumer binding")
        self._require_request_binding(request.request_id)
        receipt_response = self._terminal_receipt_response(request, replayed=True)
        if receipt_response is not None:
            return receipt_response
        approval_state, _approval_id = self._approval_state(request)
        if approval_state == "REJECTED":
            return self._response(
                request,
                authority_outcome="DENY",
                execution_state="REJECTED",
                reason="EXACT_APPROVAL_REJECTED",
            )
        return self._response(
            request,
            authority_outcome="DENY",
            execution_state="NOT_EXECUTED",
            reason="NO_TERMINAL_EFFECT",
        )
