from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from typing import Any, Mapping, Protocol, runtime_checkable

from packages.core import EffectRequest, EffectRequestError, ExecutionLease, ExecutionLeaseError
from packages.core.effect_request import canonical_json
from packages.credentials import SecretProvider, SecretProviderError, validate_credential_ref


GMAIL_ADAPTER_ID = "gmail:v1"
GMAIL_RESULT_SCHEMA = "lac.gmail-effect-result/v1"
GMAIL_SEARCH_ACTION = "email.search"
GMAIL_READ_ACTION = "email.read"
GMAIL_DRAFT_ACTION = "email.draft"
GMAIL_SEND_ACTION = "email.send"
GMAIL_ARCHIVE_ACTION = "email.archive"
GMAIL_DELETE_ACTION = "email.delete"
GMAIL_ACTIONS = frozenset(
    {
        GMAIL_SEARCH_ACTION,
        GMAIL_READ_ACTION,
        GMAIL_DRAFT_ACTION,
        GMAIL_SEND_ACTION,
        GMAIL_ARCHIVE_ACTION,
        GMAIL_DELETE_ACTION,
    }
)

_HASH_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
_EMAIL_RE = re.compile(r"^[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[A-Za-z0-9!#$%&'*+/=?^_`{|}~-]+)*@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?$")
_FORBIDDEN_RESULT_KEYS = frozenset(
    {
        "access_token",
        "authorization",
        "client_secret",
        "credential",
        "credential_ref",
        "credentials",
        "refresh_token",
        "secret",
        "token",
    }
)


class GmailEffectError(ValueError):
    """A Gmail typed-effect request/provider boundary failed closed."""


@dataclass(frozen=True)
class GmailMessageInput:
    to: tuple[str, ...]
    cc: tuple[str, ...]
    bcc: tuple[str, ...]
    subject: str
    body: str
    body_sha256: str
    attachment_hashes: tuple[str, ...]

    def to_transport_record(self) -> dict[str, Any]:
        return {
            "to": list(self.to),
            "cc": list(self.cc),
            "bcc": list(self.bcc),
            "subject": self.subject,
            "body": self.body,
            "body_sha256": self.body_sha256,
            "attachment_hashes": list(self.attachment_hashes),
        }


@dataclass(frozen=True)
class _GmailOperation:
    action: str
    message_id: str | None = None
    query: str | None = None
    max_results: int | None = None
    message: GmailMessageInput | None = None


