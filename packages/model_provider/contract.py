from __future__ import annotations

from dataclasses import dataclass, field
from threading import Event
from typing import Any, Iterator, Mapping, Protocol, runtime_checkable


class ModelProviderError(RuntimeError):
    """Base failure at the replaceable model-runtime boundary."""


class ModelProviderUnavailable(ModelProviderError):
    """The configured model runtime cannot be reached or is not serving."""


class ModelProviderTimeout(ModelProviderError):
    """The model-runtime request exceeded its bounded timeout."""


class ModelProviderCancelled(ModelProviderError):
    """The caller cancelled the model-runtime request."""


class ModelProviderMalformedResponse(ModelProviderError):
    """The runtime returned data outside the LAC-owned response contract."""


class ModelProviderCapabilityError(ModelProviderError):
    """The caller requested a feature the selected runtime cannot truthfully provide."""


@dataclass(frozen=True)
class CancellationToken:
    """Controller/agent-side cancellation signal; it carries no authority."""

    _event: Event = field(default_factory=Event, compare=False, repr=False)

    def cancel(self) -> None:
        self._event.set()

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()


@dataclass(frozen=True)
class ModelProviderCapabilities:
    streaming: bool
    tools: bool
    reasoning: bool
    structured_output: bool
    seed: bool
    cancellation: bool


@dataclass(frozen=True)
class ModelRequest:
    """LAC-owned inference request.

    This deliberately contains model/runtime concerns only. Approval, policy,
    lease, dispatcher, effect-adapter, credential, principal, and executor
    fields do not exist at this boundary.
    """

    model: str
    messages: tuple[Mapping[str, Any], ...]
    max_tokens: int | None = None
    temperature: float | None = None
    top_k: int | None = None
    top_p: float | None = None
    stop: str | tuple[str, ...] | None = None
    reasoning_effort: str | None = None
    tools: tuple[Mapping[str, Any], ...] = ()
    tool_choice: str | Mapping[str, Any] | None = None
    response_format: Mapping[str, Any] | None = None
    seed: int | None = None
    timeout_seconds: float = 120.0

    def __post_init__(self) -> None:
        if not isinstance(self.model, str) or not self.model.strip() or self.model != self.model.strip():
            raise ValueError("model must be a non-empty trimmed string")
        if not isinstance(self.messages, tuple) or not self.messages:
            raise ValueError("messages must be a non-empty tuple")
        if any(not isinstance(message, Mapping) for message in self.messages):
            raise ValueError("messages must contain mappings")
        if self.max_tokens is not None:
            if isinstance(self.max_tokens, bool) or not isinstance(self.max_tokens, int) or self.max_tokens <= 0:
                raise ValueError("max_tokens must be a positive integer")
        if self.top_k is not None:
            if isinstance(self.top_k, bool) or not isinstance(self.top_k, int) or self.top_k <= 0:
                raise ValueError("top_k must be a positive integer")
        for name, value in (("temperature", self.temperature), ("top_p", self.top_p)):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise ValueError(f"{name} must be numeric")
        if self.temperature is not None and self.temperature < 0:
            raise ValueError("temperature must be >= 0")
        if self.top_p is not None and not 0 < float(self.top_p) <= 1:
            raise ValueError("top_p must be within (0, 1]")
        if self.seed is not None and (isinstance(self.seed, bool) or not isinstance(self.seed, int)):
            raise ValueError("seed must be an integer")
        if isinstance(self.timeout_seconds, bool) or not isinstance(self.timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be numeric")
        if not 0 < float(self.timeout_seconds) <= 600:
            raise ValueError("timeout_seconds must be within (0, 600]")
        if self.reasoning_effort is not None and (
            not isinstance(self.reasoning_effort, str)
            or not self.reasoning_effort.strip()
            or self.reasoning_effort != self.reasoning_effort.strip()
        ):
            raise ValueError("reasoning_effort must be a non-empty trimmed string")
        if not isinstance(self.tools, tuple):
            raise ValueError("tools must be a tuple")
        if any(not isinstance(tool, Mapping) for tool in self.tools):
            raise ValueError("tools must contain mappings")
        if self.stop is not None:
            if isinstance(self.stop, str):
                if not self.stop:
                    raise ValueError("stop string cannot be empty")
            elif isinstance(self.stop, tuple):
                if not self.stop or any(not isinstance(value, str) or not value for value in self.stop):
                    raise ValueError("stop tuple must contain non-empty strings")
            else:
                raise ValueError("stop must be a string, tuple of strings, or None")


@dataclass(frozen=True)
class ModelUsage:
    input_tokens: int
    output_tokens: int
    total_tokens: int
    cached_input_tokens: int = 0

    def __post_init__(self) -> None:
        for field_name in ("input_tokens", "output_tokens", "total_tokens", "cached_input_tokens"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ValueError(f"{field_name} must be a non-negative integer")
        if self.total_tokens < self.input_tokens + self.output_tokens:
            raise ValueError("total_tokens cannot be less than input_tokens + output_tokens")


@dataclass(frozen=True)
class ModelResponse:
    response_id: str
    model: str
    content: str | None
    reasoning: str | None
    tool_calls: tuple[Mapping[str, Any], ...]
    finish_reason: str | None
    usage: ModelUsage


@dataclass(frozen=True)
class ModelStreamEvent:
    kind: str
    value: Any = None


@runtime_checkable
class ModelProvider(Protocol):
    @property
    def capabilities(self) -> ModelProviderCapabilities: ...

    def generate(
        self,
        request: ModelRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> ModelResponse: ...

    def stream(
        self,
        request: ModelRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> Iterator[ModelStreamEvent]: ...
