from __future__ import annotations

import copy
import json
import socket
from dataclasses import fields
from typing import Any, Iterator, Mapping
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request as UrlRequest, urlopen

from packages.model_provider import (
    CancellationToken,
    ModelProviderCapabilities,
    ModelProviderCapabilityError,
    ModelProviderCancelled,
    ModelProviderError,
    ModelProviderMalformedResponse,
    ModelProviderTimeout,
    ModelProviderUnavailable,
    ModelRequest,
    ModelResponse,
    ModelStreamEvent,
    ModelUsage,
)

FREETOKEN_COMMIT = "af71ba43206e124f5ff6419b47ee36c6e9981078"
FREETOKEN_VERSION = "0.1.2"
FREETOKEN_LICENSE = "Apache-2.0"

_AUTHORITY_FIELD_NAMES = frozenset(
    {
        "approval_id",
        "decision_id",
        "dispatcher",
        "executor_id",
        "idempotency_key",
        "lease_id",
        "principal_id",
        "request_id",
        "run_id",
    }
)
_CREDENTIAL_FIELD_NAMES = frozenset(
    {
        "api_key",
        "authorization",
        "bearer_token",
        "client_secret",
        "credential",
        "credentials",
        "password",
        "secret",
        "service_token",
    }
)


def _validate_boundary_shape() -> None:
    field_names = {item.name for item in fields(ModelRequest)}
    forbidden = field_names & (_AUTHORITY_FIELD_NAMES | _CREDENTIAL_FIELD_NAMES)
    if forbidden:
        raise RuntimeError(f"ModelRequest exposes forbidden authority/credential fields: {sorted(forbidden)!r}")


_validate_boundary_shape()


def _is_loopback_host(hostname: str | None) -> bool:
    if hostname is None:
        return False
    lowered = hostname.lower()
    return lowered in {"localhost", "127.0.0.1", "::1"}


def _normalize_base_url(value: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError("base_url must be a non-empty trimmed string")
    parsed = urlparse(value)
    if parsed.scheme != "http":
        raise ValueError("FreeToken endpoint must use loopback HTTP")
    if parsed.username is not None or parsed.password is not None:
        raise ValueError("FreeToken endpoint URL cannot embed credentials")
    if not _is_loopback_host(parsed.hostname):
        raise ValueError("FreeToken endpoint must resolve by explicit loopback host")
    if parsed.query or parsed.fragment:
        raise ValueError("FreeToken endpoint URL cannot contain query or fragment")
    path = parsed.path.rstrip("/")
    if path not in {"", "/v1"}:
        raise ValueError("FreeToken endpoint base path must be empty or /v1")
    root = f"{parsed.scheme}://{parsed.netloc}"
    return root


def _deep_json_copy(value: Any) -> Any:
    try:
        return json.loads(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False))
    except (TypeError, ValueError) as exc:
        raise ValueError("model request contains non-JSON data") from exc


def _optional_field(payload: dict[str, Any], name: str, value: Any) -> None:
    if value is not None:
        payload[name] = value


def _bounded_error_body(exc: HTTPError) -> str:
    try:
        data = exc.read(8192)
    except Exception:
        return ""
    return data.decode("utf-8", errors="replace").strip()


def _map_transport_error(exc: BaseException) -> ModelProviderError:
    if isinstance(exc, (socket.timeout, TimeoutError)):
        return ModelProviderTimeout("FreeToken request timed out")
    if isinstance(exc, HTTPError):
        body = _bounded_error_body(exc)
        suffix = f": {body}" if body else ""
        if exc.code >= 500:
            return ModelProviderUnavailable(f"FreeToken HTTP {exc.code}{suffix}")
        return ModelProviderError(f"FreeToken HTTP {exc.code}{suffix}")
    if isinstance(exc, URLError):
        reason = getattr(exc, "reason", exc)
        if isinstance(reason, (socket.timeout, TimeoutError)):
            return ModelProviderTimeout("FreeToken request timed out")
        return ModelProviderUnavailable(f"FreeToken endpoint unavailable: {reason}")
    if isinstance(exc, OSError):
        return ModelProviderUnavailable(f"FreeToken endpoint unavailable: {exc}")
    return ModelProviderError(f"FreeToken request failed: {exc}")


