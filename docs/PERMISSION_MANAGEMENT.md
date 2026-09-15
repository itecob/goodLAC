# Permission Management — Binding Phase 4 Design

**Status:** Accepted binding amendment for LAC Phase 4
**Adopted by:** `ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`

## Purpose

LAC is a reusable governing system. External applications such as Chief of Staff, Omarchy Agent OS, Pi-based agents, and future modules plug into LAC; they do not own LAC authority policy.

The controller must be operable by the user as a permission system before an external application is allowed to rely on it.

## Three separate concepts

These must never be conflated:

1. **Capability registration** describes what an application/skill may request. Registration grants zero authority.
2. **Standing permission policy** determines the outcome for future matching requests: `ALLOW`, `REQUIRE_APPROVAL`, or `DENY`.
3. **Exact effect approval** authorizes one exact canonical consequential operation when standing policy returns `REQUIRE_APPROVAL`.

A pending permission request is not a pending effect.

## Runtime outcomes

The authority core continues to expose exactly three enforcement outcomes:

- `ALLOW`
- `REQUIRE_APPROVAL`
- `DENY`

User-facing interfaces may label `REQUIRE_APPROVAL` as **ASK**. `ASK` is not a fourth authority state.

“Allow unless …” and “ask only when …” are deterministic policy-rule patterns evaluated from trusted capability/resource metadata and request fields. They are not model judgments.

## Capability/skill registry

A versioned canonical manifest describes an application or skill and the requests it may make. Initial manifest material includes:

- stable application/skill identity;
- manifest version;
- declared actions;
- resource types and bounded selectors;
- bounded argument schema for each action;
- deterministic security properties for each action/resource class;
- optional display metadata that does not affect authority.

Initial trusted security-property vocabulary should cover at least:

- `read_only`
- `local_mutation`
- `external_mutation`
- `destructive`
- `external_communication`
- `credential_sensitive`
- `security_sensitive`
- `permission_change`
- `network_egress`
- `privilege_change`

The model cannot assign or alter these properties at runtime. Registration itself creates no permission and provides no credential capability.

## Unknown/new request behavior

An unknown action, unknown resource type/scope, unsupported manifest version, or materially new argument shape must fail closed.

Required behavior:

```text
request arrives
→ capability/scope is not already known and policy-addressable
→ terminal DENY for this effect
→ no execution lease
→ no adapter mutation
→ record bounded pending-permission request
→ original effect remains closed forever
```

Resolving the pending permission record may create or change future standing policy, but it never resumes the denied effect. The application must issue a fresh request, which is evaluated against the current policy revision.

Equivalent repeated unknown requests should aggregate rather than create an unbounded queue. Preserve at least first-seen time, last-seen time, count, requester identity, skill/version, action/resource, reason, and bounded/redacted schema metadata. Never persist raw credentials in pending-permission records.

## Standing policy model

Policy may be scoped by:

- principal;
- application/agent;
- skill;
- action;
- resource/resource selector;
- deterministic conditions over trusted capability/resource/request metadata.

Users may configure broad defaults and progressively more specific overrides. Example:

```text
application=chief-of-staff
skill=google-calendar
default=ALLOW

when external_mutation=true -> REQUIRE_APPROVAL
when destructive=true       -> DENY

calendar.read on calendar:primary   -> ALLOW
calendar.delete on calendar:primary -> DENY
```

Evaluation order for v0.1:

1. non-overridable controller invariants;
2. registered/canonical capability validation;
3. known resource/scope validation;
4. matching user policy rules;
5. most-specific matching rule wins;
6. equal-specificity conflict resolves `DENY > REQUIRE_APPROVAL > ALLOW`;
7. configured application/skill default if present;
8. otherwise `DENY`.

Policy administration must never disable core fail-closed, exact-approval, credential-isolation, emergency-pause, or admin-boundary invariants.

## Administrative authority boundary

Runtime consumers and human administration use separate controller interfaces.

### Runtime interface

External applications may submit governed requests and inspect permitted request/result state. They cannot mutate capability registration, standing policy, administrator identity, or controller invariants.

### Administrative interface

For the single-owner Linux v0.1 target:

- expose a separate local Unix-domain admin socket;
- locate it beneath the owning user's runtime directory;
- protect it with owner-only filesystem permissions;
- verify peer OS UID at the controller side;
- never expose or mount the admin socket into governed agent sandboxes;
- require all policy/registry mutations to use this path;
- record atomic, versioned, auditable policy/registry changes.

No separate LAC password/RBAC system is required in v0.1. Multi-user enterprise RBAC and a privileged system-wide/polkit deployment remain future work unless the threat model changes.

The v0.1 boundary does not claim to protect against arbitrary already-compromised unsandboxed software executing as the same owner UID. Governed agent processes must remain sandboxed away from the admin socket.

## `lacctl` administration client

The first authoritative user interface is a local CLI that uses the admin API. It should support machine-readable output and, by the end of P005, operations equivalent to:

```text
lacctl skills list
lacctl skills show <skill>
lacctl permissions list
lacctl permissions show ...
lacctl permissions set ...
lacctl permissions revoke ...
lacctl pending list
lacctl pending show <id>
lacctl pending resolve <id> ...
lacctl pending dismiss <id>
lacctl approvals list
lacctl approvals show <id>
lacctl approvals approve <id>
lacctl approvals reject <id>
```

A TUI or web UI may later consume the same admin API. Neither becomes canonical authority or writes controller state directly.

## Policy mutation semantics

Policy and registry mutations are:

- administrator-only;
- atomic;
- revisioned;
- auditable;
- never initiated as an agent runtime effect;
- incapable of reviving a previously denied/expired/rejected effect.

Rollback of policy means creating a new revision equivalent to an older configuration; audit history is not erased.

## Chief of Staff boundary

Chief of Staff is separate software. LAC may contain generic service adapters and the generic runtime/admin contracts needed by consumers, but it must not contain Chief of Staff workflow, memory, prioritization, briefing, meeting-preparation, follow-up, or business-policy logic.

Chief of Staff must register/declare its capabilities through the generic LAC contract and receive only the authority the user configures in LAC.

## Required implementation sequence

```text
P001 capability/skill registry and manifest contract
P002 unknown-request quarantine + pending-permission queue
P003 scoped/conditional policy model
P004 secure admin API + OS identity boundary
P005 lacctl permissions/skills/pending/approvals CLI
P006 permission-management E2E/security qualification
B002 Calendar adapter reintroduced against the permission system
B003 generic external-consumer/LAC integration proof
Phase 4 independent review
```

No Chief of Staff implementation begins inside the LAC repository.
