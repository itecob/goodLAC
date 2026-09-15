# ADR-007 — Permission Administration and Capability Governance

**Status:** ACCEPTED
**Date:** 2026-09-15

## Context

LAC had already proven its deterministic authority/effect lifecycle and completed the B001 Gmail adapter, but its Phase 4 sequence still relied on developer-authored policy fixtures and moved directly toward Calendar and a Chief of Staff E2E. That would make an external application depend on LAC before the owner had an operable permission-management plane and risked blurring the product boundary between LAC and Chief of Staff.

## Decision

Insert a permission-management stage before Calendar and before any external Chief of Staff build.

The stage consists of `LAC-P001` through `LAC-P006`, followed by a reintroduced generic Calendar adapter (`LAC-B002`) and a generic external-consumer integration proof (`LAC-B003`). Chief of Staff is separate software and is not implemented in the LAC repository.

The following rules are binding:

1. capability/skill registration describes possible requests and grants zero authority;
2. standing policy has only `ALLOW`, `REQUIRE_APPROVAL`, and `DENY`; user interfaces may label `REQUIRE_APPROVAL` as `ASK`;
3. unknown/new action, resource scope, or material request shape is terminally denied and recorded as a pending-permission request;
4. resolving a pending-permission request never resumes the denied effect; only a fresh request may be evaluated under new policy;
5. policy may be granular by principal/application/agent/skill/action/resource/conditions and may use deterministic “allow unless / ask when” rules based on trusted metadata;
6. runtime applications cannot mutate capability registration or standing policy;
7. v0.1 administration uses a separate owner-only Linux Unix-domain admin socket with peer-UID verification and no exposure inside governed sandboxes;
8. `lacctl` is the first authoritative administration client; TUI/web surfaces, if added later, consume the same admin API and are not canonical state writers;
9. policy/registry changes are atomic, revisioned, audited, and cannot revive previously closed effects.

## Consequences

- The unexecuted `LAC_B002_CALENDAR_ADAPTER_v0.1.0` package is superseded and must not be executed.
- B001 remains accepted as a generic service-adapter precursor; it does not become Chief of Staff code.
- The controller becomes directly operable by the owner before external applications rely on it.
- The trusted computing base gains an administration interface, but it is deliberately local, minimal, and isolated from the agent runtime.
- Same-UID arbitrary unsandboxed compromise is not claimed to be solved by v0.1; governed agents remain sandboxed away from the admin endpoint.

## Rejected alternatives

- Building Chief of Staff inside LAC.
- Allowing skills to self-register with authority or change their own standing permissions.
- Treating an unknown request as a resumable pending effect.
- Adding a fourth `ALLOW_UNLESS` decision state instead of deterministic conditional policy rules.
- Building a browser/web administration surface before the authority/admin API contract is stable.
