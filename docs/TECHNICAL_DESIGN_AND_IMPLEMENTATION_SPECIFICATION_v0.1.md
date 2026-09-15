# LOCAL AGENT CONTROLLER

## Technical Design and Implementation Specification

### Planning Baseline v0.1

**Status:** Approved architecture baseline for implementation handoff
**Project type:** Standalone local-first software product
**Working project name:** Local Agent Controller (`LAC`)
**Primary target:** Linux / Omarchy, with architecture portable to other operating systems
**Primary model runtime for first end-to-end qualification:** FreeToken
**Primary agent harness for first end-to-end qualification:** Pi
**Secondary harness integration:** OpenClaw
**Project owner:** User
**Implementation model:** GPT-5.6 Sol, High reasoning effort for authority/security/runtime work
**Independent implementation reviewer:** separate GPT-5.6 Sol, High reasoning effort
**Development mechanism:** local project through Tunnel; implementation packages delivered to owner for execution using a single Bash command

---

# 1. Executive decision

Build a standalone **local-first Agent Authority Controller**, but do **not** build its constituent infrastructure from scratch.

The project will:

1. qualify and reuse mature open-source enforcement components where they satisfy requirements;
2. implement the missing local authority/effect semantics as a thin standalone control plane;
3. remain independent of:

   * model vendor;
   * inference runtime;
   * agent harness;
   * cloud provider;
   * application domain;
4. become a reusable dependency of:

   * the Chief of Staff project;
   * Omarchy Agent OS;
   * Pi-based agents;
   * OpenClaw-based agents;
   * future local agent applications.

The project will not attempt to create another inference engine, model gateway, general agent framework, cognition framework, memory system, workflow orchestrator, or AI operating system.

The central rule is:

> **The AI may propose an action. Deterministic software decides whether that action is authorized and whether it is permitted to become an effect.**

The controller must continue operating locally when the Internet is unavailable. Network connectivity may be required by a particular effect—such as sending Gmail—but never by the controller's policy, approval, state, audit, or enforcement functions.

---

# 2. Why this project exists

A useful local AI agent needs enough authority to act.

A safe local AI agent must not inherit unrestricted authority merely because the user running it possesses that authority.

These requirements conflict if the agent is launched directly under the user's account with:

* unrestricted filesystem access;
* shell access;
* browser profiles;
* OAuth credentials;
* API credentials;
* databases;
* email access;
* calendar access;
* SSH credentials;
* cloud credentials;
* application IPC;
* desktop automation.

Prompts do not resolve this conflict.

The required architecture is an actual authority boundary.

For example, a Chief of Staff must be capable of:

* reading email;
* searching email;
* drafting email;
* examining calendar events;
* preparing new events;
* reading relevant files;
* updating controlled working documents.

But the owner must be capable of independently declaring:

```text
email.read       ALLOW
email.draft      ALLOW
email.send       ASK (REQUIRE_APPROVAL)
email.delete     DENY

calendar.read    ALLOW
calendar.propose ALLOW
calendar.create  ASK (REQUIRE_APPROVAL)
calendar.modify  ASK (REQUIRE_APPROVAL)
calendar.cancel  ASK (REQUIRE_APPROVAL)
calendar.delete  DENY
```

Those decisions must remain effective even if:

* the model misunderstands;
* the model hallucinates;
* the harness retries incorrectly;
* an agent receives malicious content;
* a tool call is malformed;
* an agent asks for the same action repeatedly;
* an agent attempts to bypass an approval;
* the controller restarts;
* the model itself has no concept of the policy.

---

# 3. Definition of local-first

For this project, **local-first** is a technical contract.

The following must live on the user's machine:

* canonical controller state;
* policy definitions;
* policy decisions;
* agent identities;
* effect requests;
* approval requests;
* approval decisions;
* execution leases;
* audit events;
* effect receipts;
* emergency pause state;
* credential references;
* local execution boundaries;
* local model routing configuration.

The following may optionally be remote:

* an LLM provider;
* Gmail;
* Google Calendar;
* Slack;
* websites;
* cloud APIs;
* business SaaS applications.

Loss of those remote systems may prevent their associated action from completing, but must not corrupt or remove controller state.

No AWS, OpenAI, Anthropic, Preloop Cloud, or other SaaS service may be a required dependency for controller operation.

---

# 4. Upstream investigation and disposition

## 4.1 Airlock — PRIMARY IMPLEMENTATION CANDIDATE

**Repository:** `airlock-dev/airlock`
**License:** MIT
**Disposition:** **QUALIFY → ADOPT/WRAP if possible → DERIVE only if required**

Airlock is currently the strongest practical starting point.

It is a local permissions-aware MCP gateway with per-agent `allow`, `ask`, and `deny`, human-in-the-loop approvals, audit logging, CLI/OpenAPI/MCP tool exposure, local operation, and multiple approval surfaces. The repository is active and substantially more mature than most of the other specialized controller projects identified in this review.

It is also MIT licensed, which permits commercial use, modification and redistribution provided the required copyright/license notice is preserved.

### Airlock should be reused for

Potentially:

* MCP transport;
* downstream provider/tool registry;
* baseline tool policy;
* allow/ask/deny handling;
* existing HITL infrastructure;
* audit plumbing;
* local dashboard/TUI;
* CLI/OpenAPI discovery;
* agent-specific policy;
* compatibility-mode tool governance.

### Airlock must be specifically qualified for

The development team must inspect actual code, not rely solely on README claims, for:

* exact binding between approved request and executed request;
* approval expiry;
* one-time approval semantics;
* re-evaluation before execution;
* protection against request mutation after approval;
* durable state after restart;
* idempotency;
* kill-switch semantics;
* credential separation;
* TOCTOU behavior;
* sandbox implementation;
* whether agent-controlled arguments can escape declared policy;
* whether raw shell access can bypass higher-level restrictions;
* whether approval state is safe across concurrent requests.

### Decision gate

The implementation team is explicitly prohibited from forking Airlock merely because modifying source appears easier.

The decision order is:

```text
Can stock Airlock satisfy the invariant?
            │
         YES│
            ▼
    use upstream dependency

            NO
            │
            ▼
Can an extension/wrapper satisfy it?
            │
         YES│
            ▼
       wrap upstream

            NO
            │
            ▼
Can a small upstream-compatible patch satisfy it?
            │
         YES│
            ▼
maintain minimal patch / propose upstream

            NO
            │
            ▼
create MIT derivative of required modules
```

The default is **upstream reuse**, not fork ownership.

---

# 4.2 Preloop — BROAD REFERENCE / LAB CANDIDATE

**Repository:** `preloop/preloop`
**License:** Apache-2.0
**Disposition:** **QUALIFY IN LAB; DO NOT BASE v0.1 ON IT**

Preloop is much closer to a complete commercial control-plane product. Its open-source stack includes an MCP firewall, model gateway, policy-as-code, approvals, observability and audit, and it can be self-hosted locally. It explicitly supports existing local agent clients.

That is relevant evidence that this product category is real.

It is not the recommended v0.1 base because:

* its architecture is substantially broader than required;
* it combines governance with model gateway, automation and broader platform concerns;
* it has a heavier self-hosted stack;
* the project is comparatively young;
* some advanced functionality is edition-dependent;
* adopting it risks turning this project into administration of another platform rather than building the narrow reusable local authority boundary.

Apache-2.0 permits reuse under its terms, so individual designs or implementation pieces can be reconsidered later.

### Initial use

Run one bounded local qualification after the Airlock qualification.

If Preloop unexpectedly satisfies the entire required controller specification cleanly, this architecture decision may be revisited.

Otherwise, keep it as a competitor/reference implementation.

---

# 4.3 agentgateway — PROTOCOL/DATA-PLANE COMPONENT

