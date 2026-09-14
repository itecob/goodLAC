from __future__ import annotations

import json
import socket
import threading
import time
import unittest
from dataclasses import fields
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any

from packages.adapters.freetoken import FreeTokenModelProvider
from packages.model_provider import (
    CancellationToken,
    ModelProviderCapabilityError,
    ModelProviderCancelled,
    ModelProviderMalformedResponse,
    ModelProviderTimeout,
    ModelProviderUnavailable,
    ModelRequest,
    ModelUsage,
)


class _State:
    request_body: dict[str, Any] | None = None


class _Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, fmt: str, *args: object) -> None:
        return

    def _json(self, status: int, payload: object) -> None:
        body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        try:
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._json(
                200,
                {
                    "object": "list",
                    "data": [
                        {
                            "id": "fixture-model",
                            "object": "model",
                            "owned_by": "FreeToken",
                            "root": "/fixture",
                            "context_length": 4096,
                        }
                    ],
                },
            )
            return
        self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw.decode("utf-8"))
        except Exception:
            self._json(400, {"error": "bad json"})
            return
        _State.request_body = payload
        model = payload.get("model")
        if model == "slow-model":
            time.sleep(0.25)
        if model == "malformed-model":
            self._json(200, {"unexpected": True})
            return
        if payload.get("stream"):
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream")
            self.send_header("Connection", "close")
            self.end_headers()
            chunks = [
                {
                    "id": "chatcmpl-fixture",
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}],
                },
                {
                    "id": "chatcmpl-fixture",
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [{"index": 0, "delta": {"reasoning_content": "r"}, "finish_reason": None}],
                },
                {
                    "id": "chatcmpl-fixture",
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [{"index": 0, "delta": {"content": "ok"}, "finish_reason": None}],
                },
                {
                    "id": "chatcmpl-fixture",
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                },
                {
                    "id": "chatcmpl-fixture",
                    "object": "chat.completion.chunk",
                    "model": model,
                    "choices": [],
                    "usage": {
                        "prompt_tokens": 3,
                        "completion_tokens": 2,
                        "total_tokens": 5,
                        "prompt_tokens_details": {"cached_tokens": 1},
                    },
                },
            ]
            try:
                for chunk in chunks:
                    self.wfile.write(
                        b"data: " + json.dumps(chunk, separators=(",", ":")).encode("utf-8") + b"\n\n"
                    )
                    self.wfile.flush()
                self.wfile.write(b"data: [DONE]\n\n")
                self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                return
            return

        self._json(
            200,
            {
                "id": "chatcmpl-fixture",
                "object": "chat.completion",
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": "ok",
                            "reasoning_content": "r",
                            "tool_calls": [
                                {
                                    "id": "call-1",
                                    "type": "function",
                                    "function": {"name": "lac_fs_read", "arguments": "{\"path\":\"x\"}"},
                                }
                            ],
                        },
                        "finish_reason": "tool_calls",
                    }
                ],
                "usage": {
                    "prompt_tokens": 3,
                    "completion_tokens": 2,
                    "total_tokens": 5,
                    "prompt_tokens_details": {"cached_tokens": 1},
                },
            },
        )


class _Server:
    def __enter__(self) -> str:
        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), _Handler)
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.httpd.server_address
        return f"http://{host}:{port}"

    def __exit__(self, exc_type, exc, tb) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=2)


def _request(model: str = "fixture-model", **overrides: Any) -> ModelRequest:
    values: dict[str, Any] = {
        "model": model,
        "messages": ({"role": "user", "content": "hello"},),
        "max_tokens": 32,
        "temperature": 0.0,
        "top_k": 1,
        "top_p": 1.0,
        "stop": ("END",),
        "reasoning_effort": "low",
        "tools": (
            {
                "type": "function",
                "function": {
                    "name": "lac_fs_read",
                    "description": "fixture",
                    "parameters": {"type": "object", "properties": {"path": {"type": "string"}}},
                },
            },
        ),
        "tool_choice": "auto",
        "timeout_seconds": 2.0,
    }
    values.update(overrides)
    return ModelRequest(**values)


class FreeTokenProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        _State.request_body = None

    def test_loopback_only_and_no_url_credentials(self) -> None:
        for bad in (
            "https://127.0.0.1:8000",
            "http://example.com:8000",
            "http://user:pass@127.0.0.1:8000",
            "http://127.0.0.1:8000/other",
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    FreeTokenModelProvider(base_url=bad)

    def test_request_translation_is_deterministic_and_propagates_supported_settings(self) -> None:
        provider = FreeTokenModelProvider()
        request = _request()
        first = provider.encode_request(request, stream=True)
        second = provider.encode_request(request, stream=True)
        self.assertEqual(first, second)
        payload = json.loads(first)
        self.assertEqual(payload["model"], "fixture-model")
        self.assertEqual(payload["temperature"], 0.0)
        self.assertEqual(payload["top_k"], 1)
        self.assertEqual(payload["top_p"], 1.0)
        self.assertEqual(payload["max_tokens"], 32)
        self.assertEqual(payload["stop"], ["END"])
        self.assertEqual(payload["reasoning_effort"], "low")
        self.assertEqual(payload["tool_choice"], "auto")
        self.assertEqual(payload["stream_options"], {"include_usage": True})
        self.assertNotIn("api_key", payload)
        self.assertNotIn("authorization", payload)

    def test_unsupported_seed_and_structured_output_fail_closed(self) -> None:
        provider = FreeTokenModelProvider()
        self.assertFalse(provider.capabilities.seed)
        self.assertFalse(provider.capabilities.structured_output)
        with self.assertRaises(ModelProviderCapabilityError):
            provider.translate_request(_request(seed=7), stream=False)
        with self.assertRaises(ModelProviderCapabilityError):
            provider.translate_request(
                _request(response_format={"type": "json_schema", "json_schema": {"name": "x"}}),
                stream=False,
            )

    def test_generate_normalizes_response_and_usage(self) -> None:
        with _Server() as base:
            provider = FreeTokenModelProvider(base_url=base)
            response = provider.generate(_request())
        self.assertEqual(response.response_id, "chatcmpl-fixture")
        self.assertEqual(response.model, "fixture-model")
        self.assertEqual(response.content, "ok")
        self.assertEqual(response.reasoning, "r")
        self.assertEqual(response.finish_reason, "tool_calls")
        self.assertEqual(response.tool_calls[0]["function"]["name"], "lac_fs_read")
        self.assertEqual(response.usage, ModelUsage(3, 2, 5, 1))
        self.assertEqual(_State.request_body["messages"], [{"role": "user", "content": "hello"}])

    def test_stream_normalizes_reasoning_text_finish_usage_and_done(self) -> None:
        with _Server() as base:
            provider = FreeTokenModelProvider(base_url=base)
            events = list(provider.stream(_request()))
        self.assertEqual(
            [(event.kind, event.value) for event in events],
            [
                ("reasoning_delta", "r"),
                ("text_delta", "ok"),
                ("finish", "stop"),
                ("usage", ModelUsage(3, 2, 5, 1)),
                ("done", None),
            ],
        )

    def test_stream_cancellation_closes_on_next_chunk(self) -> None:
        token = CancellationToken()
        with _Server() as base:
            provider = FreeTokenModelProvider(base_url=base)
            stream = provider.stream(_request(), cancellation=token)
            first = next(stream)
            self.assertEqual((first.kind, first.value), ("reasoning_delta", "r"))
            token.cancel()
            with self.assertRaises(ModelProviderCancelled):
                next(stream)

    def test_models_endpoint_is_normalized(self) -> None:
        with _Server() as base:
            provider = FreeTokenModelProvider(base_url=base)
            models = provider.list_models()
        self.assertEqual(models[0]["id"], "fixture-model")
        self.assertEqual(models[0]["context_length"], 4096)

    def test_malformed_response_fails_closed(self) -> None:
        with _Server() as base:
            provider = FreeTokenModelProvider(base_url=base)
            with self.assertRaises(ModelProviderMalformedResponse):
                provider.generate(_request("malformed-model"))

    def test_unavailable_runtime_fails_closed(self) -> None:
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
        sock.close()
        provider = FreeTokenModelProvider(base_url=f"http://127.0.0.1:{port}")
        with self.assertRaises(ModelProviderUnavailable):
            provider.generate(_request(timeout_seconds=0.1))

    def test_timeout_is_bounded_and_fails_closed(self) -> None:
        with _Server() as base:
            provider = FreeTokenModelProvider(base_url=base)
            with self.assertRaises(ModelProviderTimeout):
                provider.generate(_request("slow-model", timeout_seconds=0.05))

    def test_precancel_fails_without_contacting_runtime(self) -> None:
        token = CancellationToken()
        token.cancel()
        provider = FreeTokenModelProvider()
        with self.assertRaises(ModelProviderCancelled):
            provider.generate(_request(), cancellation=token)

    def test_model_request_has_no_authority_or_credential_fields(self) -> None:
        names = {field.name for field in fields(ModelRequest)}
        forbidden = {
            "approval_id",
            "decision_id",
            "dispatcher",
            "executor_id",
            "idempotency_key",
            "lease_id",
            "principal_id",
            "request_id",
            "run_id",
            "api_key",
            "authorization",
            "credential",
            "password",
            "secret",
            "service_token",
        }
        self.assertFalse(names & forbidden)

    def test_freetoken_adapter_has_no_authority_module_imports(self) -> None:
        source = (Path(__file__).resolve().parents[2] / "packages/adapters/freetoken/provider.py").read_text(
            encoding="utf-8"
        )
        for forbidden in (
            "packages.dispatcher",
            "packages.effects",
            "packages.policy",
            "packages.state",
            "packages.sandbox",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
