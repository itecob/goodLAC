# ACTIVE TASK — LAC-B001

## Task ID

`LAC-B001`

## Objective

Implement the Phase 4 Gmail typed effect adapter as the next fresh implementation segment, preserving the accepted LAC authority core, exact approval binding, sandbox/credential boundaries, and durable receipt semantics.

## In scope

- Implement the Gmail effect surface required by the controlling specification: `email.search`, `email.read`, `email.draft`, `email.send`, `email.archive`, and `email.delete`.
- Keep Gmail effects behind the existing typed LAC Authority Core / Dispatcher path; the model or Pi harness never becomes authoritative.
- Implement the initial policy profile from the specification: search/read/draft `ALLOW`, send/archive `APPROVE`, delete `DENY`.
- For `email.send`, bind approval to account, to, cc, bcc, subject, body hash, and attachment hashes so any security-relevant mutation invalidates approval.
- Preserve credential isolation: agents receive references/capabilities, never raw service credentials in model context, tool arguments, logs, or receipts.
- Use deterministic local/synthetic fixtures for automated tests. Any live Gmail qualification must use a dedicated test account or an explicitly owner-authorized bounded account and must not introduce production credentials into repository/test evidence.
- Add only the minimum adapter/provider seam needed for B001; reuse existing controller/state/policy/approval/lease/receipt interfaces.

## Out of scope

- Calendar (`LAC-B002`).
- Chief of Staff E2E (`LAC-B003`).
- Gmail UI, general web UI, voice UI, memory architecture, OpenClaw, or Omarchy integration.
- Broadening controller authority semantics, shell allowlists, or agent ambient authority.
- Production credential provisioning unless separately authorized by the owner.

## Required inputs

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, especially Gmail and Phase 4 sections.
- Accepted Phase 1 authority lifecycle and Phase 2 enforcement components.
- Accepted Phase 3 Pi/FreeToken integration and A004 owner-UAT PASS evidence.
- Existing `EffectAdapter`, credential-reference boundary, policy, approval, dispatcher, lease, receipt, and audit contracts as applicable.

## Required outputs

- Bounded Gmail effect implementation under the existing project structure.
- Deterministic unit/integration/negative-security tests for the B001 contract.
- Regression evidence for all applicable accepted earlier phases.
- One owner-executable package completing B001 and activating `LAC-B002` on success, or an appropriate valid stop gate if genuinely blocked by external authority/dependency.

## Acceptance tests

At minimum prove deterministically that:

1. search/read/draft can succeed through the typed governed path under `ALLOW` without granting model authority;
2. send without an exact valid approval cannot produce the external send effect;
3. send after exact approval can execute once and yields a durable receipt;
4. changing recipient, cc/bcc, subject, body content/hash, attachment hashes, or account after approval invalidates that approval;
5. duplicate/retry handling does not duplicate a consequential send;
6. archive requires approval and cannot execute without it;
7. delete is denied and cannot produce the prohibited effect;
8. unknown/malformed Gmail actions/resources fail closed;
9. raw credentials do not enter agent/model-visible context or durable audit/receipt data;
10. applicable Phase 1–3/A004 regressions remain passing.

## Package required?

Yes.

## Next task on success

`LAC-B002` in a fresh implementation session. Do not begin it in the B001 session.