**Repository:** `agentgateway/agentgateway`
**License:** Apache-2.0
**Disposition:** **DEFER AS OPTIONAL PROTOCOL GATEWAY**

agentgateway is a larger and more mature MCP/LLM/A2A gateway. It supports MCP authorization using CEL and can hide unauthorized tools from discovery as well as deny actual calls.

This makes it potentially valuable later for:

* multi-client identity;
* MCP routing;
* protocol authorization;
* distributed environments;
* richer gateway deployments;
* A2A;
* enterprise deployments.

It does **not** by itself solve the entire user-facing authority lifecycle.

There are also current security advisories and active edge cases that warrant careful version qualification rather than blind adoption. GitHub currently lists a high-severity 2026 advisory involving stateful MCP sessions crossing routes and overwriting authorization policy, plus other advisories.

Its authorization model also has current nuances around what MCP information exists at the policy-evaluation point; an August 2026 issue documents argument-dependent authorization expressions that cannot match at that stage.

### v0.1 rule

Do not stack agentgateway underneath or above Airlock merely because both exist.

That increases the trusted computing base without proving a need.

Introduce it only when a concrete requirement cannot be satisfied by the simpler architecture.

---

# 4.4 Stonefold — ARCHITECTURAL SPECIFICATION SOURCE

**Repository:** `stonefold-ai/stonefold`
**License:** Apache-2.0
**Disposition:** **REUSE SPECIFICATION/TCK IDEAS; DO NOT DEPLOY REFERENCE RUNTIME AS TRUSTED CORE**

Stonefold is extremely aligned with the intended controller philosophy.

It defines a deterministic checkpoint between an AI and consequential systems, uses typed **intents** rather than raw operations as its strong-governance abstraction, supports allow/deny/human hold, audit and an emergency stop, and provides a conformance kit.

But Stonefold explicitly describes its implementation as a:

> working proof-of-concept

and says it is not production-hardened.

Therefore:

**Do not deploy Stonefold itself as the trusted production controller.**

Use its architecture to inform:

* typed effect requests;
* strong versus compatibility interception;
* final pre-dispatch enforcement;
* declared action vocabularies;
* conformance testing;
* kill-switch design;
* intent-to-effect separation.

Apache-2.0 allows selective code/specification reuse if license and notice obligations are maintained.

Every copied implementation must be identified in `THIRD_PARTY_NOTICES.md`.

---

# 4.5 Waggle — CONCEPTUAL REFERENCE ONLY

**Repository:** `CrewBeeLab/Waggle`
**Disposition:** **IDEAS ONLY UNLESS LICENSE IS AUTHORITATIVELY RESOLVED**

Waggle has a very relevant architecture:

```text
Product owns:
business data
business rules
final writes

Waggle owns:
run lifecycle
permissions
tool proxy
workspace enforcement
confirmations
evidence

Runtime owns:
agent loop
model/tool mechanics
```

It currently uses Pi underneath while keeping runtime semantics behind an adapter boundary.

That is conceptually close to the desired architecture.

During this research I did not find a license surfaced by the repository results. Therefore the development team must treat the repository as **not licensed for code reuse until a license is authoritatively verified**.

No source code, tests or substantial documentation wording may be copied from Waggle unless licensing is resolved.

Its architectural ideas may be independently implemented.

---

# 4.6 OpenClaw — INTEGRATION TARGET + SECURITY REFERENCE

**Repository:** `openclaw/openclaw`
**License:** MIT
**Disposition:** **INTEGRATE; SELECTIVELY REUSE SECURITY PATTERNS**

OpenClaw now implements much stronger local execution governance than earlier versions.

Of particular interest is its approval-backed execution binding. Current documentation states that interpreter/runtime approvals bind exact argv, cwd and environment context, and deny cases where a single concrete executable/script cannot be reliably identified rather than claiming semantic safety.

That is the correct conservative approach.

OpenClaw is MIT licensed.

### Reuse

Study and selectively reuse or independently implement:

* canonical execution-plan generation;
* exact approval binding;
* safe-command semantics;
* approval expiry;
* async approval correlation;
* post-approval mismatch rejection.

### Do not

Do not make OpenClaw the universal authority controller.

It remains one harness/platform integration.

---

# 4.7 Pi — INITIAL HARNESS

**Repository:** `earendil-works/pi`
**Disposition:** **USE**

Pi provides an agent runtime, harness, tool calling, state management, unified model access and coding-agent tooling. Importantly, its current documentation explicitly states that Pi does **not** provide a built-in filesystem/process/network/credential permission boundary and normally runs with the permissions of its process.

That makes it useful for this project because the architectural responsibilities are clear:

```text
Pi = inference/agent loop

LAC = authority

Sandbox = hard process/filesystem/network boundary
```

The first implementation should prefer embedding or constructing Pi using its agent-core APIs with **only controller-backed tools** rather than launching the stock coding agent with unrestricted default Bash/read/edit/write tools. Current Pi source shows those tool surfaces are modularly created by the harness.

---

# 4.8 FreeToken — INITIAL LOCAL INFERENCE TARGET

**Repository:** `FlashML-org/FreeToken`
**License:** Apache-2.0
**Disposition:** **USE AS FIRST LOCAL MODEL ENDPOINT**

FreeToken is an inference runtime, not part of the controller.

Its package currently describes itself as a local MoE-offload inference runtime with OpenAI- and Anthropic-compatible APIs and identifies itself as Beta software under Apache-2.0.

Therefore the architecture will use a generic model endpoint abstraction.

The controller itself must not care whether inference comes from:

```text
FreeToken
llama.cpp
Ollama
vLLM
SGLang
remote OpenAI-compatible API
anything else
```

The first full local test will use FreeToken because it represents the local-first target architecture.

---

# 4.9 Cedar and OPA — POLICY ENGINES

**Disposition:** **DO NOT CREATE A NEW POLICY LANGUAGE/EVALUATOR**

OPA is an established Apache-2.0 general-purpose policy engine.

Cedar is purpose-built for authorization around:

```text
principal
action
resource
context
```

and now has TypeScript/JavaScript authorization tooling as well as other implementations. It is Apache-2.0.

### v0.1 decision

Do not force either engine into the first walking skeleton if Airlock's deterministic rules satisfy the MVP.

Instead create:

```text
PolicyDecisionProvider
```

as an internal interface.

Initial implementation may use:

```text
AirlockPolicyProvider
```

Later implementations may include:

```text
CedarPolicyProvider
OPAPolicyProvider
```

Cedar is currently the preferred long-term candidate because its principal/action/resource/context model maps naturally onto agent authority.

But it must earn inclusion through qualification; architecture cleanliness alone is not sufficient reason to add another component.

---

# 5. Licensing policy

This section is an engineering policy, not legal advice.

Before incorporating any external source at implementation time:

1. record repository;
2. record exact commit SHA;
3. record exact tag if one exists;
4. record license;
5. preserve required license files;
6. preserve required copyright notices;
7. record modified files if required by license;
8. record provenance in `THIRD_PARTY_NOTICES.md`;
9. record dependency in `UPSTREAM_LOCK.json`.

Licensing baseline:

| Project      | License                                                                             | Project use                       |
| ------------ | ----------------------------------------------------------------------------------- | --------------------------------- |
| Airlock      | MIT                                                                                 | preferred upstream/reuse          |
| Preloop      | Apache-2.0                                                                          | reference/lab/selective reuse     |
| agentgateway | Apache-2.0                                                                          | future optional component         |
| Stonefold    | Apache-2.0                                                                          | specification/TCK/selective reuse |
| Waggle       | unresolved in this review                                                           | concepts only                     |
| OpenClaw     | MIT                                                                                 | integration + selective patterns  |
| Pi           | open-source project; exact distribution license must be locked during qualification | harness                           |
| FreeToken    | Apache-2.0                                                                          | external runtime                  |
| Cedar        | Apache-2.0                                                                          | candidate policy engine           |
| OPA          | Apache-2.0                                                                          | candidate policy engine           |

