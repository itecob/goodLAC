# ACTIVE TASK — LAC-V001

## Task ID
`LAC-V001`

## Objective
Productize the accepted LAC v1 Pi-reference path into a reproducible local-first Linux distribution without changing the accepted controller authority model.

## In scope
- Installer and clean-target installation workflow.
- The accepted `scripts/lac-pi` governed Pi launcher/profile as the reference user path.
- Configuration workflow for required local paths/runtime settings.
- Owner permission/approval UX over the accepted P004/P005 administration API; canonical authority must remain in LAC.
- Service auto-start where appropriate and explicitly bounded.
- Upgrade and database migration handling with pre-migration backup when required.
- Rollback/recovery behavior.
- Portable Linux distribution packaging and operating/recovery documentation.
- Deterministic clean-install, upgrade, rollback, restart, permission/approval and governed-effect regression tests.
- Mandatory owner-package release qualification defined in `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`.

## Out of scope
- Any additional harness integration.
- OpenClaw implementation.
- External-product/application workflow logic.
- Generic compatibility-protocol facade merely for breadth.
- Additional model-provider expansion.
- Moving policy, approval, identity, leases, receipts, credentials, durable authority state, or emergency control into Pi or a UI.
- Weakening the accepted sandbox, credential isolation, four-dimensional binding, exact approval, non-resumption, continuation, idempotency or emergency semantics.

## Required inputs
- Accepted Phase 5 reviewed commit recorded by the successor prompt.
- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, especially Phase 6 and package-verification requirements.
- `docs/PI_V1_GOVERNED_PROFILE.md`.
- `docs/NATIVE_LOCAL_CONSUMER_CONTRACT.md`.
- Accepted Phase 5 deterministic gates and owner execution evidence.

## Required outputs
- Reproducible v1 installer/package for the accepted Pi reference path.
- Bounded configuration and owner administration workflow.
- Upgrade/migration/rollback/recovery path.
- Portable operating documentation.
- Deterministic productization test suite and evidence.
- One release-qualified owner-executable package/handoff when owner mutation is required.

## Acceptance tests
- Clean installation into a disposable target succeeds and produces only the intended files/services/state.
- Post-install governed Pi uses the accepted controller-backed tool surface and sandbox boundary.
- Permission discovery, configured ALLOW, explicit DENY, exact REQUIRE_APPROVAL, emergency pause/resume, duplicate prevention and receipts remain functional.
- Ordinary standalone Pi is never represented as governed.
- Agent/model runtime cannot reach the admin surface or service credentials.
- Restart preserves canonical controller state and never auto-dispatches a continuation.
- Upgrade/migration preserves accepted durable state or fails closed with a restorable backup.
- Rollback restores the exact supported preinstall state.
- Offline/local governance remains usable without required SaaS.
- Package verification follows `build -> tests -> package -> clean-target install -> post-install tests -> rollback test where applicable -> package hash -> owner handoff`.
- Every owner-executable package passes the mandatory complete lifecycle qualification in `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`.
- Applicable retained Phase 5 and earlier security/conformance regression gates pass.

## Package required?
`yes`

## Next task on success
`LAC-P6-REVIEW` — fresh Phase 6/v1 productization phase-boundary independent review.
