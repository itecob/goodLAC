from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Mapping

from packages.adapters.pi.adapter import PiAgentAdapterError, _arguments_for_tool
from packages.core import EffectRequest, canonical_json
from packages.effects.filesystem import (
    FILESYSTEM_CREATE_ACTION,
    FILESYSTEM_READ_ACTION,
    FILESYSTEM_REPLACE_ACTION,
    FilesystemEffectAdapter,
)
from packages.effects.shell import SHELL_EXEC_ACTION, ShellEffectAdapter
from packages.runtime import (
    EXTERNAL_CONSUMER_REQUEST_SCHEMA,
    ExternalConsumerDeclaration,
    ExternalConsumerRuntime,
    NativeLocalConsumerRuntime,
)
from packages.runtime.pi_continuation import PiWorkflowContinuationError
from packages.runtime.workflow_continuation import NATIVE_CONTINUATION_TTL_SECONDS
from packages.state import SQLiteStateStore

PI_V1_PRINCIPAL_ID = "principal:owner"
PI_V1_AGENT_ID = "agent:pi"
PI_V1_APPLICATION_ID = "lac-pi-v1"
PI_V1_SKILL_ID = "governed-local-effects"
PI_V1_REQUEST_TTL_SECONDS = 3600

_FS_RESOURCE = "filesystem:workspace"
_SHELL_RESOURCE = "shell:workspace"
_STR4096 = {"type": "string", "minLength": 0, "maxLength": 4096}
_NONEMPTY4096 = {"type": "string", "minLength": 1, "maxLength": 4096}
_CONTENT = {"type": "string", "minLength": 0, "maxLength": 1048576}
_EMPTY_ENV = {"type": "object", "properties": {}, "required": [], "additionalProperties": False}