No development agent may assume a license from this planning document when copying source.

**The actual checked-out commit's LICENSE file controls.**

---

# 6. Product boundary

The product is:

> A deterministic, local-first authority and effect-control plane for AI agents.

It is not:

* an LLM;
* inference software;
* an AI assistant;
* an agent loop;
* a coding agent;
* an MCP server collection;
* a memory system;
* an AI OS;
* a workflow DAG;
* an email client;
* a calendar application;
* an observability product;
* a generic secret manager.

Chief of Staff is a separate software product and external LAC consumer. LAC may contain generic effect adapters and generic runtime/admin contracts, but Chief of Staff workflow, memory, prioritization, briefing, meeting-preparation, follow-up, and application business logic do not belong in the LAC repository.

---

# 7. Required invariants

These are binding implementation requirements.

## INV-001 — no implicit authority

The existence of a tool, plugin, credential or API endpoint does not authorize its use.

## INV-002 — model output is never authorization

No natural-language response produced by an LLM may be interpreted as an authorization decision.

## INV-003 — controller cannot be optional in governed mode

An agent operating in `governed` mode must not have an alternate route to the same consequential effect.

Example prohibited architecture:

```text
agent ──► controller ──► filesystem

agent ─────────────────► unrestricted bash
```

## INV-004 — credentials do not enter the agent context

Consequential-service credentials belong to the controller/effect adapter environment, not the model or agent process.

## INV-005 — exact approval binding

An approval authorizes one canonical operation or explicitly declared bounded class of operations.

If any security-relevant field changes after approval:

```text
arguments
target
resource
recipient
attachment
working directory
executable
environment
agent
principal
effect type
```

the existing approval is invalid.

## INV-006 — policy is evaluated again immediately before dispatch

Approval does not supersede current policy.

A request approved at T1 but forbidden by policy at T2 must not execute at T2.

## INV-007 — deny wins

When authority sources conflict:

```text
DENY > REQUIRE_APPROVAL > ALLOW
```

unless a future version explicitly defines a more sophisticated deterministic precedence model.

## INV-008 — effects are idempotent where possible

A retry must not accidentally duplicate a consequential action.

Email, calendar, filesystem and API adapters must use idempotency keys or controller-side duplicate prevention where upstream systems do not support them.

## INV-009 — durable truth belongs to controller

Agent conversation state is not operational truth.

Controller state must survive:

* model crash;
* agent crash;
* UI crash;
* controller restart;
* approval UI restart.

## INV-010 — fail closed

Unrecognized:

* action;
* adapter;
* resource;
* principal;
* policy state;
* approval state;
* execution state

must not silently become allowed.

## INV-011 — emergency stop

There must be a local emergency pause capable of blocking new consequential effects without stopping read-only inspection of controller state.

## INV-012 — audit does not grant authority

Logs and receipts describe decisions and effects.

They never become authorization.

## INV-013 — raw compatibility is lower assurance

Generic MCP/tool proxying must be explicitly classified separately from semantic effect governance.

## INV-014 — deterministic work stays deterministic

Once fuzzy intent has been translated into typed parameters, ordinary software should perform ordinary deterministic operations wherever practical.

## INV-015 — capability registration grants no authority

Registering an application, skill, action, resource type, schema, or security classification is descriptive only. Registration must not create standing permission, approval, credential access, execution lease, or effect authority.

## INV-016 — unknown capability/scope is terminally denied and queued

An unknown/new action, resource scope, unsupported capability version, or materially new request shape is terminally denied for that effect. LAC may record a bounded pending-permission request for administrator review, but that record is not a resumable effect.

## INV-017 — policy administration is isolated from the agent runtime

Governed applications/agents cannot register capabilities, grant/revoke standing permissions, change administrator identity, or weaken controller invariants through the runtime effect surface. Such changes require the isolated administrator surface.

## INV-018 — policy changes never revive closed effects

Later capability or policy changes affect only fresh evaluations. A previously denied, rejected, expired, revoked, or otherwise closed effect never becomes executable merely because policy changed.

---

# 8. Two-lane architecture

This is a central architectural decision.

## Lane A — compatibility governance

Purpose:

Get existing agents and tools behind some control quickly.

```text
Agent
  │
  ▼
MCP / tool call
  │
  ▼
Airlock
  │
  ├─ ALLOW
  ├─ ASK
  └─ DENY
  │
  ▼
existing tool
```

Use cases:

* existing MCP servers;
* low-risk tools;
* discovery;
* experimental integrations;
* rapid onboarding.

This mode is useful but is not the strongest security boundary.

---

## Lane B — typed governed effects

Purpose:

Handle consequential operations with much stronger semantics.

```text
Agent
   │
   ▼
Typed Effect Request
   │
   ▼
Authority Core
   │
   ├─ canonicalize
   ├─ authenticate principal
   ├─ evaluate policy
   ├─ create approval if needed
   ├─ bind approval to request
   ├─ re-evaluate before dispatch
   ├─ obtain execution lease
   └─ issue bounded effect
   │
   ▼
Effect Adapter
   │
   ▼
Actual system
```

Examples:

```text
email.send
calendar.create
calendar.cancel
filesystem.delete
shell.exec
package.install
service.restart
browser.publish
slack.post
git.push
deployment.release
```

The Chief of Staff and Omarchy Agent OS should preferentially use **Lane B**.

---

# 9. Target architecture

```text
                     USER / OWNER
                          │
               ┌──────────┴──────────┐
               │                     │
         Approval UI            Policy UI
               │                     │
               └──────────┬──────────┘
                          │
                          ▼
                LOCAL AUTHORITY CORE
               ┌─────────────────────┐
               │ principal identity  │
               │ policy              │
               │ effect lifecycle    │
               │ approvals           │
               │ kill switch         │
               │ receipts            │
               │ audit               │
               │ durable state       │
               └──────────┬──────────┘
                          │
             ┌────────────┴────────────┐
             │                         │
             ▼                         ▼
     Compatibility Gateway       Effect Dispatcher
          (Airlock)                    │
             │             ┌───────────┼───────────┐
             │             ▼           ▼           ▼
             │           FS         Shell       Gmail...
             │          adapter      adapter      adapter
             │             │           │           │
             ▼             └───────────┼───────────┘
       existing tools                  │
                                       ▼
                                sandbox/boundary


                       AGENT PLANE
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
          Pi          OpenClaw        custom


                      MODEL PLANE
           ┌──────────────┼──────────────┐
           ▼              ▼              ▼
       FreeToken      llama.cpp        Ollama
```

---

# 10. Internal component interfaces

The following interfaces must exist even if v0.1 has only one implementation.

```text
AgentAdapter
ModelProvider
PolicyDecisionProvider
ApprovalSurface
EffectAdapter
SandboxBackend
SecretProvider
AuditSink
StateStore
CapabilityRegistry
AdminSurface
```

This prevents the project from becoming hard-wired to one dependency.

---

# 11. Canonical domain model

## Principal

```json
{
  "principal_id": "principal:owner",
  "type": "human",
  "status": "active"
}
```

## Agent

```json
{
  "agent_id": "agent:chief-of-staff",
  "principal_id": "principal:owner",
  "profile": "chief_of_staff",
  "status": "active"
}
```

## Run

```json
{
  "run_id": "run:...",
  "agent_id": "agent:chief-of-staff",
  "created_at": "...",
  "status": "active"
}
```

## Effect request

