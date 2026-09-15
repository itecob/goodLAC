# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / B002 CALENDAR ADAPTER

`SESSION_SEGMENT=LAC-B002`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-B002` Calendar adapter implementation. Do not begin Chief of Staff E2E (`LAC-B003`) in this session.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md` only as needed for Calendar / Phase 4 / binding invariants;
- `qualification/evidence/b001_owner_execution.json`;
- `qualification/evidence/a004_owner_uat_revalidation.json` only if needed to confirm the preserved Phase 3/A004 foundation;
- only the existing B001 credential seam and authority/effect interfaces/tests needed to implement B002.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer / LAC-B001`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=f965b723b88475a2ced8a363d88cdd5044b6453c`
- `HANDOFF_START_GIT_COMMIT=9684486783ee7b9e2a2126ecea6a5cdf2f4353fd`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/b001_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_CHIEF_OF_STAFF_PILOT`
- `EXPECTED_ACTIVE_TASK=LAC-B002`
- `EXPECTED_NEXT_TASK=LAC-B003`

The accepted Phase 3 independent review and A004 owner-UAT PASS remain preserved. B001 is a Phase 4 implementation segment, not a new independent phase review.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm B001 owner-execution evidence is valid, durable state/task/prompt are mutually consistent, the B001 implementation commit is in Git history, and the live HEAD delta after that implementation commit is handoff-only.
2. Implement `LAC-B002` completely as defined by `tasks/ACTIVE_TASK.md` and the controlling Calendar/Phase 4 specification.
3. Preserve all binding LAC invariants: no implicit authority, model output never authorization, exact approval binding, pre-dispatch policy re-evaluation, deny precedence, idempotency/duplicate prevention, durable truth, fail-closed behavior, emergency pause, and credential isolation.
4. Use deterministic local/synthetic fixtures for automated tests. Do not put real service credentials in model context, source, logs, test fixtures, receipts, or package artifacts. If live Calendar qualification is genuinely required and no authorized dedicated test account/credential path exists, stop only at the appropriate valid external-authority/dependency gate after completing all implementable local work.
5. Run focused B002 tests and the applicable accepted regression gate, including B001; correct in-scope defects before handoff.
6. Produce one owner-executable package that completes B002 and activates fresh `LAC-B003` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement B003 in this conversation.

## Scope discipline

Do not add Chief of Staff E2E, OpenClaw, Omarchy Agent OS, unrelated UI, voice, memory architecture, generalized workflow features, new shell executables, or weaker authority semantics.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-B002`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