PI_V1_CAPABILITY_MANIFEST = {
    "schema": "lac.capability-manifest/v1",
    "manifest_version": 1,
    "application_id": PI_V1_APPLICATION_ID,
    "skill_id": PI_V1_SKILL_ID,
    "actions": [
        {
            "action": FILESYSTEM_READ_ACTION,
            "resource": {"type": "filesystem.workspace", "selectors": [_FS_RESOURCE]},
            "arguments": {
                "type": "object",
                "properties": {"path": _NONEMPTY4096},
                "required": ["path"],
                "additionalProperties": False,
            },
            "security_properties": ["read_only"],
        },
        {
            "action": FILESYSTEM_CREATE_ACTION,
            "resource": {"type": "filesystem.workspace", "selectors": [_FS_RESOURCE]},
            "arguments": {
                "type": "object",
                "properties": {"path": _NONEMPTY4096, "content": _CONTENT},
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            "security_properties": ["local_mutation"],
        },
        {
            "action": FILESYSTEM_REPLACE_ACTION,
            "resource": {"type": "filesystem.workspace", "selectors": [_FS_RESOURCE]},
            "arguments": {
                "type": "object",
                "properties": {"path": _NONEMPTY4096, "content": _CONTENT},
                "required": ["path", "content"],
                "additionalProperties": False,
            },
            "security_properties": ["local_mutation"],
        },
        {
            "action": SHELL_EXEC_ACTION,
            "resource": {"type": "shell.workspace", "selectors": [_SHELL_RESOURCE]},
            "arguments": {
                "type": "object",
                "properties": {
                    "executable": _NONEMPTY4096,
                    "argv": {
                        "type": "array",
                        "items": _STR4096,
                        "minItems": 0,
                        "maxItems": 128,
                    },
                    "cwd": _NONEMPTY4096,
                    "environment": _EMPTY_ENV,
                },
                "required": ["executable", "argv", "cwd", "environment"],
                "additionalProperties": False,
            },
            "security_properties": ["local_mutation", "security_sensitive"],
        },
    ],
}


class PiV1RuntimeError(RuntimeError):
    pass


class PiV1CompositeAdapter:
    """Facade over H002/H003. Capability/policy validation remains authoritative."""

    adapter_id = "pi-governed-local-effects:v1"

    def __init__(self, filesystem_adapter: FilesystemEffectAdapter, shell_adapter: ShellEffectAdapter):
        if not isinstance(filesystem_adapter, FilesystemEffectAdapter):
            raise PiV1RuntimeError("filesystem_adapter must be FilesystemEffectAdapter")
        if not isinstance(shell_adapter, ShellEffectAdapter):
            raise PiV1RuntimeError("shell_adapter must be ShellEffectAdapter")
        self.filesystem_adapter = filesystem_adapter
        self.shell_adapter = shell_adapter

    def supports(self, request: EffectRequest) -> bool:
        # Broad by design so P002 classifies unknown/new capability material.
        # This grants no authority; invoke occurs only after capability + policy gates.
        return isinstance(request, EffectRequest)

    def _delegate(self, request: EffectRequest):
        if request.action in {
            FILESYSTEM_READ_ACTION,
            FILESYSTEM_CREATE_ACTION,
            FILESYSTEM_REPLACE_ACTION,
        }:
            if request.resource != self.filesystem_adapter.resource:
                raise PiV1RuntimeError("filesystem request is outside configured Pi workspace")
            return self.filesystem_adapter
        if request.action == SHELL_EXEC_ACTION:
            if request.resource != self.shell_adapter.resource:
                raise PiV1RuntimeError("shell request is outside configured Pi workspace")
            return self.shell_adapter
        raise PiV1RuntimeError("capability-authorized action has no Pi v1 implementation")

    def invoke(self, request, *, lease):
        return self._delegate(request).invoke(request, lease=lease)

    def reconcile(self, request, *, lease):
        delegate = self._delegate(request)
        reconcile = getattr(delegate, "reconcile", None)
        return reconcile(request, lease=lease) if callable(reconcile) else None


@dataclass(frozen=True)
class PiV1RequestIdentity:
    request_id: str
    idempotency_key: str


class PiPermissionRuntime:
    """Thin Pi edge over the accepted Phase 4 ExternalConsumerRuntime.

    Permission workflow continuation is deliberately non-authoritative. The first unconfigured
    request is still terminally denied by Phase 4. This edge only captures the immutable intent
    and, after an owner resolution, submits one fresh request through the same authoritative
    runtime.
    """

    def __init__(
        self,
        *,
        store: SQLiteStateStore,
        filesystem_adapter: FilesystemEffectAdapter,
        shell_adapter: ShellEffectAdapter,
        run_id: str,
        clock: Callable[[], datetime] | None = None,
        continuation_ttl_seconds: int = NATIVE_CONTINUATION_TTL_SECONDS,
    ):
        if not isinstance(store, SQLiteStateStore):
            raise PiV1RuntimeError("store must be SQLiteStateStore")
        if not isinstance(run_id, str) or not run_id or run_id != run_id.strip():
            raise PiV1RuntimeError("run_id must be non-empty trimmed text")
        self.store = store
        self.run_id = run_id
        self.filesystem_adapter = filesystem_adapter
        self.shell_adapter = shell_adapter
        self.composite_adapter = PiV1CompositeAdapter(filesystem_adapter, shell_adapter)
        self.declaration = ExternalConsumerDeclaration.create(PI_V1_CAPABILITY_MANIFEST)
        self.runtime = ExternalConsumerRuntime(
            store=store,
            declaration=self.declaration,
            principal_id=PI_V1_PRINCIPAL_ID,
            agent_id=PI_V1_AGENT_ID,
            application_id=PI_V1_APPLICATION_ID,
            skill_id=PI_V1_SKILL_ID,
            adapter=self.composite_adapter,
            clock=clock,
            request_ttl_seconds=PI_V1_REQUEST_TTL_SECONDS,
        )
        self.consumer = NativeLocalConsumerRuntime(
            store=store,
            authority_runtime=self.runtime,
            clock=clock,
            continuation_ttl_seconds=continuation_ttl_seconds,
        )
        self.continuations = self.consumer.continuations

    def _identity(self, tool_call_id: str) -> PiV1RequestIdentity:
        if (
            not isinstance(tool_call_id, str)
            or not tool_call_id
            or tool_call_id != tool_call_id.strip()
        ):
            raise PiAgentAdapterError("tool_call_id must be non-empty trimmed text")
        material = canonical_json(
            {
                "run_id": self.run_id,
                "agent_id": PI_V1_AGENT_ID,
                "application_id": PI_V1_APPLICATION_ID,
                "skill_id": PI_V1_SKILL_ID,
                "tool_call_id": tool_call_id,
            }
        ).encode("utf-8")
        digest = hashlib.sha256(material).hexdigest()
        return PiV1RequestIdentity(
            request_id=f"effect:pi-v1:{digest[:40]}",
            idempotency_key=f"idem:pi-v1:{digest}",
        )

    def build_material(self, *, tool_name: str, arguments: object, tool_call_id: str):
        action, canonical_arguments = _arguments_for_tool(tool_name, arguments)
        resource = (
            self.filesystem_adapter.resource
            if action
            in {FILESYSTEM_READ_ACTION, FILESYSTEM_CREATE_ACTION, FILESYSTEM_REPLACE_ACTION}
            else self.shell_adapter.resource
        )
        ident = self._identity(tool_call_id)
        return {
            "schema": EXTERNAL_CONSUMER_REQUEST_SCHEMA,
            "request_id": ident.request_id,
            "run_id": self.run_id,
            "action": action,
            "resource": resource,
            "arguments": canonical_arguments,
            "idempotency_key": ident.idempotency_key,
        }

    def _decorate(self, response: Mapping[str, Any]):
        # Compatibility helper retained for accepted PI001 tests. Contract decoration is now
        # owned by the consumer-neutral runtime rather than by the Pi edge.
        return self.consumer.decorate(response)

    def _submit_authoritative(self, material: Mapping[str, Any]) -> dict[str, Any]:
        return self.consumer.submit_authoritative(material)

    def submit_tool(self, *, tool_name: str, arguments: object, tool_call_id: str):
        material = self.build_material(
            tool_name=tool_name, arguments=arguments, tool_call_id=tool_call_id
        )
        return self.consumer.submit(material)

    def submit_message(self, message: object):
        if not isinstance(message, Mapping):
            raise PiAgentAdapterError("Pi bridge message must be a JSON object")
        expected = {"toolCallId", "toolName", "arguments"}
        if set(message) != expected:
            raise PiAgentAdapterError(
                f"Pi bridge message must contain exactly {sorted(expected)!r}; "
                f"observed={sorted(set(message))!r}"
            )
        return self.submit_tool(
            tool_name=message["toolName"],
            arguments=message["arguments"],
            tool_call_id=message["toolCallId"],
        )

    def continuation_status(self, continuation_id: str) -> dict[str, Any]:
        return self.consumer.continuation_status(continuation_id)

    def list_continuations(self, *, recoverable_only: bool = False) -> list[dict[str, Any]]:
        return self.consumer.list_continuations(recoverable_only=recoverable_only)

    def resume_continuation(
        self,
        continuation_id: str,
        *,
        expected_message: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        expected_material = None
        if expected_message is not None:
            if not isinstance(expected_message, Mapping):
                raise PiWorkflowContinuationError("expected Pi message must be an object")
            expected = {"toolCallId", "toolName", "arguments"}
            if set(expected_message) != expected:
                raise PiWorkflowContinuationError(
                    "expected Pi message fields do not match governed tool request"
                )
            expected_material = self.build_material(
                tool_name=expected_message["toolName"],
                arguments=expected_message["arguments"],
                tool_call_id=expected_message["toolCallId"],
            )
        return self.consumer.resume(
            continuation_id, expected_material=expected_material
        )