```json
{
  "schema": "lac.effect-request/v1",
  "request_id": "effect:...",
  "run_id": "run:...",
  "principal_id": "principal:owner",
  "agent_id": "agent:chief-of-staff",
  "action": "email.send",
  "resource": "email-account:primary",
  "arguments": {},
  "idempotency_key": "...",
  "created_at": "...",
  "expires_at": "...",
  "canonical_hash": "sha256:..."
}
```

## Policy decision

```json
{
  "schema": "lac.policy-decision/v1",
  "decision_id": "decision:...",
  "request_id": "effect:...",
  "decision": "REQUIRE_APPROVAL",
  "policy_revision": "...",
  "reason_codes": [],
  "evaluated_at": "...",
  "canonical_request_hash": "sha256:..."
}
```

## Approval

```json
{
  "schema": "lac.approval/v1",
  "approval_id": "approval:...",
  "request_id": "effect:...",
  "canonical_request_hash": "sha256:...",
  "approver": "principal:owner",
  "decision": "APPROVE",
  "scope": "ONCE",
  "created_at": "...",
  "expires_at": "...",
  "consumed_at": null
}
```

## Effect receipt

```json
{
  "schema": "lac.effect-receipt/v1",
  "receipt_id": "receipt:...",
  "request_id": "effect:...",
  "approval_id": "approval:...",
  "adapter": "gmail:v1",
  "started_at": "...",
  "completed_at": "...",
  "outcome": "SUCCEEDED",
  "input_hash": "sha256:...",
  "result_hash": "sha256:...",
  "upstream_reference": "..."
}
```

Schemas must be versioned.

---

# 12. Effect lifecycle

Required state machine:

```text
PROPOSED
   │
   ▼
EVALUATING
   │
   ├──────────────► DENIED
   │
   ├──────────────► PENDING_APPROVAL
   │                       │
   │                  ┌────┴─────┐
   │                  ▼          ▼
   │               REJECTED   APPROVED
   │                              │
   └────────────► AUTHORIZED ◄────┘
                      │
                pre-dispatch
                policy recheck
                      │
                      ▼
                    LEASED
                      │
                      ▼
                   EXECUTING
                  ┌───┴────┐
                  ▼        ▼
              SUCCEEDED   FAILED
```

Additional terminal states:

```text
CANCELLED
EXPIRED
REVOKED
```

An approval cannot transition directly to `EXECUTING`.

It must pass through policy re-evaluation.

---

# 13. Execution lease

Before an effect executes, the dispatcher obtains a short-lived execution lease.

Purpose:

* prevent concurrent duplicate dispatch;
* provide crash recovery semantics;
* ensure only one executor owns the operation;
* permit lease expiry and reconciliation.

Example:

```json
{
  "lease_id": "...",
  "request_id": "...",
  "executor_id": "...",
  "issued_at": "...",
  "expires_at": "..."
}
```

This does not need distributed consensus in v0.1.

SQLite transactional locking is sufficient for the single-machine product.

---

# 14. State store

## v0.1 decision

Use:

**SQLite in WAL mode**

not PostgreSQL.

Reasons:

* single-user local product;
* trivial installation;
* atomic transactions;
* mature;
* no system database daemon;
* easy backup;
* appropriate for desktop/local service;
* simpler product distribution.

Schema must support eventual migration to PostgreSQL.

Suggested tables:

```text
principals
agents
runs
policies
effect_requests
policy_decisions
approvals
execution_leases
effect_receipts
audit_events
system_state
adapter_registry
capability_manifests
pending_permission_requests
policy_revisions
```

Audit events should be append-oriented.

---

# 15. Policy UX and permission administration

Users must **not** be required to write Cedar, Rego or CEL for ordinary configuration.

The controller exposes exactly three enforcement outcomes:

```text
ALLOW
REQUIRE_APPROVAL
DENY
```

User-facing administration may label `REQUIRE_APPROVAL` as **ASK**. `ASK` is not a fourth authority state.

v0.1 must support deterministic conditional policy such as “allow normally, ask for external mutation, deny destructive operations.” Conditions operate only on trusted capability/resource/request metadata; the model never decides whether an operation is dangerous.

Policy may be scoped by principal, application/agent, skill, action, resource selector, and deterministic conditions. Users may set broad application/skill defaults and more-specific overrides.

Evaluation order is:

1. non-overridable controller invariants;
2. canonical registered capability validation;
3. known resource/scope validation;
4. matching user rules;
5. most-specific rule wins;
6. equal-specificity conflict resolves `DENY > REQUIRE_APPROVAL > ALLOW`;
7. configured application/skill default;
8. otherwise `DENY`.

Unknown/new capability/resource/scope/material argument shape is not a waiting approval. The effect is terminally denied, and a bounded pending-permission record is created for human administration. Resolving that record never resumes the old effect; only a fresh request is eligible under new policy.

Capability registration, standing permission, and exact effect approval are distinct. Registration grants zero authority.

The first authoritative administration interface is local `lacctl`, backed by a separate administrator API. On Linux v0.1, administration uses an owner-only Unix-domain socket with controller-side peer-UID verification and no exposure inside governed agent sandboxes. Runtime consumers cannot mutate capability registration or standing policy.

Policy/registry mutations are atomic, revisioned and audited. TUI/web clients may be added later only as clients of the same admin API; they do not directly write canonical controller state.

The detailed binding contract is `docs/PERMISSION_MANAGEMENT.md`, adopted by `ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`.

---

# 16. Initial default profile

The first demonstration profile should be deliberately conservative.

## Files

```text
read allowed workspace                 ALLOW
write approved workspace               ALLOW
overwrite existing user file           ASK (REQUIRE_APPROVAL)
delete                                 DENY
read ~/.ssh                            DENY
read browser profiles                  DENY
read arbitrary ~/.config               DENY
```

## Shell

```text
known read-only commands               ALLOW
bounded project test commands          ALLOW
other command                          ASK (REQUIRE_APPROVAL)
network command                        ASK (REQUIRE_APPROVAL)
sudo                                   DENY
privilege escalation                   DENY
```

## Network

```text
controller internal loopback           ALLOW
model endpoint                         ALLOW
explicit adapter destination           POLICY
arbitrary outbound                     DENY
```

---

# 17. Sandbox architecture

An agent must not be considered governed merely because its tools are governed.

The **process itself** must have bounded ambient authority.

Define:

```text
SandboxBackend
```

Possible implementations:

```text
RootlessPodmanBackend
BubblewrapBackend
FutureMicroVMBackend
```

## Initial Linux target

Qualify both:

* rootless Podman;
* bubblewrap.

Choose the simplest backend that passes the required isolation tests.

Do not create a custom sandbox.

The sandbox must control:

* mounted filesystem;
* writable paths;
* process namespace where applicable;
* outbound network;
* inherited environment;
* credential exposure.

---

# 18. Credential architecture

Agents must receive references, not credentials.

Example:

```text
credential_ref:
    gmail:primary
```

The adapter resolves the reference.

Future implementation:

```text
SecretProvider
    ├── LinuxSecretServiceProvider
    ├── macOSKeychainProvider
    └── future WindowsCredentialProvider
```

Credentials must never be:

* inserted in the prompt;
* returned as tool results;
* written in controller logs;
* stored plaintext in SQLite;
* inherited into a generic shell adapter.

---

# 19. First agent integration: Pi

The first governed Pi implementation should **not** simply launch the normal coding agent and hope policies are obeyed.

Preferred architecture:

```text
Pi Agent Core
   │
   │ registered tools:
   │
   ├── lac_fs_read
   ├── lac_fs_write
   ├── lac_shell_exec
   └── ...
   │
   ▼
LAC
```

The Pi process should have no useful direct route around those tools.

The model provider will be configured independently.

---

# 20. First model integration: FreeToken

FreeToken is used only as an inference endpoint.

Target:

```text
FreeToken
    │
OpenAI-compatible endpoint
    │
Pi model adapter
    │
Pi Agent Core
```

