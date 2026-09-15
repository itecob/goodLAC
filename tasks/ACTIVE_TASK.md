# ACTIVE TASK — LAC-B002

## Task ID

`LAC-B002`

## Objective

Implement the Phase 4 Google Calendar typed effect adapter as the next fresh implementation segment, preserving the accepted LAC authority core, exact approval binding, sandbox/credential boundaries, and durable receipt semantics.

## In scope

- Implement the Calendar effect surface required by the controlling specification: `calendar.search`, `calendar.read`, `calendar.propose`, `calendar.create`, `calendar.modify`, `calendar.cancel`, and `calendar.delete`.
- Keep Calendar effects behind the existing typed LAC Authority Core / Dispatcher path; the model or Pi harness never becomes authoritative.
- Implement the initial policy profile from the specification: search/read/propose `ALLOW`, create/modify/cancel `APPROVE`, delete `DENY`.
- For consequential Calendar changes, bind approval to calendar, title, start, end, timezone, attendees, location, recurrence, and conference settings so any security-relevant mutation invalidates approval.
- Preserve credential isolation: agents receive references/capabilities, never raw service credentials in model context, tool arguments, logs, or receipts.
- Use deterministic local/synthetic fixtures for automated tests. Any live Google Calendar qualification must use a dedicated test account or an explicitly owner-authorized bounded account and must not introduce production credentials into repository/test evidence.
- Add only the minimum adapter/provider seam needed for B002; reuse existing controller/state/policy/approval/lease/receipt interfaces and the credential-boundary pattern established by B001.

## Out of scope

- Chief of Staff E2E (`LAC-B003`).
- Gmail redesign or additional Gmail capabilities beyond accepted B001.
- Calendar UI, general web UI, voice UI, memory architecture, OpenClaw, or Omarchy integration.
- Broadening controller authority semantics, shell allowlists, or agent ambient authority.
- Production credential provisioning unless separately authorized by the owner.

## Required inputs

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, especially Calendar and Phase 4 sections.
- Accepted Phase 1 authority lifecycle and Phase 2 enforcement components.
- Accepted Phase 3 Pi/FreeToken integration and A004 owner-UAT PASS evidence.
- Completed B001 Gmail adapter/credential-provider seam as a pattern only; do not broaden Gmail scope.
- Existing `EffectAdapter`, credential-reference boundary, policy, approval, dispatcher, lease, receipt, and audit contracts as applicable.

## Required outputs

- Bounded Calendar effect implementation under the existing project structure.
- Deterministic unit/integration/negative-security tests for the B002 contract.
- Regression evidence for all applicable accepted earlier phases including B001.
- One owner-executable package completing B002 and activating `LAC-B003` on success, or an appropriate valid stop gate if genuinely blocked by external authority/dependency.

## Acceptance tests

At minimum prove deterministically that:

1. search/read/propose can succeed through the typed governed path under `ALLOW` without granting model authority;
2. create/modify/cancel without an exact valid approval cannot produce the external Calendar effect;
3. approved consequential change can execute once and yields a durable receipt;
4. changing calendar, title, start, end, timezone, attendees, location, recurrence, or conference settings after approval invalidates that approval;
5. duplicate/retry handling does not duplicate a consequential Calendar change;
6. delete is denied and cannot produce the prohibited effect;
7. unknown/malformed Calendar actions/resources fail closed;
8. raw credentials do not enter agent/model-visible context or durable audit/receipt data;
9. applicable Phase 1–3/A004/B001 regressions remain passing.

## Package required?

Yes.

## Next task on success

`LAC-B003` in a fresh implementation session. Do not begin it in the B002 session.
