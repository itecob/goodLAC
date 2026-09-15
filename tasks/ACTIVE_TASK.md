# ACTIVE TASK — LAC-A004-UAT

## Objective

Perform owner hands-on validation of the installed A004 interactive baseline harness before Phase 4 business adapters begin.

## In scope

- Use `scripts/lac-baseline` and `docs/A004_OWNER_BASELINE_UAT.md` against the dedicated bounded A004 workspace.
- Validate normal multi-turn conversation, governed read/create/replace/shell behavior, observable receipts, denied boundary behavior, and clean shutdown/restart.
- Inspect `qualification/evidence/a004_owner_execution.json` and live installed files as predecessor evidence.
- If the owner explicitly accepts the baseline, prepare the minimal durable transition to `LAC-B001` without implementing B001 in this session.
- If a concrete A004 defect is observed, keep scope on A004 remediation and do not advance to B001.

## Out of scope

- Gmail, Calendar, Chief of Staff implementation, prompts, credentials, or production accounts.
- New authority semantics, new effect types, sandbox redesign, model/runtime replacement, web UI, voice UI, or memory architecture.
- Reopening the accepted Phase 3 independent review absent evidence of material regression.

## Required inputs

- `PROJECT_STATE.json`
- `docs/ARCHITECTURE.md`
- `UPSTREAM_LOCK.json`
- `tasks/ACTIVE_TASK.md`
- `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`
- `qualification/evidence/a004_owner_execution.json`
- `docs/A004_OWNER_BASELINE_UAT.md`
- installed A004 implementation and Git history

## Required outputs

- Owner validation result: `PASS` or a concrete defect description.
- On owner PASS only: one minimal owner-executable transition package that makes `LAC-B001` active and installs its populated successor prompt.
- On failure: an A004 remediation handoff; B001 remains deferred.

## Acceptance tests

1. `/status` reports the expected pinned baseline model, Bubblewrap boundary, bounded workspace, and exactly four governed tools.
2. A two-turn conversation demonstrates retained session context through the same sandboxed Pi agent.
3. Governed create/read/replace operations work in the bounded workspace and show durable successful receipt identities.
4. Governed allowed shell inspection works and shows a durable successful receipt.
5. An out-of-workspace filesystem request fails without exposing the prohibited host content.
6. A shell request outside the accepted executable surface fails without producing the prohibited host process effect.
7. Hidden reasoning and service credentials are not exposed in the terminal surface.
8. `/quit` shuts the session down cleanly and a fresh `scripts/lac-baseline` restart works.
9. Owner explicitly accepts the baseline as sufficient to proceed to Phase 4.

## Package required?

Yes, but only for the durable post-UAT transition after explicit owner PASS.

## Next task on success

`LAC-B001` — Gmail adapter. Do not implement it until A004-UAT is explicitly accepted and the transition package succeeds.