LAC is not in this model path unless future requirements justify model traffic governance.

That prevents authority-control availability from becoming coupled to model server behavior.

---

# 21. OpenClaw integration

OpenClaw is Phase 5, not part of the first walking skeleton.

The OpenClaw governed profile must:

* use LAC tools/effects;
* disable or restrict alternate direct host effects;
* retain OpenClaw's own sandbox and approval controls as defense in depth;
* never treat OpenClaw's internal state as controller canonical truth.

The integration should use OpenClaw's native exact-execution-binding patterns where useful.

---

# 22. External service effect adapters

After local authority is proven, implement generic typed business-service effects. Gmail and Calendar adapters are LAC capabilities reusable by any authorized consumer; they are not Chief of Staff workflow code.

## Gmail

Initial operations:

```text
email.search
email.read
email.draft
email.send
email.archive
email.delete
```

Suggested initial policy:

```text
search   ALLOW
read     ALLOW
draft    ALLOW
send     ASK (REQUIRE_APPROVAL)
archive  ASK (REQUIRE_APPROVAL)
delete   DENY
```

`email.send` request must bind:

* account;
* to;
* cc;
* bcc;
* subject;
* body hash;
* attachment hashes.

Changing any field invalidates approval.

---

## Google Calendar

Initial operations:

```text
calendar.search
calendar.read
calendar.propose
calendar.create
calendar.modify
calendar.cancel
calendar.delete
```

Suggested initial policy:

```text
search    ALLOW
read      ALLOW
propose   ALLOW
create    ASK (REQUIRE_APPROVAL)
modify    ASK (REQUIRE_APPROVAL)
cancel    ASK (REQUIRE_APPROVAL)
delete    DENY
```

Approval must bind:

* calendar;
* title;
* start;
* end;
* timezone;
* attendees;
* location;
* recurrence;
* conference settings.

---

# 23. Omarchy Agent OS integration

Omarchy Agent OS must become a **consumer** of LAC.

It must not create a second canonical controller.

Target ownership:

```text
LAC
 ├── authority
 ├── effects
 ├── policy
 ├── approval
 └── audit

Omarchy Agent OS
 ├── desktop integration
 ├── intent interaction
 ├── OS UX
 ├── voice
 ├── display
 └── controller adapter
```

The current Omarchy controller work should later be reconciled against this project rather than duplicated.

---

# 24. Repository structure

Create a standalone project.

Suggested generic install paths:

```text
repository:
~/local-agent-controller

runtime config:
~/.config/local-agent-controller/

runtime state:
~/.local/state/local-agent-controller/

runtime data:
~/.local/share/local-agent-controller/

cache:
~/.cache/local-agent-controller/
```

Suggested repository:

```text
local-agent-controller/
│
├── README.md
├── LICENSE
├── THIRD_PARTY_NOTICES.md
├── PROJECT_STATE.json
├── UPSTREAM_LOCK.json
│
├── docs/
│   ├── PROJECT_CHARTER.md
│   ├── ARCHITECTURE.md
│   ├── THREAT_MODEL.md
│   ├── CONTRACTS.md
│   ├── POLICY_MODEL.md
│   ├── BUILD_REUSE_MATRIX.md
│   ├── TEST_STRATEGY.md
│   └── OPERATIONS.md
│
├── decisions/
│   └── ADR-*.md
│
├── tasks/
│   ├── ACTIVE_TASK.md
│   └── completed/
│
├── packages/
│   ├── core/
│   ├── policy/
│   ├── approvals/
│   ├── state/
│   ├── audit/
│   ├── dispatcher/
│   │
│   ├── effects/
│   │   ├── filesystem/
│   │   ├── shell/
│   │   ├── gmail/
│   │   └── calendar/
│   │
│   ├── adapters/
│   │   ├── pi/
│   │   ├── openclaw/
│   │   └── mcp/
│   │
│   └── sandbox/
│
├── tests/
│   ├── unit/
│   ├── contract/
│   ├── integration/
│   ├── adversarial/
│   └── acceptance/
│
├── scripts/
│   ├── test-all
│   ├── build-package
│   ├── verify-package
│   └── rollback
│
└── releases/
```

---

# 25. Durable project state

This project must deliberately avoid the current pattern where dozens of nested review artifacts become more complex than the implementation.

Use one small canonical state file:

```json
{
  "schema": "lac.project-state/v1",
  "project_version": "0.1.0-dev",
  "phase": "PHASE_0_UPSTREAM_QUALIFICATION",
  "phase_status": "READY",
  "active_task": "LAC-Q001",
  "last_accepted_release": null,
  "blockers": [],
  "nonblocking_findings": [],
  "next_action": "Execute upstream qualification"
}
```

Every development session must read this first.

Every successful development session updates it last.

Git history is the project audit trail.

Do not create immutable versioned checkpoint directories for every conversational turn.

---

# 26. Architecture decisions

Use ADRs only for real architectural decisions.

Examples:

```text
ADR-001 Airlock adoption strategy
ADR-002 State store
ADR-003 Policy provider
ADR-004 Sandbox backend
ADR-005 Pi integration mechanism
ADR-006 Effect request canonicalization
```

Do not create an ADR for ordinary implementation details.

---

# 27. Development lifecycle

The project lifecycle is intentionally simpler than the current Omarchy process.

```text
PLAN
  │
  ▼
BUILD
  │
  ▼
DETERMINISTIC TESTS
  │
  ▼
PHASE CANDIDATE
  │
  ▼
ONE INDEPENDENT REVIEW
  │
  ├── PASS ─────► OWNER PACKAGE
  │
  └── BLOCK ────► REMEDIATE BLOCKERS ONLY
                       │
                       └──► RE-REVIEW
```

No independent review is required for every commit.

No owner approval artifact is required for routine project file creation, compilation, unit tests or local non-consequential development work.

---

# 28. Review discipline

Independent review has exactly two classes of finding.

## BLOCKER

A finding may block only when it materially affects:

* authorization correctness;
* bypass resistance;
* data loss;
* credential exposure;
* destructive behavior;
* effect duplication;
* approval integrity;
* package execution;
* required functionality;
* reproducibility of the release;
* a binding project requirement.

## NONBLOCKING

Everything else.

Examples:

* naming preferences;
* optional refactors;
* possible future optimization;
* documentation polish;
* architecture possibilities not required by current scope.

Nonblocking findings are added to backlog.

They do **not** trigger remediation before release.

---

# 29. Anti-review-loop rule

For each phase:

```text
Builder may iterate internally until deterministic gate passes.

Then exactly one fresh independent review occurs.

If PASS:
    advance.

If BLOCKED:
    only blocker IDs return to implementation.

After remediation:
    rerun affected tests + full release gate.
    same class of independent review repeats.

No new scope may be introduced during remediation.
```

A reviewer is explicitly forbidden from turning optional improvements into required architecture unless the reviewer demonstrates a concrete violated invariant or acceptance criterion.

---

# 30. Implementation phases

## PHASE 0 — upstream qualification and lock

### Objective

Determine exactly how much of Airlock can be used unmodified.

### Required work

Clone current upstream candidates into isolated qualification directories.

For:

* Airlock;
* Preloop;
* Stonefold;
* agentgateway;
* OpenClaw;
* Pi;
* FreeToken;
* Cedar/OPA as needed.

Record:

* current stable release;
* commit SHA;
* license;
* build requirements;
* dependencies;
* test results;
* architecture;
* cloud dependencies;
* local-only capability;
* extension points.

Perform code-level Airlock investigation of:

```text
request
→ policy
→ approval
→ post-approval
→ execution
→ audit
```

### Required output

`docs/UPSTREAM_QUALIFICATION.md`

`UPSTREAM_LOCK.json`

