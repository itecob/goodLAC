# ModelProvider Contract — Phase 3 A002

## Purpose

`ModelProvider` is LAC's replaceable inference boundary. It carries model/runtime data only. It is not an authorization boundary and cannot approve, lease, dispatch, or execute effects.

```text
Pi / AgentAdapter
        |
        v
LAC ModelProvider
        |
        v
FreeToken local HTTP inference endpoint
```

The first implementation is `FreeTokenModelProvider`, pinned to FreeToken `0.1.2` at commit
`af71ba43206e124f5ff6419b47ee36c6e9981078`.

## LAC-owned request surface

`ModelRequest` contains only:

- model id;
- conversation messages;
- output/token budget;
- sampling controls (`temperature`, `top_k`, `top_p`, `stop`);
- reasoning effort;
- model tool schemas/tool choice;
- optional structured-output/seed requests for providers that support them;
- bounded request timeout.

It contains no principal, approval, decision, lease, request, executor, idempotency, dispatcher,
effect-adapter, service credential, password, bearer token, or API-key field.

## LAC-owned response surface

`ModelResponse` normalizes:

- response id and model id;
- assistant text;
- reasoning text;
- tool-call proposals;
- finish reason;
- input/output/total/cached token usage.

Streaming is normalized into `ModelStreamEvent` values for text, reasoning, tool-call deltas,
finish, usage, and terminal completion.

Tool calls are model proposals only. They acquire no LAC authority by crossing this boundary.

## FreeToken v0.1.2 capability profile

The pinned native OpenAI-compatible API supplies:

- `POST /v1/chat/completions`;
- `GET /v1/models`;
- SSE streaming with `[DONE]`;
- tools/tool choice;
- reasoning content;
- token usage;
- `temperature`, `top_k`, `top_p`, `max_tokens`, and stop controls.

The pinned interface does **not** expose a seed field. LAC therefore rejects non-null `seed`
instead of silently dropping it.

The pinned server explicitly rejects constrained `response_format` JSON object/schema requests.
LAC therefore reports structured output as unsupported for this provider and rejects such
requests before contacting the runtime.

## Endpoint and credential boundary

A002 accepts explicit loopback HTTP endpoints only (`localhost`, `127.0.0.1`, or `::1`).
Credentials embedded in endpoint URLs are rejected. The FreeToken adapter has no API-key or
service-credential parameter and does not add authorization headers.

This is intentionally narrower than a generic remote OpenAI-compatible client. Remote/provider
credentials belong in a future provider-specific integration, not in this local FreeToken
adapter.

## Failure semantics

The adapter fails closed on:

- unavailable endpoint;
- HTTP server errors;
- malformed JSON;
- malformed response/chunk shape;
- stream termination without `[DONE]`;
- unsupported seed or structured-output requests;
- timeout;
- cancellation.

A model-runtime failure never changes policy, approval, lease, dispatcher, effect, or sandbox
state.

## Replacement rule

LAC owns `ModelRequest`, `ModelResponse`, `ModelUsage`, `ModelStreamEvent`, cancellation, and
provider error semantics. FreeToken-specific wire translation stays under
`packages/adapters/freetoken/`. Replacing FreeToken must not require changes to the authority
core or effect adapters.
