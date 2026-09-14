#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from dataclasses import asdict, is_dataclass
from pathlib import Path
from typing import Any, Mapping

# This file is spawned as a script by the Pi stream bridge. Direct execution
# otherwise exposes only <repo>/scripts on sys.path. Resolve and prepend the
# repository root explicitly before importing LAC-owned provider code.
REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.adapters.freetoken import FreeTokenModelProvider
from packages.model_provider import ModelRequest


def fail(message: str) -> None:
    print(json.dumps({"kind": "error", "message": message}, sort_keys=True), flush=True)
    raise SystemExit(0)


def text_content(value: object) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        raise ValueError("Pi message content must be text or a text-content array")
    parts: list[str] = []
    for block in value:
        if not isinstance(block, Mapping) or block.get("type") != "text" or not isinstance(block.get("text"), str):
            raise ValueError("A003 supports text-only Pi messages at the local model boundary")
        parts.append(block["text"])
    return "\n".join(parts)


def assistant_message(message: Mapping[str, Any]) -> dict[str, Any]:
    content = message.get("content")
    if not isinstance(content, list):
        raise ValueError("assistant content must be an array")
    texts: list[str] = []
    reasoning: list[str] = []
    calls: list[dict[str, Any]] = []
    for block in content:
        if not isinstance(block, Mapping):
            raise ValueError("assistant content block must be an object")
        kind = block.get("type")
        if kind == "text":
            if not isinstance(block.get("text"), str):
                raise ValueError("assistant text block is malformed")
            texts.append(block["text"])
        elif kind == "thinking":
            if not isinstance(block.get("thinking"), str):
                raise ValueError("assistant thinking block is malformed")
            reasoning.append(block["thinking"])
        elif kind == "toolCall":
            call_id = block.get("id")
            name = block.get("name")
            arguments = block.get("arguments")
            if not isinstance(call_id, str) or not call_id or not isinstance(name, str) or not name:
                raise ValueError("assistant tool call is missing id/name")
            if not isinstance(arguments, Mapping):
                raise ValueError("assistant tool-call arguments must be an object")
            calls.append(
                {
                    "id": call_id,
                    "type": "function",
                    "function": {
                        "name": name,
                        "arguments": json.dumps(dict(arguments), sort_keys=True, separators=(",", ":")),
                    },
                }
            )
        else:
            raise ValueError(f"unsupported assistant content block: {kind!r}")
    result: dict[str, Any] = {"role": "assistant", "content": "\n".join(texts) if texts else None}
    if reasoning:
        result["reasoning_content"] = "\n".join(reasoning)
    if calls:
        result["tool_calls"] = calls
    return result


def translate_context(context: Mapping[str, Any]) -> tuple[tuple[dict[str, Any], ...], tuple[dict[str, Any], ...]]:
    messages: list[dict[str, Any]] = []
    system = context.get("systemPrompt")
    if system:
        if not isinstance(system, str):
            raise ValueError("systemPrompt must be a string")
        messages.append({"role": "system", "content": system})
    raw_messages = context.get("messages")
    if not isinstance(raw_messages, list):
        raise ValueError("Pi context.messages must be an array")
    for message in raw_messages:
        if not isinstance(message, Mapping):
            raise ValueError("Pi message must be an object")
        role = message.get("role")
        if role == "user":
            messages.append({"role": "user", "content": text_content(message.get("content"))})
        elif role == "assistant":
            messages.append(assistant_message(message))
        elif role == "toolResult":
            call_id = message.get("toolCallId")
            if not isinstance(call_id, str) or not call_id:
                raise ValueError("tool result is missing toolCallId")
            messages.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": text_content(message.get("content")),
            })
        else:
            raise ValueError(f"unsupported Pi message role: {role!r}")

    tools: list[dict[str, Any]] = []
    raw_tools = context.get("tools") or []
    if not isinstance(raw_tools, list):
        raise ValueError("Pi context.tools must be an array")
    for tool in raw_tools:
        if not isinstance(tool, Mapping):
            raise ValueError("Pi tool definition must be an object")
        name = tool.get("name")
        description = tool.get("description")
        parameters = tool.get("parameters")
        if not isinstance(name, str) or not name or not isinstance(description, str) or not isinstance(parameters, Mapping):
            raise ValueError("Pi tool definition is malformed")
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": dict(parameters),
            },
        })
    return tuple(messages), tuple(tools)


def serializable(value: object) -> object:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return [serializable(item) for item in value]
    if isinstance(value, list):
        return [serializable(item) for item in value]
    if isinstance(value, Mapping):
        return {str(k): serializable(v) for k, v in value.items()}
    return value


def main() -> None:
    try:
        payload = json.load(sys.stdin)
        if not isinstance(payload, Mapping):
            raise ValueError("bridge request must be a JSON object")
        model = payload.get("model")
        context = payload.get("context")
        options = payload.get("options") or {}
        if not isinstance(model, str) or not model or not isinstance(context, Mapping) or not isinstance(options, Mapping):
            raise ValueError("bridge request is missing model/context/options")
        messages, tools = translate_context(context)
        reasoning = options.get("reasoning")
        if reasoning == "off":
            reasoning = None
        request = ModelRequest(
            model=model,
            messages=messages,
            max_tokens=int(options.get("maxTokens") or 1024),
            temperature=float(options.get("temperature") if options.get("temperature") is not None else 0.0),
            reasoning_effort=reasoning if isinstance(reasoning, str) and reasoning else None,
            tools=tools,
            tool_choice=str(options.get("toolChoice") or "auto") if tools else None,
            timeout_seconds=float(options.get("timeoutSeconds") or 300),
        )
        base_url = os.environ.get("LAC_A003_FREETOKEN_URL", "http://127.0.0.1:1919")
        provider = FreeTokenModelProvider(base_url=base_url)
        for event in provider.stream(request):
            print(json.dumps({"kind": event.kind, "value": serializable(event.value)}, sort_keys=True), flush=True)
        print(json.dumps({"kind": "done"}), flush=True)
    except BaseException as exc:
        fail(f"{type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