@dataclass(frozen=True)
class GmailEffectResult:
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
class GmailTransport(Protocol):
    """Credential-bearing service client hidden behind the deterministic adapter."""

    def search(self, *, query: str, max_results: int) -> Mapping[str, Any]:
        ...

    def read(self, *, message_id: str) -> Mapping[str, Any]:
        ...

    def create_draft(
        self,
        *,
        message: Mapping[str, Any],
        request_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        ...

    def send(
        self,
        *,
        message: Mapping[str, Any],
        request_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        ...

    def archive(
        self,
        *,
        message_id: str,
        request_id: str,
        idempotency_key: str,
    ) -> Mapping[str, Any]:
        ...

    def reconcile(
        self,
        *,
        action: str,
        request_id: str,
        idempotency_key: str,
        operation: Mapping[str, Any],
    ) -> Mapping[str, Any] | None:
        ...


@runtime_checkable
class GmailTransportFactory(Protocol):
    """Creates a Gmail service client from an opaque controller-only secret."""

    def create(self, *, account_resource: str, secret: object) -> GmailTransport:
        ...


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise GmailEffectError(f"{field} must be non-empty text")
    if value != value.strip():
        raise GmailEffectError(f"{field} must not have leading/trailing whitespace")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise GmailEffectError(f"{field} must be valid UTF-8 text") from exc
    return value


def _utf8_text(value: object, field: str) -> str:
    if not isinstance(value, str):
        raise GmailEffectError(f"{field} must be text")
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise GmailEffectError(f"{field} must be valid UTF-8 text") from exc
    return value


def _canonical_request(request: EffectRequest) -> EffectRequest:
    if not isinstance(request, EffectRequest):
        raise GmailEffectError("request must be a canonical EffectRequest")
    try:
        canonical = EffectRequest.from_record(request.to_record())
    except (EffectRequestError, TypeError, AttributeError) as exc:
        raise GmailEffectError("request failed canonical integrity validation") from exc
    if canonical != request:
        raise GmailEffectError("request is not canonical")
    return canonical


def _canonical_lease(lease: ExecutionLease) -> ExecutionLease:
    if not isinstance(lease, ExecutionLease):
        raise GmailEffectError("lease must be a canonical ExecutionLease")
    try:
        canonical = ExecutionLease.from_record(lease.to_record())
    except (ExecutionLeaseError, TypeError, AttributeError) as exc:
        raise GmailEffectError("lease failed canonical integrity validation") from exc
    if canonical != lease:
        raise GmailEffectError("lease is not canonical")
    return canonical


def _message_id(value: object) -> str:
    value = _required_text(value, "message_id")
    if len(value) > 512 or any(ord(ch) < 33 or ord(ch) == 127 for ch in value):
        raise GmailEffectError("message_id is not canonical bounded opaque text")
    return value


def _email_address(value: object, field: str) -> str:
    value = _required_text(value, field)
    if len(value) > 320 or not _EMAIL_RE.fullmatch(value):
        raise GmailEffectError(f"{field} must be a canonical mailbox address")
    return value


def _address_list(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise GmailEffectError(f"{field} must be a JSON array")
    if len(value) > 100:
        raise GmailEffectError(f"{field} exceeds the bounded recipient count")
    normalized = tuple(_email_address(item, f"{field}[]") for item in value)
    if len(set(normalized)) != len(normalized):
        raise GmailEffectError(f"{field} must not contain duplicate addresses")
    return normalized


def _sha256(value: object, field: str) -> str:
    if not isinstance(value, str) or not _HASH_RE.fullmatch(value):
        raise GmailEffectError(f"{field} must be lowercase canonical sha256: material")
    return value


def _attachment_hashes(value: object) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise GmailEffectError("attachment_hashes must be a JSON array")
    if len(value) > 25:
        raise GmailEffectError("attachment_hashes exceeds the bounded attachment count")
    normalized = tuple(_sha256(item, "attachment_hashes[]") for item in value)
    if tuple(sorted(normalized)) != normalized or len(set(normalized)) != len(normalized):
        raise GmailEffectError("attachment_hashes must be sorted and unique")
    return normalized


def _message_input(arguments: Mapping[str, Any]) -> GmailMessageInput:
    required = {
        "to",
        "cc",
        "bcc",
        "subject",
        "body",
        "body_sha256",
        "attachment_hashes",
    }
    if set(arguments) != required:
        raise GmailEffectError(
            "email draft/send arguments must contain exactly to, cc, bcc, subject, body, body_sha256, attachment_hashes"
        )
    to = _address_list(arguments["to"], "to")
    cc = _address_list(arguments["cc"], "cc")
    bcc = _address_list(arguments["bcc"], "bcc")
    if not (to or cc or bcc):
        raise GmailEffectError("email draft/send requires at least one recipient")
    subject = _utf8_text(arguments["subject"], "subject")
    if "\r" in subject or "\n" in subject or len(subject) > 998:
        raise GmailEffectError("subject contains prohibited newline material or is too long")
    body = _utf8_text(arguments["body"], "body")
    if len(body.encode("utf-8")) > 10 * 1024 * 1024:
        raise GmailEffectError("body exceeds the B001 bounded payload size")
    expected_body_hash = "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()
    body_hash = _sha256(arguments["body_sha256"], "body_sha256")
    if body_hash != expected_body_hash:
        raise GmailEffectError("body_sha256 does not match the exact UTF-8 body")
    attachment_hashes = _attachment_hashes(arguments["attachment_hashes"])
    return GmailMessageInput(
        to=to,
        cc=cc,
        bcc=bcc,
        subject=subject,
        body=body,
        body_sha256=body_hash,
        attachment_hashes=attachment_hashes,
    )


def _parse_operation(request: EffectRequest, *, resource: str) -> _GmailOperation:
    canonical = _canonical_request(request)
    if canonical.resource != resource:
        raise GmailEffectError("Gmail request targets a different configured account resource")
    if canonical.action not in GMAIL_ACTIONS:
        raise GmailEffectError(f"unsupported Gmail action: {canonical.action!r}")
    arguments = canonical.arguments

    if canonical.action == GMAIL_SEARCH_ACTION:
        if set(arguments) != {"query", "max_results"}:
            raise GmailEffectError("email.search arguments must contain exactly query and max_results")
        query = _required_text(arguments["query"], "query")
        if len(query) > 2048:
            raise GmailEffectError("query exceeds the bounded Gmail search length")
        max_results = arguments["max_results"]
        if not isinstance(max_results, int) or isinstance(max_results, bool) or not 1 <= max_results <= 50:
            raise GmailEffectError("max_results must be an integer from 1 through 50")
        return _GmailOperation(action=canonical.action, query=query, max_results=max_results)

    if canonical.action in (GMAIL_READ_ACTION, GMAIL_ARCHIVE_ACTION, GMAIL_DELETE_ACTION):
        if set(arguments) != {"message_id"}:
            raise GmailEffectError(f"{canonical.action} arguments must contain exactly message_id")
        return _GmailOperation(action=canonical.action, message_id=_message_id(arguments["message_id"]))

    if canonical.action in (GMAIL_DRAFT_ACTION, GMAIL_SEND_ACTION):
        return _GmailOperation(action=canonical.action, message=_message_input(arguments))

    raise GmailEffectError("unknown Gmail action fails closed")


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
                raise GmailEffectError("Gmail provider result contains a non-string key")
            if key.lower() in _FORBIDDEN_RESULT_KEYS:
                raise GmailEffectError("Gmail provider result contains credential-shaped material")
            _validate_result_value(item, path=f"{path}.{key}")
        return
    raise GmailEffectError(f"Gmail provider result contains unsupported value at {path}")


def _safe_result_record(value: object) -> tuple[dict[str, Any], str | None]:
    if not isinstance(value, Mapping):
        raise GmailEffectError("Gmail provider result must be a JSON object")
    raw = dict(value)
    _validate_result_value(raw)
    try:
        normalized = json.loads(canonical_json(raw))
    except Exception as exc:
        raise GmailEffectError("Gmail provider result is not canonical JSON") from exc
    upstream_reference = normalized.pop("upstream_reference", None)
    if upstream_reference is not None:
        upstream_reference = _required_text(upstream_reference, "upstream_reference")
        if len(upstream_reference) > 1024:
            raise GmailEffectError("upstream_reference exceeds the bounded length")
    return normalized, upstream_reference


class GmailEffectAdapter:
    """Typed Gmail boundary reached only through the LAC Dispatcher.

    Account identity is bound by EffectRequest.resource. The credential reference is
    adapter configuration, not agent/model input. It is resolved lazily only after
    deterministic authorization has reached invoke/reconcile.
    """

    def __init__(
        self,
        *,
        secret_provider: SecretProvider,
        transport_factory: GmailTransportFactory,
        resource: str = "email-account:primary",
        credential_ref: str = "gmail:primary",
    ) -> None:
        if not isinstance(secret_provider, SecretProvider):
            raise GmailEffectError("secret_provider must implement SecretProvider")
        if not isinstance(transport_factory, GmailTransportFactory):
            raise GmailEffectError("transport_factory must implement GmailTransportFactory")
        self._resource = _required_text(resource, "resource")
        try:
            self._credential_ref = validate_credential_ref(credential_ref)
        except SecretProviderError as exc:
            raise GmailEffectError("credential reference failed validation") from exc
        self._secret_provider = secret_provider
        self._transport_factory = transport_factory

    @property
    def adapter_id(self) -> str:
        return GMAIL_ADAPTER_ID

    @property
    def resource(self) -> str:
        return self._resource

    def supports(self, request: EffectRequest) -> bool:
        try:
            _parse_operation(request, resource=self._resource)
        except GmailEffectError:
            return False
        return True

    def _transport(self) -> GmailTransport:
        try:
            secret = self._secret_provider.resolve(self._credential_ref)
        except Exception as exc:
            raise GmailEffectError("Gmail credential resolution failed closed") from None
        if secret is None:
            raise GmailEffectError("Gmail credential resolution returned no capability")
        try:
            transport = self._transport_factory.create(
                account_resource=self._resource,
                secret=secret,
            )
        except Exception as exc:
            raise GmailEffectError("Gmail transport creation failed closed") from None
        if not isinstance(transport, GmailTransport):
            raise GmailEffectError("Gmail transport does not implement the required contract")
        return transport

    def _result(
        self,
        request: EffectRequest,
        lease: ExecutionLease,
        provider_result: object,
        *,
        require_upstream_reference: bool,
    ) -> GmailEffectResult:
        data, upstream_reference = _safe_result_record(provider_result)
        if require_upstream_reference and upstream_reference is None:
            raise GmailEffectError("Gmail mutation result lacks a stable upstream_reference")
        return GmailEffectResult(
            schema=GMAIL_RESULT_SCHEMA,
            adapter_id=GMAIL_ADAPTER_ID,
            request_id=request.request_id,
            canonical_request_hash=request.canonical_hash,
            lease_id=lease.lease_id,
            action=request.action,
            resource=request.resource,
            data=data,
            upstream_reference=upstream_reference,
        )

    def invoke(self, request: EffectRequest, *, lease: ExecutionLease) -> GmailEffectResult:
        canonical_request = _canonical_request(request)
        canonical_lease = _canonical_lease(lease)
        if canonical_lease.request_id != canonical_request.request_id:
            raise GmailEffectError("execution lease binds a different request_id")
        operation = _parse_operation(canonical_request, resource=self._resource)

        # email.delete is represented so policy can deterministically DENY it, but
        # the adapter has no delete implementation even if called incorrectly.
        if operation.action == GMAIL_DELETE_ACTION:
            raise GmailEffectError("email.delete is prohibited and has no mutation implementation")

        transport = self._transport()
        try:
            if operation.action == GMAIL_SEARCH_ACTION:
                assert operation.query is not None and operation.max_results is not None
                raw = transport.search(query=operation.query, max_results=operation.max_results)
                return self._result(canonical_request, canonical_lease, raw, require_upstream_reference=False)
            if operation.action == GMAIL_READ_ACTION:
                assert operation.message_id is not None
                raw = transport.read(message_id=operation.message_id)
                return self._result(canonical_request, canonical_lease, raw, require_upstream_reference=False)
            if operation.action == GMAIL_DRAFT_ACTION:
                assert operation.message is not None
                raw = transport.create_draft(
                    message=operation.message.to_transport_record(),
                    request_id=canonical_request.request_id,
                    idempotency_key=canonical_request.idempotency_key,
                )
                return self._result(canonical_request, canonical_lease, raw, require_upstream_reference=True)
            if operation.action == GMAIL_SEND_ACTION:
                assert operation.message is not None
                raw = transport.send(
                    message=operation.message.to_transport_record(),
                    request_id=canonical_request.request_id,
                    idempotency_key=canonical_request.idempotency_key,
                )
                return self._result(canonical_request, canonical_lease, raw, require_upstream_reference=True)
            if operation.action == GMAIL_ARCHIVE_ACTION:
                assert operation.message_id is not None
                raw = transport.archive(
                    message_id=operation.message_id,
                    request_id=canonical_request.request_id,
                    idempotency_key=canonical_request.idempotency_key,
                )
                return self._result(canonical_request, canonical_lease, raw, require_upstream_reference=True)
        except GmailEffectError:
            raise
        except Exception as exc:
            # Do not surface provider exception text; it may contain secret material.
            raise GmailEffectError("Gmail provider invocation failed closed") from exc
        raise GmailEffectError("unknown Gmail action fails closed")

    def reconcile(
        self,
        request: EffectRequest,
        *,
        lease: ExecutionLease,
    ) -> GmailEffectResult | None:
        canonical_request = _canonical_request(request)
        canonical_lease = _canonical_lease(lease)
        if canonical_lease.request_id != canonical_request.request_id:
            raise GmailEffectError("execution lease binds a different request_id")
        operation = _parse_operation(canonical_request, resource=self._resource)
        if operation.action == GMAIL_DELETE_ACTION:
            raise GmailEffectError("email.delete is prohibited and cannot reconcile")

        # Search/read are non-consequential and safe to reissue. Mutations use the
        # provider's read-only reconciliation surface. None means ambiguity remains
        # and Dispatcher must stop instead of repeating the external mutation.
        if operation.action in (GMAIL_SEARCH_ACTION, GMAIL_READ_ACTION):
            return self.invoke(canonical_request, lease=canonical_lease)

        transport = self._transport()
        try:
            operation_record: dict[str, Any] = {"action": operation.action}
            if operation.message_id is not None:
                operation_record["message_id"] = operation.message_id
            if operation.message is not None:
                operation_record["message"] = operation.message.to_transport_record()
            raw = transport.reconcile(
                action=operation.action,
                request_id=canonical_request.request_id,
                idempotency_key=canonical_request.idempotency_key,
                operation=operation_record,
            )
        except Exception as exc:
            raise GmailEffectError("Gmail reconciliation failed closed") from exc
        if raw is None:
            return None
        return self._result(canonical_request, canonical_lease, raw, require_upstream_reference=True)
