# Integrating goodLAC

This document defines the architectural conditions that must be true for an agent system to be represented as **goodLAC-governed**.

It is independent of a particular model, inference layer, or agent harness.

> **Model output is not authorization.**

## Terminology

- **model** — the language/reasoning model, such as Qwen, Llama, GPT, Claude, or Gemma;
- **inference layer** — whatever makes a model available to the agent harness, such as a local inference runtime or remote model API;
- **agent harness / agent application** — software around the model that manages the agent loop, context and tool use, for example Pi, Codex, Claude Code, Hermes Agent, or a custom application;
- **goodLAC integration contract** — the security/interface requirements at the boundary between the harness/application and goodLAC;
- **consequential effect** — an operation that changes or reveals consequential state, such as filesystem mutation, shell execution, external API action, browser action, database mutation, message send, or cloud/service operation.

Vendors may use different terms such as agent, framework, CLI, runtime, or application. These terms are used here to make the architecture explicit.

## Trust structure

```text
Model
  |
  v
Inference layer
  |
  v
Agent harness / application
  |
  | goodLAC integration contract
  v
goodLAC
  |
  v
Consequential effects / effect systems
```

The products may differ. The trust relationship must not.

goodLAC governs effects. It does not need to own model selection or inference compatibility.

## Required property 1 — complete mediation

Every consequential effect path available to the agent must cross the goodLAC authorization boundary before the effect occurs.

A system is **not** goodLAC-governed merely because the agent can call goodLAC.

Broken:
```text
Agent harness
   | \
   |  \----> direct shell / direct API / alternate mutation tool
   v
goodLAC
   |
   v
governed effect
```

Required:
```text
Agent harness
   |
   | only consequential-effect path
   v
goodLAC
   |
   v
effect executor / external system
```

### Duplicate-path test

For every consequential capability, ask:

> Can the agent produce this same consequential effect through any executable path that does not cross goodLAC?

If yes, the integration is incomplete.

Inspect at least:
- unrestricted shell/code execution;
- second filesystem mutation tools;
- browser/desktop automation;
- MCP/plugin/tool servers with overlapping effects;
- direct API clients carrying service credentials;
- privileged local sockets/services;
- direct effect adapters/executors;
- fallback behavior that bypasses goodLAC.

This is illustrative, not exhaustive.

## Required property 2 — model output does not establish authority

The model may propose an effect. It must not create/alter policy, create approval, choose an authority outcome, grant itself capability, establish trusted identity merely by asserting it, obtain governed-effect credentials, or choose an alternate path that grants greater authority.

## Required property 3 — trusted identity and context binding

Authorization-relevant context must be controller-owned or controller-verified.

Depending on the applicable goodLAC contract, this can include principal/user, project/application, agent/session, capability/action/resource, exact request, approval subject, and idempotency/replay identity.

Prompt text is not a trusted identity mechanism.

The existing goodLAC external/native consumer contracts already reject authority-bearing fields that belong to the controller.

## Required property 4 — credential and privileged-executor separation

The untrusted model/agent context must not receive credentials or privileged access that lets it perform a governed effect directly.

Examples include service API tokens, OAuth tokens, cloud/SSH credentials, privileged sockets, administrator interfaces, and unrestricted host executors.

If the model/harness can use the same credential or executor independently of goodLAC, it may route around the authority boundary.

## Required property 5 — fail closed

If goodLAC cannot establish required trusted state, the effect must not occur.

This includes failure of identity/context binding, capability validity, current policy, exact approval validity, emergency state, dispatch integrity, controller communication, and request/replay integrity.

Never implement: "goodLAC is unavailable, so execute directly."

## Required property 6 — preserve goodLAC authority semantics

An integration surface is an input/transport edge. It must not become a second authority system.

Harness-specific code must not independently own canonical standing policy, exact approval, capability authority, leases, receipts, emergency authorization state, or credential authority.

Reuse existing goodLAC contracts where they fit rather than creating parallel authority.

## Reference configurations versus compatibility

A tested configuration is not a certification program.

- **tested** — actually exercised by the project;
- **expected compatible** — should be integrable when the contract is satisfied;
- **untested/unverified** — not independently exercised by the project.

Untested does not mean prohibited. Tested does not mean guaranteed, certified, or permanently approved.

## Integration procedure

### Step 1 — identify the layers

Record the harness/application, inference layer, model selection mechanism, user/project/session identity source, available tools/plugins/MCP/extensions, effect destinations, and credentials/privileged executors.

### Step 2 — inventory consequential capabilities

