from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Mapping

from packages.core import EffectRequest, canonical_json
from packages.dispatcher import Dispatcher
from packages.effects.filesystem import (
    FILESYSTEM_CREATE_ACTION,
    FILESYSTEM_READ_ACTION,
    FILESYSTEM_REPLACE_ACTION,
    FilesystemEffectAdapter,
)
from packages.effects.shell import SHELL_EXEC_ACTION, ShellEffectAdapter
from packages.state import EffectRequestRepository, SQLiteStateStore


PI_FS_READ_TOOL = "lac_fs_read"
PI_FS_CREATE_TOOL = "lac_fs_create"
PI_FS_REPLACE_TOOL = "lac_fs_replace"
PI_SHELL_EXEC_TOOL = "lac_shell_exec"
PI_GOVERNED_TOOL_NAMES = (
    PI_FS_READ_TOOL,
    PI_FS_CREATE_TOOL,
    PI_FS_REPLACE_TOOL,
    PI_SHELL_EXEC_TOOL,
)

_RESERVED_AUTHORITY_KEYS = frozenset(
    {
        "approval_id",
        "decision_id",
        "executor_id",
        "idempotency_key",
        "lease_id",
        "principal_id",
        "agent_id",
        "request_id",
        "run_id",
    }
)


class PiAgentAdapterError(ValueError):
    """A Pi tool proposal is outside the bounded LAC AgentAdapter contract."""


def _required_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value != value.strip():
        raise PiAgentAdapterError(f"{field} must be a non-empty trimmed string")
    return value


def _trusted_now(clock: Callable[[], datetime]) -> datetime:
    try:
        observed = clock()
    except Exception as exc:
        raise PiAgentAdapterError("trusted AgentAdapter clock failed closed") from exc
    if not isinstance(observed, datetime) or observed.tzinfo is None or observed.utcoffset() is None:
        raise PiAgentAdapterError("trusted AgentAdapter clock must return a timezone-aware datetime")
    return observed.astimezone(timezone.utc)


