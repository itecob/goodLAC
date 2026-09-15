# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 4 B001 GMAIL ADAPTER

`SESSION_SEGMENT=LAC-B001`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. Act as the **Lead Implementation Engineer** for exactly `LAC-B001`. Do not repeat the accepted Phase 3 review merely because `HEAD` is newer through review/workflow handoff administration, and do not begin `LAC-B002` in this session.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then inspect the controlling specification sections needed for B001, especially §§18, 22, 34, 38, and 49, plus `docs/CONTRACTS.md`, `docs/THREAT_MODEL.md`, existing Dispatcher/approval/receipt/idempotency code, and the tests needed to preserve the accepted authority boundary.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Fresh Independent Reviewer`
- `PREDECESSOR_RESULT=PASS`
- `REVIEWED_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `REVIEW_LIVE_GIT_COMMIT=76fe9a6ce33efad6a72592d00333d1dbe988ef09`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/a003_owner_execution.json`
- `EXPECTED_PHASE=PHASE_4_CHIEF_OF_STAFF_PILOT`
- `EXPECTED_ACTIVE_TASK=LAC-B001`
- `EXPECTED_NEXT_TASK=LAC-B002`

The accepted Phase 3 corrected implementation substance is `809bb01ec52e6f04d96f22c0195c47961b3efd7a`. The Phase 3 reviewer inspected the subsequent evidence/workflow handoff and returned PASS. The owner review-handoff package creates one additional workflow commit. Before implementing B001, inspect the complete `809bb01ec52e6f04d96f22c0195c47961b3efd7a`-to-live-`HEAD` delta and require its path set to be exactly:

- `PROJECT_STATE.json`;
- `tasks/ACTIVE_TASK.md`;
- `NEXT_SESSION_PROMPT.md`;
- `qualification/evidence/a003_owner_execution.json`.

Those paths are non-material Phase 3 evidence/workflow administration only. Any other implementation, tests, qualification, architecture, contracts, threat model, ADR, upstream pin/license, or acceptance-criteria drift invalidates review preservation and is a blocker. If the delta is exact, record `REVIEW_PRESERVED_ACROSS_NONMATERIAL_DELTA=true` and proceed directly into B001 after bounded predecessor verification.

## B001 objective

Implement the typed Gmail adapter required by `tasks/ACTIVE_TASK.md` without redesigning the authority core. The agent/model may propose Gmail operations; deterministic controller software remains responsible for authorization, exact approval binding, pre-dispatch re-evaluation, leases, idempotency, adapter invocation, receipts, audit, and credential isolation.

The initial typed Gmail action surface is:

- `email.search`
- `email.read`
- `email.draft`
- `email.send`
- `email.archive`
- `email.delete`

Use the controlling policy semantics and acceptance tests in `tasks/ACTIVE_TASK.md`. In particular, `email.send` approval must bind account, to, cc, bcc, subject, body hash, and attachment hashes; any security-relevant mutation invalidates approval. Sending must be exactly-once under retry/duplicate conditions. Credentials remain controller/adapter-side references and must not enter the agent/model context or generic shell.

Use synthetic/local deterministic test doubles by default. Do not perform real production Gmail effects or ingest production credentials. A live external qualification requires a dedicated test account or separate explicit bounded owner authority.

## Required implementation lifecycle

1. Perform bounded predecessor verification only. Do not redo the Phase 3 independent review when the handoff delta is exact.
2. Implement `LAC-B001` completely.
3. Run B001-specific deterministic tests and the full applicable regression gate.
4. Correct in-scope defects and rerun affected/full gates.
5. Produce one owner-executable package and exactly one self-contained Bash command.
6. The successful package must advance durable state to `LAC-B002` and install a populated successor `NEXT_SESSION_PROMPT.md` before reporting PASS.
7. Stop at `OWNER_EXECUTION_REQUIRED`. Do not implement B002 in this conversation.

## Security validation framing

Use only user-owned repository state, synthetic fixtures, local fake/test services, deterministic databases, and bounded test accounts if separately authorized. Verify documented invariants and actual negative outcomes; do not use real credentials, production accounts, third-party targets, generalized security-control circumvention, or unrelated external effects.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-B001`
- `PREDECESSOR_RESULT=PASS`
- `REVIEWED_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