List every capability through which the agent can mutate files, execute processes/code, send external requests/messages, control browser/desktop state, change databases/cloud/service state, expose sensitive information, or perform another consequential operation.

Do not limit this inventory to tools already connected to goodLAC.

### Step 3 — enumerate effect paths

For each capability, enumerate every executable path from the harness to the effect.

Two tools that can mutate the same state are two paths. A directly usable service credential creates a direct API path.

### Step 4 — eliminate or govern bypasses

For every path that does not cross goodLAC, remove it, disable it, isolate it, replace it with a goodLAC-backed path, or place it behind an equivalent governed boundary.

Do not label the deployment goodLAC-governed while an equivalent ungoverned path remains.

### Step 5 — establish trusted identity/context

Determine which authorization-relevant values must be bound outside model control.

Do not rely on prompts telling the model which identity/project to report.

### Step 6 — isolate credentials and privileged execution

Ensure the model/agent process cannot directly obtain credentials, privileged sockets, administrator endpoints, or executors used by governed effects.

### Step 7 — map requests to the goodLAC contract

Use an existing goodLAC consumer/runtime contract where it fits. Do not add policy/approval authority to the harness merely to simplify integration.

### Step 8 — define failure behavior

For every required goodLAC dependency, document what happens when unavailable/invalid. Consequential effects must fail closed.

### Step 9 — validate the architecture

Attempt to find a model-to-effect path that does not cross goodLAC.

Inspect built-in tools, plugins/extensions, MCP/tool servers, shell/code execution, filesystem/network/browser access, inherited environment, credentials, local sockets/services, subprocess authority, and fallback/error modes.

A policy `DENY` response is not evidence that an alternate OS/runtime path is unavailable. Validate actual effect paths.

### Step 10 — record evidence

Record the integration map, disabled/removed bypasses, trusted identity/context source, credential boundary, goodLAC contract used, failure-mode tests, attempted bypass tests, and remaining limitations.

## Invalid deployment examples

- goodLAC shell plus unrestricted second shell;
- governed API adapter plus model-visible service credential;
- goodLAC installed while native mutation tools remain unrestricted;
- authorization identity supplied only in model text;
- controller outage that falls back to direct execution.

## Coding-agent implementation instructions

If you are an AI coding agent integrating goodLAC into another system:

1. Do not start by editing code.
2. Produce the integration map above.
3. Identify all consequential effect paths, including native/built-in tools.
4. Mark each path `GOVERNED`, `REMOVE/DISABLE`, or `NONCONSEQUENTIAL`, with a reason.
5. Identify every authorization-relevant field and its trusted source.
6. Identify every credential/privileged executor and show how it is inaccessible to the untrusted model context.
7. Identify the existing goodLAC contract you will reuse.
8. State all required code/configuration changes.
9. State how controller failure will fail closed.
10. State validation tests that prove bypass resistance.
11. Do not invent a new approval, policy, identity, credential, or lease authority in the harness.
12. Do not claim the integration is goodLAC-governed until validation passes.

If required security information is missing, surface the missing requirement rather than guessing an authorization boundary.

## Agent-operability acceptance criteria

Documentation is sufficiently explicit only if a capable general-purpose coding agent, given this repository and an unfamiliar harness architecture, can produce without undocumented assumptions:

- an architecture map;
- a consequential-capability inventory;
- an alternate-path/bypass inventory;
- a trusted identity/context plan;
- a credential-separation plan;
- the applicable goodLAC contract mapping;
- fail-closed behavior;
- a bounded implementation plan;
- a verification plan that tests actual effects rather than trusting model responses.

If the agent must guess a security-critical requirement, the documentation is incomplete.

## Operator responsibility

goodLAC can govern only effect paths placed behind its authority boundary. The project cannot prevent an operator from exposing a second ungoverned path, credential, privileged executor, or administrator interface to the agent.

Operators integrating an untested harness/application are responsible for ensuring their architecture satisfies this integration contract before representing it as goodLAC-governed.

## Related documents

- [`ARCHITECTURE.md`](ARCHITECTURE.md)
- [`CONTRACTS.md`](CONTRACTS.md)
- [`NATIVE_LOCAL_CONSUMER_CONTRACT.md`](NATIVE_LOCAL_CONSUMER_CONTRACT.md)
- [`B003_EXTERNAL_CONSUMER_INTEGRATION.md`](B003_EXTERNAL_CONSUMER_INTEGRATION.md)
- [`THREAT_MODEL.md`](THREAT_MODEL.md)