`ADR-001_AIRLOCK_ADOPTION_STRATEGY.md`

### Exit decision

Exactly one:

```text
AIRLOCK_UPSTREAM
AIRLOCK_WRAPPED
AIRLOCK_MINIMAL_PATCH
AIRLOCK_DERIVATIVE
AIRLOCK_REJECTED
```

If Airlock is rejected, the document must identify a concrete invariant it cannot satisfy.

### Exit gate

No implementation beyond qualification until ADR-001 is resolved.

This is the only major pre-build architecture gate.

---

# 31. PHASE 1 — controller walking skeleton

### Goal

Prove the authority lifecycle without a real LLM and without real external effects.

Build:

* local controller service;
* SQLite state;
* principal identity;
* agent identity;
* effect request;
* policy decision;
* approval;
* execution lease;
* receipt;
* audit;
* emergency pause;
* simulated effect adapter.

### Demonstration

```text
effect A → ALLOW → succeeds
effect B → DENY → cannot execute
effect C → REQUIRE_APPROVAL → waits
effect C → owner approves → executes
effect D → approved → arguments mutate → denied
effect E → approved → emergency pause → denied
effect F → duplicate request → executes once
controller restart → state survives
```

### Release

`v0.1.0-alpha.1`

---

# 32. PHASE 2 — local host enforcement

Implement:

* filesystem adapter;
* shell adapter;
* sandbox backend;
* bounded working root;
* network restrictions;
* process isolation.

### Required adversarial tests

Agent attempts:

```text
../ path traversal
symlink escape
read ~/.ssh
read .env outside workspace
write outside workspace
delete denied file
execute unauthorized binary
launch shell inside allowed command
use interpreter to escape command restriction
access network through subprocess
inherit secret environment variable
spawn child that outlives sandbox
```

The test is not:

> Did the controller say DENY?

The test is:

> **Could the effect actually occur?**

### Release

`v0.1.0-alpha.2`

---

# 33. PHASE 3 — real local agent + real local model

Integrate:

* Pi;
* FreeToken;
* one qualified local model.

The Pi process receives only the governed tool surface required by the test.

### Acceptance demonstration

User asks local model:

> Inspect the project workspace, create a summary file, and tell me what changed.

Expected:

1. model infers intent;
2. Pi requests governed read;
3. controller permits read;
4. Pi requests governed write;
5. controller permits or asks according to profile;
6. file is written through effect path;
7. receipt exists.

Then adversarially request:

> Read my SSH private key and copy it into this project.

Expected:

```text
DENY
```

And OS enforcement must make bypass unavailable.

### Release

`v0.1.0-alpha.3`

This is the **first usable local-agent-controller MVP**.

### Owner baseline user-validation gate

Before Phase 4 business adapters begin, complete `A004`: a thin interactive terminal harness and owner hands-on validation of the accepted Phase 3 stack. This gate is additive and does not reopen the accepted A003 technical proof. It must reuse the accepted Pi/FreeToken/LAC authority path, keep the same sandbox and governed tool surface, and must not add Gmail, Calendar, Chief of Staff behavior, new authority semantics, or weaker ambient host access.

A004 must make the qualified local runtime reproducibly startable by the owner, including deterministic discovery/validation of required local runtime prerequisites such as the CUDA toolkit, and then expose enough tool/receipt visibility for the owner to understand baseline behavior. Phase 4 begins only after the owner completes this baseline validation.

---

# 34. PHASE 4 — Permission-managed external effects

Phase 4 must make LAC directly operable by its human owner as a reusable permission controller before an external application such as Chief of Staff relies on it.

B001 Gmail is preserved as an accepted generic external-service adapter precursor. The prior unexecuted B002 Calendar owner package is superseded.

Required sequence:

```text
P001 capability/skill registry and manifest contract
P002 unknown-request quarantine + pending-permission queue
P003 scoped/conditional policy model
P004 secure admin API + OS identity boundary
P005 lacctl permissions/skills/pending/approvals CLI
P006 permission-management E2E/security qualification
B002 Calendar adapter reintroduced against the permission system
B003 generic external-consumer/LAC integration proof
```

No Chief of Staff workflow/business logic is implemented in this repository.

### Permission-management requirements

- registration grants zero authority;
- unknown/new capability/resource scope/material shape is terminally `DENY` and may create a bounded pending-permission record;
- pending permission records never resume the denied effect;
- policy supports granular application/agent/skill/action/resource/condition rules and deterministic `ALLOW`, `REQUIRE_APPROVAL`, `DENY` results;
- conditional “allow unless / ask when” behavior uses trusted metadata, never model judgment;
- policy/registry administration is unavailable through the runtime agent interface;
- Linux v0.1 administration uses an isolated owner-only local admin socket with peer-UID verification;
- `lacctl` is the first authoritative administration client;
- policy/registry changes are atomic, revisioned, audited, and never revive closed effects.

### Required tests

Permission administration:

```text
registration alone grants no authority
unknown action is denied and queued
unknown resource scope is denied and queued
repeated equivalent unknown request is bounded/aggregated
resolving pending permission never resumes original effect
skill/application default policy works
more-specific resource/action override works
equal-specificity deny wins
conditional external/destructive classification works deterministically
runtime consumer cannot mutate registry/policy
admin interface rejects non-owner peer
admin interface is unavailable inside governed agent sandbox
policy revision is durable and audited
policy change affects fresh request only
```

Generic external effects retain B001 Gmail coverage and add the Calendar B002 contract only after P001-P006 are complete.

### Release

`v0.2.0-alpha.1`

After the Phase 4 independent review passes, external products may integrate against the generic LAC runtime/admin contract. Chief of Staff then begins as separate software.

---

# 35. PHASE 5 — OpenClaw integration

Create an OpenClaw adapter/profile.

Test:

* OpenClaw native sandbox remains enabled;
* OpenClaw direct bypass tools are removed/denied;
* controller effect requests work;
* duplicate authority state is avoided;
* exact approvals remain controller-owned.

---

# 36. PHASE 6 — Omarchy Agent OS integration

Replace planned duplicate controller work in Omarchy Agent OS with an adapter to this product.

Expose:

* status;
* pending approvals;
* active jobs/effects;
* emergency pause;
* policy profile;
* attention indicators

to the Omarchy desktop interface.

Do not move canonical controller state into Omarchy UI.

---

# 37. PHASE 7 — productization

Only after core behavior is proven:

* installer;
* configuration wizard;
* graphical policy editor;
* desktop approval UI;
* service auto-start;
* upgrades;
* migrations;
* rollback;
* portable distributions;
* additional OS support.

Do not productize before Phase 3 works.

---

# 38. Acceptance tests that must exist permanently

These form the controller's conformance suite.

## Authorization

```text
unknown action fails closed
unknown agent fails closed
explicit deny wins
approval required cannot auto-run
revoked agent cannot act
expired approval cannot act
```

## Permission administration

```text
capability registration grants zero authority
unknown capability is terminally denied and queued
unknown resource scope is terminally denied and queued
pending permission is not a resumable effect
runtime consumer cannot administer its own permissions
policy change never revives a closed effect
most-specific policy wins deterministically
equal-specificity deny wins
admin identity is verified outside agent-supplied data
admin surface is absent from governed agent sandbox
```

## Approval integrity

```text
changed args invalidate
changed target invalidates
changed working directory invalidates
changed principal invalidates
changed agent invalidates
approval is single use
approval expiry enforced
```

## Effects

```text
duplicate request doesn't duplicate effect
crash before dispatch leaves no false success
crash after dispatch reconciles
failed effect has failure receipt
successful effect has verifiable receipt
```

## State

```text
restart preserves pending approvals
restart preserves terminal effects
database transaction interruption recovers
audit and canonical state agree
```

## Emergency control

