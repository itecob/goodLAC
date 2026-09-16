# ACTIVE TASK — LAC-B002

## Task ID

`LAC-B002`

## Objective

Implement and qualify the generic Google Calendar typed-effect adapter against the accepted Phase 4 permission-management plane. Calendar is a reusable LAC adapter, not Chief of Staff business logic.

## In scope

- Implement the typed Calendar operations already defined by the controlling specification: `calendar.search`, `calendar.read`, `calendar.propose`, `calendar.create`, `calendar.modify`, `calendar.cancel`, and `calendar.delete`.
- Reuse B001 adapter/transport patterns where applicable; keep Calendar authorization controller-owned.
- Bind all security-relevant Calendar mutation material into the canonical effect request, including calendar identity, title, start/end/timezone, attendees, location, recurrence, and conference settings as applicable.
- Keep service credentials behind adapter credential references; no credential material enters model/agent context or pending-permission metadata.
- Qualify with synthetic/local fixtures and non-production transport. Do not perform consequential production Calendar effects.
- Exercise the first-use permission sequence before any authorized Calendar adapter mutation:
  1. register/validate the Calendar capability;
  2. issue a fresh valid Calendar request with no applicable owner-configured standing permission/default;
  3. prove terminal `DENY`, bounded owner-reviewable `NO_CONFIGURED_STANDING_PERMISSION` item, no lease, and no adapter mutation;
  4. configure future scope through P004/P005;
  5. prove the original denied request cannot resume;
  6. issue a fresh Calendar request;
  7. prove current policy yields only `ALLOW`, `REQUIRE_APPROVAL`, or `DENY`;
  8. reach the Calendar adapter only when currently authorized.
- Prove an explicit configured Calendar `DENY` does not generate recurring permission-discovery work.
- Preserve exact approval binding, pre-dispatch policy re-evaluation, deny precedence, idempotency/duplicate prevention, durable truth, admin/runtime isolation, and fail-closed behavior.
- Run focused B002 tests plus the accepted deterministic regression through P006-UAT and prior phases.
- Produce one owner-executable B002 completion package on PASS.

## Out of scope

- Chief of Staff workflow, memory, prioritization, briefing, meeting-preparation, or follow-up logic.
- B003 external-consumer implementation.
- Production Calendar credentials or consequential external Calendar effects.
- Web/TUI administration, OpenClaw, Omarchy Agent OS, remote administration, enterprise RBAC.
- Changing the accepted permission semantics or weakening any LAC invariant.

## Required inputs

- Accepted P006-UAT owner execution evidence.
- `docs/PERMISSION_MANAGEMENT.md`, `docs/CONTRACTS.md`, and ADR-007.
- Existing B001 Gmail adapter implementation/tests as the generic external-service adapter precedent.
- Calendar contract in the controlling Technical Design and Implementation Specification v0.1.

## Required outputs

- Generic Calendar adapter and bounded transport interface.
- Deterministic unit/integration/negative-security tests.
- Explicit first-use permission-discovery/non-resumption qualification for Calendar.
- Credential-isolation and exact mutation-binding proof.
- Regression evidence through accepted P006-UAT.
- One owner-executable package that advances only to `LAC-B003` on PASS.

## Acceptance tests

- typed Calendar request schemas reject malformed/unknown material;
- first valid unconfigured Calendar request is `DENY`, creates/aggregates owner-review work, gets no lease, and invokes no adapter;
- owner policy configuration cannot revive that original request;
- a fresh request is required after configuration;
- configured `ALLOW`, `REQUIRE_APPROVAL`, and `DENY` are all deterministic;
- explicit configured `DENY` creates no discovery noise;
- exact approval binds the complete security-relevant mutation;
- policy changes are re-evaluated immediately before dispatch;
- duplicate/idempotent effects cannot execute twice;
- credentials remain adapter-side and absent from agent/pending/audit surfaces;
- synthetic transport proves authorized adapter behavior without production external effects;
- accepted deterministic P006-UAT and prior regression remain PASS.

## Package required?

Yes.

## Next task on success

`LAC-B003` in a fresh implementation session.