def _rfc3339(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00", "Z")


def _exact_keys(arguments: Mapping[str, Any], expected: set[str], tool_name: str) -> None:
    observed = set(arguments)
    if observed & _RESERVED_AUTHORITY_KEYS:
        raise PiAgentAdapterError("Pi/model tool arguments cannot supply controller authority identifiers")
    if observed != expected:
        raise PiAgentAdapterError(
            f"{tool_name} arguments must contain exactly {sorted(expected)!r}; observed={sorted(observed)!r}"
        )


def _arguments_for_tool(tool_name: str, raw: object) -> tuple[str, dict[str, Any]]:
    if not isinstance(raw, Mapping):
        raise PiAgentAdapterError("Pi tool arguments must be a JSON object")
    arguments = dict(raw)

    if tool_name == PI_FS_READ_TOOL:
        _exact_keys(arguments, {"path"}, tool_name)
        if not isinstance(arguments["path"], str):
            raise PiAgentAdapterError("lac_fs_read.path must be a string")
        return FILESYSTEM_READ_ACTION, {"path": arguments["path"]}

    if tool_name in (PI_FS_CREATE_TOOL, PI_FS_REPLACE_TOOL):
        _exact_keys(arguments, {"path", "content"}, tool_name)
        if not isinstance(arguments["path"], str) or not isinstance(arguments["content"], str):
            raise PiAgentAdapterError(f"{tool_name}.path and .content must be strings")
        action = FILESYSTEM_CREATE_ACTION if tool_name == PI_FS_CREATE_TOOL else FILESYSTEM_REPLACE_ACTION
        return action, {"path": arguments["path"], "content": arguments["content"]}

    if tool_name == PI_SHELL_EXEC_TOOL:
        _exact_keys(arguments, {"executable", "argv", "cwd", "environment"}, tool_name)
        executable = arguments["executable"]
        argv = arguments["argv"]
        cwd = arguments["cwd"]
        environment = arguments["environment"]
        if not isinstance(executable, str) or not isinstance(cwd, str):
            raise PiAgentAdapterError("lac_shell_exec executable and cwd must be strings")
        if not isinstance(argv, list) or any(not isinstance(item, str) for item in argv):
            raise PiAgentAdapterError("lac_shell_exec argv must be an array of strings")
        if not isinstance(environment, dict) or any(
            not isinstance(key, str) or not isinstance(value, str) for key, value in environment.items()
        ):
            raise PiAgentAdapterError("lac_shell_exec environment must map string names to string values")
        return SHELL_EXEC_ACTION, {
            "executable": executable,
            "argv": list(argv),
            "cwd": cwd,
            "environment": dict(environment),
        }

    raise PiAgentAdapterError(f"unknown or ungoverned Pi tool: {tool_name!r}")


@dataclass(frozen=True)
class PiRunContext:
    run_id: str
    principal_id: str
    agent_id: str
    executor_id: str

    def __post_init__(self) -> None:
        for field in ("run_id", "principal_id", "agent_id", "executor_id"):
            object.__setattr__(self, field, _required_text(getattr(self, field), field))


class PiAgentAdapter:
    """Translate Pi Agent Core tool proposals into canonical LAC governed effects.

    The model controls only ``tool_name`` and the tool-specific argument object. Request,
    policy-decision, lease, executor, idempotency, and optional approval identifiers stay
    on the controller side of this boundary.
    """

    def __init__(
        self,
        *,
        store: SQLiteStateStore,
        dispatcher: Dispatcher,
        filesystem_adapter: FilesystemEffectAdapter,
        shell_adapter: ShellEffectAdapter,
        context: PiRunContext,
        clock: Callable[[], datetime] | None = None,
        request_ttl_seconds: int = 300,
        id_factory: Callable[[], str] | None = None,
    ) -> None:
        if not isinstance(store, SQLiteStateStore):
            raise PiAgentAdapterError("store must be a SQLiteStateStore")
        if not isinstance(dispatcher, Dispatcher):
            raise PiAgentAdapterError("dispatcher must be the LAC Dispatcher")
        if not isinstance(filesystem_adapter, FilesystemEffectAdapter):
            raise PiAgentAdapterError("filesystem_adapter must be FilesystemEffectAdapter")
        if not isinstance(shell_adapter, ShellEffectAdapter):
            raise PiAgentAdapterError("shell_adapter must be ShellEffectAdapter")
        if not isinstance(context, PiRunContext):
            raise PiAgentAdapterError("context must be PiRunContext")
        if not isinstance(request_ttl_seconds, int) or isinstance(request_ttl_seconds, bool):
            raise PiAgentAdapterError("request_ttl_seconds must be an integer")
        if request_ttl_seconds <= 0 or request_ttl_seconds > 3600:
            raise PiAgentAdapterError("request_ttl_seconds must be within [1, 3600]")
        if clock is not None and not callable(clock):
            raise PiAgentAdapterError("clock must be callable")
        if id_factory is not None and not callable(id_factory):
            raise PiAgentAdapterError("id_factory must be callable")
        self._store = store
        self._dispatcher = dispatcher
        self._filesystem_adapter = filesystem_adapter
        self._shell_adapter = shell_adapter
        self._context = context
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._request_ttl_seconds = request_ttl_seconds
        self._id_factory = id_factory or (lambda: uuid.uuid4().hex)

    @property
    def tool_names(self) -> tuple[str, ...]:
        return PI_GOVERNED_TOOL_NAMES

    @property
    def context(self) -> PiRunContext:
        return self._context

    def _controller_id(self, prefix: str) -> str:
        raw = _required_text(self._id_factory(), "controller-generated id")
        return f"{prefix}:{raw}"

    def build_request(self, *, tool_name: str, arguments: object, tool_call_id: str) -> EffectRequest:
        tool_name = _required_text(tool_name, "tool_name")
        tool_call_id = _required_text(tool_call_id, "tool_call_id")
        action, canonical_arguments = _arguments_for_tool(tool_name, arguments)
        resource = (
            self._filesystem_adapter.resource
            if action in (FILESYSTEM_READ_ACTION, FILESYSTEM_CREATE_ACTION, FILESYSTEM_REPLACE_ACTION)
            else self._shell_adapter.resource
        )
        call_material = canonical_json(
            {
                "run_id": self._context.run_id,
                "agent_id": self._context.agent_id,
                "tool_call_id": tool_call_id,
            }
        ).encode("utf-8")
        call_digest = hashlib.sha256(call_material).hexdigest()
        request_id = f"effect:pi:{call_digest[:40]}"
        idempotency_key = f"idem:pi:{call_digest}"

        # A Pi tool-call id is the durable retry identity. If the request already
        # exists, reuse its trusted timestamps verbatim and require all model-visible
        # security material to match. This keeps approval resumption/retry canonical
        # even when wall-clock time has advanced.
        existing = EffectRequestRepository(self._store).get(request_id)
        if existing is not None:
            if (
                existing.run_id != self._context.run_id
                or existing.principal_id != self._context.principal_id
                or existing.agent_id != self._context.agent_id
                or existing.action != action
                or existing.resource != resource
                or existing.arguments != canonical_arguments
                or existing.idempotency_key != idempotency_key
            ):
                raise PiAgentAdapterError(
                    "Pi tool_call_id is already bound to different canonical request material"
                )
            return existing

        now = _trusted_now(self._clock)
        expires = now + timedelta(seconds=self._request_ttl_seconds)
        return EffectRequest.create(
            request_id=request_id,
            run_id=self._context.run_id,
            principal_id=self._context.principal_id,
            agent_id=self._context.agent_id,
            action=action,
            resource=resource,
            arguments=canonical_arguments,
            idempotency_key=idempotency_key,
            created_at=_rfc3339(now),
            expires_at=_rfc3339(expires),
        )

    def execute_message(self, message: object) -> dict[str, Any]:
        """Execute the exact model-facing bridge message emitted by ``governed_pi.mjs``.

        This message has no authority fields. Approval resumption, if required, is a
        separate controller-host operation through :meth:`execute_tool`.
        """
        if not isinstance(message, Mapping):
            raise PiAgentAdapterError("Pi bridge message must be a JSON object")
        observed = set(message)
        expected = {"toolCallId", "toolName", "arguments"}
        if observed != expected:
            raise PiAgentAdapterError(
                f"Pi bridge message must contain exactly {sorted(expected)!r}; observed={sorted(observed)!r}"
            )
        result = self.execute_tool(
            tool_name=message["toolName"],
            arguments=message["arguments"],
            tool_call_id=message["toolCallId"],
        )
        to_record = getattr(result, "to_record", None)
        if not callable(to_record):
            raise PiAgentAdapterError("effect adapter returned a non-serializable governed result")
        record = to_record()
        if not isinstance(record, dict):
            raise PiAgentAdapterError("effect adapter result record must be a JSON object")
        return record

    def execute_tool(
        self,
        *,
        tool_name: str,
        arguments: object,
        tool_call_id: str,
        approval_id: str | None = None,
    ) -> Any:
        """Persist and dispatch one governed Pi proposal.

        ``approval_id`` is a controller-host input, deliberately absent from every Pi
        tool schema. Supplying or resolving approvals remains outside model context.
        """
        if approval_id is not None:
            approval_id = _required_text(approval_id, "approval_id")
        request = self.build_request(
            tool_name=tool_name,
            arguments=arguments,
            tool_call_id=tool_call_id,
        )
        request = EffectRequestRepository(self._store).put(request)
        adapter = (
            self._filesystem_adapter
            if request.action in (FILESYSTEM_READ_ACTION, FILESYSTEM_CREATE_ACTION, FILESYSTEM_REPLACE_ACTION)
            else self._shell_adapter
        )
        return self._dispatcher.dispatch(
            request,
            adapter=adapter,
            decision_id=self._controller_id("decision:pi"),
            lease_id=self._controller_id("lease:pi"),
            executor_id=self._context.executor_id,
            approval_id=approval_id,
        )