class FreeTokenModelProvider:
    """Thin LAC-owned adapter over FreeToken v0.1.2's OpenAI-compatible endpoint.

    It performs inference translation only. There is intentionally no reference to
    policy, approval, leases, dispatcher, effects, sandbox credentials, or host
    credentials.
    """

    _CAPABILITIES = ModelProviderCapabilities(
        streaming=True,
        tools=True,
        reasoning=True,
        structured_output=False,
        seed=False,
        cancellation=True,
    )

    def __init__(self, *, base_url: str = "http://127.0.0.1:8000") -> None:
        self._base_url = _normalize_base_url(base_url)

    @property
    def capabilities(self) -> ModelProviderCapabilities:
        return self._CAPABILITIES

    @property
    def base_url(self) -> str:
        return self._base_url

    def translate_request(self, request: ModelRequest, *, stream: bool) -> dict[str, Any]:
        if not isinstance(request, ModelRequest):
            raise TypeError("request must be a ModelRequest")
        if request.seed is not None:
            raise ModelProviderCapabilityError(
                "FreeToken v0.1.2 has no seed field in ChatCompletionRequest; refusing silent seed loss"
            )
        if request.response_format is not None:
            raise ModelProviderCapabilityError(
                "FreeToken v0.1.2 rejects constrained response_format; structured output is unsupported"
            )

        payload: dict[str, Any] = {
            "model": request.model,
            "messages": [_deep_json_copy(dict(message)) for message in request.messages],
            "stream": bool(stream),
        }
        _optional_field(payload, "max_tokens", request.max_tokens)
        _optional_field(payload, "temperature", request.temperature)
        _optional_field(payload, "top_k", request.top_k)
        _optional_field(payload, "top_p", request.top_p)
        if request.stop is not None:
            payload["stop"] = request.stop if isinstance(request.stop, str) else list(request.stop)
        _optional_field(payload, "reasoning_effort", request.reasoning_effort)
        if request.tools:
            payload["tools"] = [_deep_json_copy(dict(tool)) for tool in request.tools]
        _optional_field(payload, "tool_choice", _deep_json_copy(request.tool_choice) if request.tool_choice is not None else None)
        if stream:
            payload["stream_options"] = {"include_usage": True}
        return payload

    def encode_request(self, request: ModelRequest, *, stream: bool) -> bytes:
        payload = self.translate_request(request, stream=stream)
        return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")

    def generate(
        self,
        request: ModelRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> ModelResponse:
        self._check_cancelled(cancellation)
        raw = self._post(request, stream=False)
        try:
            body = raw.read()
        except BaseException as exc:
            raw.close()
            raise _map_transport_error(exc) from exc
        finally:
            try:
                raw.close()
            except Exception:
                pass
        self._check_cancelled(cancellation)
        try:
            decoded = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelProviderMalformedResponse("FreeToken returned malformed JSON") from exc
        return self._normalize_response(decoded)

    def stream(
        self,
        request: ModelRequest,
        *,
        cancellation: CancellationToken | None = None,
    ) -> Iterator[ModelStreamEvent]:
        self._check_cancelled(cancellation)
        raw = self._post(request, stream=True)
        saw_done = False
        try:
            for raw_line in raw:
                self._check_cancelled(cancellation, raw=raw)
                try:
                    line = raw_line.decode("utf-8").strip()
                except UnicodeDecodeError as exc:
                    raise ModelProviderMalformedResponse("FreeToken stream was not UTF-8") from exc
                if not line or line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    raise ModelProviderMalformedResponse("FreeToken stream emitted a non-SSE data line")
                data = line[5:].strip()
                if data == "[DONE]":
                    saw_done = True
                    yield ModelStreamEvent("done")
                    break
                try:
                    chunk = json.loads(data)
                except json.JSONDecodeError as exc:
                    raise ModelProviderMalformedResponse("FreeToken stream emitted malformed JSON") from exc
                yield from self._normalize_stream_chunk(chunk)
            if not saw_done:
                raise ModelProviderMalformedResponse("FreeToken stream ended without [DONE]")
        except ModelProviderError:
            raise
        except BaseException as exc:
            raise _map_transport_error(exc) from exc
        finally:
            try:
                raw.close()
            except Exception:
                pass

    def list_models(self, *, timeout_seconds: float = 10.0) -> tuple[Mapping[str, Any], ...]:
        if isinstance(timeout_seconds, bool) or not isinstance(timeout_seconds, (int, float)):
            raise ValueError("timeout_seconds must be numeric")
        if not 0 < float(timeout_seconds) <= 60:
            raise ValueError("timeout_seconds must be within (0, 60]")
        request = UrlRequest(f"{self._base_url}/v1/models", method="GET")
        try:
            with urlopen(request, timeout=float(timeout_seconds)) as response:
                body = response.read()
        except BaseException as exc:
            raise _map_transport_error(exc) from exc
        try:
            payload = json.loads(body.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ModelProviderMalformedResponse("FreeToken /v1/models returned malformed JSON") from exc
        if not isinstance(payload, Mapping) or payload.get("object") != "list" or not isinstance(payload.get("data"), list):
            raise ModelProviderMalformedResponse("FreeToken /v1/models response shape is invalid")
        models: list[Mapping[str, Any]] = []
        for item in payload["data"]:
            if not isinstance(item, Mapping) or not isinstance(item.get("id"), str) or not item["id"]:
                raise ModelProviderMalformedResponse("FreeToken /v1/models contains an invalid model card")
            models.append(copy.deepcopy(dict(item)))
        return tuple(models)

    def _post(self, request: ModelRequest, *, stream: bool):
        data = self.encode_request(request, stream=stream)
        http_request = UrlRequest(
            f"{self._base_url}/v1/chat/completions",
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "text/event-stream" if stream else "application/json",
            },
        )
        try:
            return urlopen(http_request, timeout=float(request.timeout_seconds))
        except BaseException as exc:
            raise _map_transport_error(exc) from exc

    @staticmethod
    def _check_cancelled(cancellation: CancellationToken | None, *, raw: Any | None = None) -> None:
        if cancellation is not None and cancellation.cancelled:
            if raw is not None:
                try:
                    raw.close()
                except Exception:
                    pass
            raise ModelProviderCancelled("FreeToken request cancelled")

    @staticmethod
    def _normalize_usage(raw: object) -> ModelUsage:
        if not isinstance(raw, Mapping):
            raise ModelProviderMalformedResponse("FreeToken response usage must be an object")
        prompt = raw.get("prompt_tokens")
        completion = raw.get("completion_tokens")
        total = raw.get("total_tokens")
        for name, value in (("prompt_tokens", prompt), ("completion_tokens", completion), ("total_tokens", total)):
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise ModelProviderMalformedResponse(f"FreeToken usage.{name} must be a non-negative integer")
        cached = 0
        details = raw.get("prompt_tokens_details")
        if details is not None:
            if not isinstance(details, Mapping):
                raise ModelProviderMalformedResponse("FreeToken prompt_tokens_details must be an object")
            cached_value = details.get("cached_tokens", 0)
            if isinstance(cached_value, bool) or not isinstance(cached_value, int) or cached_value < 0:
                raise ModelProviderMalformedResponse("FreeToken cached_tokens must be a non-negative integer")
            cached = cached_value
        try:
            return ModelUsage(prompt, completion, total, cached)
        except ValueError as exc:
            raise ModelProviderMalformedResponse(str(exc)) from exc

    @classmethod
    def _normalize_response(cls, payload: object) -> ModelResponse:
        if not isinstance(payload, Mapping):
            raise ModelProviderMalformedResponse("FreeToken response must be a JSON object")
        if payload.get("object") != "chat.completion":
            raise ModelProviderMalformedResponse("FreeToken response object must be chat.completion")
        response_id = payload.get("id")
        model = payload.get("model")
        choices = payload.get("choices")
        if not isinstance(response_id, str) or not response_id:
            raise ModelProviderMalformedResponse("FreeToken response id is missing")
        if not isinstance(model, str) or not model:
            raise ModelProviderMalformedResponse("FreeToken response model is missing")
        if not isinstance(choices, list) or len(choices) != 1 or not isinstance(choices[0], Mapping):
            raise ModelProviderMalformedResponse("FreeToken response must contain exactly one choice")
        choice = choices[0]
        message = choice.get("message")
        if not isinstance(message, Mapping) or message.get("role") != "assistant":
            raise ModelProviderMalformedResponse("FreeToken choice.message must be an assistant message")
        content = message.get("content")
        if content is not None and not isinstance(content, str):
            raise ModelProviderMalformedResponse("FreeToken assistant content must be string or null")
        reasoning = message.get("reasoning_content")
        if reasoning is not None and not isinstance(reasoning, str):
            raise ModelProviderMalformedResponse("FreeToken reasoning_content must be string or null")
        tool_calls = message.get("tool_calls", [])
        if tool_calls is None:
            tool_calls = []
        if not isinstance(tool_calls, list) or any(not isinstance(item, Mapping) for item in tool_calls):
            raise ModelProviderMalformedResponse("FreeToken tool_calls must be an array of objects")
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None and not isinstance(finish_reason, str):
            raise ModelProviderMalformedResponse("FreeToken finish_reason must be string or null")
        return ModelResponse(
            response_id=response_id,
            model=model,
            content=content,
            reasoning=reasoning,
            tool_calls=tuple(copy.deepcopy(dict(item)) for item in tool_calls),
            finish_reason=finish_reason,
            usage=cls._normalize_usage(payload.get("usage")),
        )

    @classmethod
    def _normalize_stream_chunk(cls, payload: object) -> Iterator[ModelStreamEvent]:
        if not isinstance(payload, Mapping):
            raise ModelProviderMalformedResponse("FreeToken stream chunk must be a JSON object")
        if "error" in payload:
            raise ModelProviderError(f"FreeToken stream error: {payload['error']}")
        if payload.get("object") != "chat.completion.chunk":
            raise ModelProviderMalformedResponse("FreeToken stream object must be chat.completion.chunk")
        choices = payload.get("choices")
        if not isinstance(choices, list):
            raise ModelProviderMalformedResponse("FreeToken stream choices must be an array")
        if not choices:
            if "usage" not in payload:
                raise ModelProviderMalformedResponse("FreeToken empty-choice stream chunk must carry usage")
            yield ModelStreamEvent("usage", cls._normalize_usage(payload["usage"]))
            return
        if len(choices) != 1 or not isinstance(choices[0], Mapping):
            raise ModelProviderMalformedResponse("FreeToken stream must contain at most one choice")
        choice = choices[0]
        delta = choice.get("delta")
        if not isinstance(delta, Mapping):
            raise ModelProviderMalformedResponse("FreeToken stream choice.delta must be an object")
        content = delta.get("content")
        if content is not None:
            if not isinstance(content, str):
                raise ModelProviderMalformedResponse("FreeToken stream content delta must be a string")
            if content:
                yield ModelStreamEvent("text_delta", content)
        reasoning = delta.get("reasoning_content")
        if reasoning is not None:
            if not isinstance(reasoning, str):
                raise ModelProviderMalformedResponse("FreeToken stream reasoning delta must be a string")
            if reasoning:
                yield ModelStreamEvent("reasoning_delta", reasoning)
        tool_calls = delta.get("tool_calls")
        if tool_calls is not None:
            if not isinstance(tool_calls, list) or any(not isinstance(item, Mapping) for item in tool_calls):
                raise ModelProviderMalformedResponse("FreeToken stream tool_calls delta must be an array of objects")
            if tool_calls:
                yield ModelStreamEvent("tool_call_delta", tuple(copy.deepcopy(dict(item)) for item in tool_calls))
        finish_reason = choice.get("finish_reason")
        if finish_reason is not None:
            if not isinstance(finish_reason, str):
                raise ModelProviderMalformedResponse("FreeToken stream finish_reason must be a string")
            yield ModelStreamEvent("finish", finish_reason)
        if "usage" in payload and payload["usage"] is not None:
            yield ModelStreamEvent("usage", cls._normalize_usage(payload["usage"]))