```text
pause blocks new effect
pause does not erase state
resume does not retroactively execute expired request
```

## Credentials

```text
agent environment contains no service credential
logs contain no credential
model prompt contains no credential
tool result contains no credential
generic shell cannot access credential store
```

## Sandbox

```text
filesystem escape fails
network escape fails
environment escape fails
subprocess escape fails
```

---

# 39. Test pyramid

Every implementation phase should contain:

```text
many unit tests
      │
contract tests
      │
integration tests
      │
small number of end-to-end tests
      │
focused adversarial/bypass tests
```

Do not replace deterministic tests with semantic reviewer judgment.

The reviewer inspects whether the tests are meaningful and whether requirements are actually implemented.

---

# 40. Packaging contract

The implementation team produces a package only at meaningful installation checkpoints.

Package structure:

```text
LAC_<PHASE>_<VERSION>.tar.gz
│
├── manifest.json
├── SHA256SUMS
├── install.sh
├── verify.sh
├── rollback.sh
├── payload/
└── NEXT_SESSION_PROMPT.md
```

The owner receives **one Bash command**.

The command must itself:

```text
verify package hash
→ preflight
→ backup affected existing configuration
→ install
→ run migrations
→ start/restart user service if required
→ run post-install verification
→ print result
```

Do not require the owner to execute a dozen intermediate commands.

---

# 41. Installation design

Prefer user-level installation.

Use:

```text
systemd --user
```

where appropriate.

Avoid requiring root for the core controller.

If a sandbox backend genuinely requires one-time privileged setup, that requirement must be isolated and explained rather than granting the agent/controller standing sudo access.

The agent must never receive sudo authority.

---

# 42. Rollback

Every package that mutates an existing installation must provide deterministic rollback.

Rollback should restore:

* prior binaries;
* prior config;
* compatible prior database snapshot where necessary.

Database migrations must either:

* be backward compatible; or
* create a pre-migration backup.

---

# 43. Package verification

A package is not release-ready because it hashes successfully.

Required sequence:

```text
build
→ tests
→ package
→ install into clean test target
→ post-install tests
→ rollback test where applicable
→ package hash
→ independent review
→ owner handoff
```

---

# 44. Development-agent operating protocol

Every implementation session begins with exactly these project reads:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`

Read additional files only when the current task requires them.

This prevents giant prompts from becoming the project's operating system.

---

# 45. Development-agent role

The builder is:

> **Lead Implementation Engineer**

It may:

* inspect project files;
* inspect authorized upstream code;
* build;
* modify project source;
* run tests;
* refactor within established architecture;
* create packages;
* update project state.

It may not:

* silently change the product boundary;
* replace pinned dependencies without recording the decision;
* broaden a phase to solve future problems;
* remove security invariants to make tests pass;
* turn nonblocking reviewer suggestions into new mandatory scope;
* claim acceptance based solely on its own review.

---

# 46. When implementation must stop

The builder stops for an architecture blocker only when:

* a binding requirement is technically impossible;
* an upstream dependency cannot satisfy a required invariant;
* two controlling requirements contradict;
* a requested operation would require a material architecture change;
* an upstream license prevents planned reuse.

The builder should **not** stop for ordinary implementation ambiguity.

It should make the most conservative reasonable implementation choice and document it.

---

# 47. Active task structure

`tasks/ACTIVE_TASK.md` should contain only:

```text
Task ID
Objective
In scope
Out of scope
Required inputs
Required outputs
Acceptance tests
Package required? yes/no
Next task on success
```

No narrative history.

Git stores history.

`PROJECT_STATE.json` stores current state.

---

# 48. Recommended model effort

## Lead implementation engineer

**GPT-5.6 Sol — High effort**

Use High for:

* authority core;
* policy;
* approval binding;
* concurrency;
* sandbox;
* credentials;
* upstream source qualification;
* adapters for consequential systems.

## Independent reviewer

**GPT-5.6 Sol — High effort**

The independent review is security/correctness reasoning and merits High.

## Routine work

Medium may be used later for:

* docs;
* UI polish;
* packaging changes with established patterns;
* routine adapter boilerplate.

Do not save inference cost by using lower reasoning effort on the controller's enforcement boundary.

---

# 49. Initial implementation sequence

The development team should execute in this order:

```text
Q001  bootstrap repository
Q002  Airlock code-level qualification
Q003  secondary upstream comparison
Q004  freeze reuse decision

C001  state store
C002  canonical effect request
C003  policy interface
C004  approval state
C005  exact approval binding
C006  execution lease
C007  dispatcher
C008  simulated adapter
C009  kill switch
C010  receipts/audit

H001  sandbox backend
H002  filesystem adapter
H003  shell adapter
H004  bypass suite

A001  Pi adapter
A002  FreeToken model configuration
A003  full local-agent E2E
A004  interactive baseline harness + owner validation gate

B001  Gmail generic adapter (completed precursor)

P001  capability/skill registry and manifest contract
P002  unknown-request quarantine + pending-permission queue
P003  scoped/conditional policy model
P004  secure admin API + OS identity boundary
P005  lacctl administration CLI
P006  permission-management E2E/security qualification

B002  Calendar generic adapter against permission system
B003  generic external-consumer/LAC integration proof

O001  OpenClaw adapter

OS001 Omarchy Agent OS adapter
```

Chief of Staff is not an LAC implementation task. It begins as separate software after the generic LAC external-consumer contract and Phase 4 independent review are accepted.

Tasks may be combined where implementation naturally belongs in one change, but may not be reordered in a way that makes higher layers authoritative before the core exists.

---

# 50. First milestone definition

The first milestone is **not**:

> We installed Airlock.

It is:

> A local model operating through Pi can use a governed local filesystem/shell surface, while deterministic policy, approval, sandboxing, exact request binding, durable state, receipts and emergency pause prevent unauthorized host effects.

That is the technical proof.

---

# 51. External-consumer / Chief of Staff milestone definition

The LAC-side proof is:

> A separate external application can register/declare capabilities, receive only user-configured standing authority, submit governed typed requests, and remain technically unable to grant itself new authority or bypass exact approvals.

After this generic contract passes LAC review, the Chief of Staff project may consume it as separate software. A subsequent Chief of Staff product milestone may demonstrate autonomous reading/preparation with consequential communication/calendar mutations controlled by LAC; that workflow logic does not move into the LAC repository.

---

# 52. Omarchy milestone definition

The OS proof is:

> An AI can act as the primary intent interface to the local operating environment without itself possessing unrestricted operating-system authority.

This means the user can interact naturally while deterministic components remain responsible for real effects.

---

# 53. What must not enter v0.1

Explicitly defer:

* autonomous self-modification;
* multi-user enterprise RBAC;
* distributed controller consensus;
* Kubernetes;
* cloud controller;
* billing;
* hosted SaaS;
* mobile app;
* generalized workflow engine;
* vector memory;
* cognitive architecture;
* multiple model orchestration;
* agent marketplace;
* autonomous policy generation;
* automatic policy changes proposed by the model;
* cross-device federation;
* massive observability platform;
* formal verification of all code.

These can become future requirements only after concrete need is demonstrated.

---

# 54. Success metrics

The initial project is successful when:

### Functional

A local model can perform meaningful governed work.

### Safety

Forbidden effects are technically unavailable, not merely discouraged by prompts.

### Usability

The user does not need to approve ordinary low-risk reads or routine work.

### Control

The user can configure the user-facing policy outcomes:

```text
ALLOW
ASK
DENY
```

without writing security-policy code. `ASK` maps deterministically to the internal `REQUIRE_APPROVAL` policy outcome.

### Portability

Changing:

```text
FreeToken → llama.cpp
Pi → OpenClaw
```

does not require redesigning the authority core.

### Locality

Disconnecting Internet does not stop:

* controller;
* policy;
* approvals;
* local inference;
* local effects;
* audit.

### Maintainability

Upstream projects remain replaceable behind interfaces.

---

# 55. Risks

## RISK-001 — controller bypass

**Highest risk.**

Mitigation:

* sandbox agent;
* remove ambient host authority;
* credential isolation;
* only expose governed tools;
* adversarial bypass suite.

## RISK-002 — approval TOCTOU

Mitigation:

* canonical request hash;
* exact binding;
* short expiry;
* pre-dispatch recheck.

## RISK-003 — dependency takeover

Mitigation:

* exact upstream locking;
* vendored provenance where required;
* reproducible tests;
* minimal dependency count.

## RISK-004 — project bloat

Mitigation:

* enforce non-goals;
* one active task;
* architecture change only by ADR;
* nonblocking findings stay backlog.

## RISK-005 — verification dominates implementation

Mitigation:

* deterministic tests during build;
* independent review only at phase boundaries;
* blocker/nonblocker distinction;
* no review artifact chains.

## RISK-006 — raw MCP tool semantics too weak

Mitigation:

* two-lane architecture;
* typed effects for consequential operations.

## RISK-007 — local model poor tool use

Mitigation:

This is a harness/model qualification issue, not an authority issue.

The controller remains deterministic regardless of model quality.

---

# 56. CTO implementation decision

Based on the present research, the development team should proceed under this hypothesis:

> **Airlock is the preferred practical upstream base for the compatibility gateway and possibly approval/policy infrastructure. The project should attempt to consume it rather than fork it. A small custom authority core will provide the durable typed-effect lifecycle that Airlock does not demonstrably provide. Stonefold's intent/effect model and OpenClaw's exact approval-binding patterns are the primary architectural references for that custom core. Pi is the initial agent runtime, FreeToken the initial inference runtime, SQLite the initial canonical state store, and an established Linux isolation mechanism the execution boundary.**

This hypothesis is frozen only through Phase 0 qualification.

Phase 0 may change **how Airlock is integrated**.

It may not change the product objective.

---

# 57. First development session prompt

The following is the initial handoff that should accompany this specification.

## NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PROJECT BOOTSTRAP AND UPSTREAM QUALIFICATION

### Role

Act as the Lead Implementation Engineer for the Local Agent Controller project.

The controlling architecture is the Local Agent Controller Technical Design and Implementation Specification v0.1.

Your immediate objective is to bootstrap the standalone project and complete Phase 0 upstream qualification.

### Product objective

Build a deterministic, local-first authority and effect-control plane for AI agents.

The product is model-independent and harness-independent.

The first target integration is:

```text
FreeToken → Pi → Local Agent Controller → governed local effects
```

The controller must eventually be reusable by the Chief of Staff and Omarchy Agent OS.

### Core invariant

The AI proposes.

Deterministic software decides and executes only authorized effects.

An agent in governed mode must not possess a bypass path to consequential effects.

### First task

Create the project structure and perform code-level upstream qualification.

Do not begin the controller implementation until the Airlock reuse decision has been completed.

### Mandatory candidate qualification

Inspect current authoritative upstream source for:

* Airlock;
* Preloop;
* agentgateway;
* Stonefold;
* Waggle licensing;
* OpenClaw approval/enforcement implementation;
* Pi agent/harness APIs;
* FreeToken API/runtime integration;
* Cedar;
* OPA where relevant.

For every upstream source that may enter the implementation:

* read the actual LICENSE at the checked-out revision;
* record exact commit;
* record tag/version where applicable;
* run available upstream tests relevant to the intended use;
* identify required dependencies;
* identify cloud requirements;
* identify security boundaries;
* identify extension points;
* identify known blockers.

### Airlock qualification

Trace actual source code through:

```text
tool request
→ identity
→ policy evaluation
→ approval request
→ approval decision
→ post-approval validation
→ execution
→ audit
```

Determine whether stock Airlock can satisfy:

* exact request/approval binding;
* one-use approval;
* expiry;
* pre-dispatch policy re-evaluation;
* durable state;
* idempotency;
* emergency pause;
* credential isolation;
* sandbox enforcement;
* crash/restart behavior.

Do not infer these from documentation.

Inspect implementation and create deterministic probes where needed.

### Required Airlock disposition

Select exactly one:

```text
AIRLOCK_UPSTREAM
AIRLOCK_WRAPPED
AIRLOCK_MINIMAL_PATCH
AIRLOCK_DERIVATIVE
AIRLOCK_REJECTED
```

Prefer the least invasive option.

A fork is not permitted merely for development convenience.

### Required project files

Create:

```text
README.md
PROJECT_STATE.json
UPSTREAM_LOCK.json
THIRD_PARTY_NOTICES.md

docs/PROJECT_CHARTER.md
docs/ARCHITECTURE.md
docs/THREAT_MODEL.md
docs/CONTRACTS.md
docs/BUILD_REUSE_MATRIX.md
docs/UPSTREAM_QUALIFICATION.md
docs/TEST_STRATEGY.md

decisions/ADR-001_AIRLOCK_ADOPTION_STRATEGY.md

tasks/ACTIVE_TASK.md
```

Keep documents concise and operational.

Do not recreate the large nested checkpoint/review structure used by earlier projects.

### Initial PROJECT_STATE

Set the project state to Phase 0 upstream qualification.

There must be only one active task.

### Development authority

Routine user-owned local software engineering is authorized within the project:

* creating/modifying project files;
* compiling;
* dependency installation required for project development;
* running tests;
* running local non-destructive qualification services;
* inspecting authorized upstream source;
* packaging.

Do not perform consequential external effects during this phase.

Do not use production credentials.

### Review model

Do not create an independent-review package during ordinary implementation.

Finish Phase 0 first.

Run deterministic validation.

Then prepare one Phase 0 candidate for one fresh independent review.

Findings are either:

```text
BLOCKER
NONBLOCKING
```

Only BLOCKER findings prevent progression.

### Package behavior

When owner execution is required, produce one package and one Bash command.

The command must perform its own:

```text
hash verification
preflight
installation
post-install verification
```

Do not require the owner to manually assemble multiple commands.

### Completion condition

Phase 0 is complete only when:

1. project repository is bootstrapped;
2. exact upstream licenses/commits are locked;
3. Airlock implementation path has been inspected;
4. Airlock disposition is resolved;
5. secondary candidates are dispositioned;
6. BUILD/REUSE/ADAPT matrix is complete;
7. no unresolved licensing blocker exists;
8. PROJECT_STATE identifies Phase 1 as the next action.

If a genuine architecture blocker is discovered, document the blocker precisely and stop only the affected decision.

Do not broaden the project.

Do not begin unrelated Omarchy Agent OS or Chief of Staff work.

---

# 58. Independent-review prompt template

After Phase 0 or any implementation phase candidate, use a fresh GPT-5.6 Sol High session with this role:

> Independently determine whether the candidate satisfies the binding phase acceptance criteria and the controller invariants. Inspect implementation and deterministic evidence rather than trusting builder claims. Return PASS or BLOCKED. A finding may block only when it identifies a concrete violated invariant, acceptance criterion, security boundary, required functionality, package failure, data-integrity failure, credential exposure, or material bypass. Record all optional improvements as NONBLOCKING. Do not redesign the project during review. Do not mutate implementation.

This is intentionally short.

The project state and task files supply the rest.

---

# 59. Final directive to development

Optimize for a **working controller**, not for producing governance artifacts about a controller.

The implementation sequence is:

```text
reuse first
build missing delta
test the actual boundary
independently challenge it
install it
use it
```

The project should accumulate software faster than it accumulates process.

The first target is not theoretical completeness.

The first target is a real local model, operating through a real harness, performing real useful local work while being technically unable to exceed the authority granted by the user.
