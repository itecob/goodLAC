# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / B001 GMAIL ADAPTER

`SESSION_SEGMENT=LAC-B001`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** `LAC-B001` Gmail adapter implementation. Do not begin Calendar (`LAC-B002`) or Chief of Staff E2E (`LAC-B003`) in this session.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md` only as needed for Gmail / Phase 4 / binding invariants;
- `qualification/evidence/a004_owner_uat_revalidation.json`;
- `qualification/evidence/a004_uat_handoff_execution.json`;
- only the existing authority/effect/credential interfaces and tests needed to implement B001.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Owner Validation Checkpoint / LAC-A004-UAT`
- `PREDECESSOR_RESULT=OWNER_UAT_PASS`
- `PREDECESSOR_GIT_COMMIT=8aab0f39e84dcb627c394df4811d565fae054002`
- `HANDOFF_START_GIT_COMMIT=eaf83cfa89753818bdb45a27de1d2c8ce1032127`
- `ORIGINAL_A004_IMPLEMENTATION_GIT_COMMIT=94c7db928b3848069d2a7c432316db0d88477871`
- `A004_REMEDIATION_GIT_COMMIT=c930cacbd1260f24477e8fb16056f463f9a3c306`
- `REVIEWED_PHASE3_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `OWNER_UAT_PASS_EVIDENCE=qualification/evidence/a004_owner_uat_revalidation.json`
- `OWNER_HANDOFF_EXECUTION_EVIDENCE=qualification/evidence/a004_uat_handoff_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_4_CHIEF_OF_STAFF_PILOT`
- `EXPECTED_ACTIVE_TASK=LAC-B001`
- `EXPECTED_NEXT_TASK=LAC-B002`

The accepted Phase 3 independent review remains preserved. A004 was an additive usability checkpoint and has passed after remediation of `A004-UAT-B001` and `A004-UAT-B002`.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm A004 owner-UAT PASS evidence and handoff execution evidence are valid, durable state/task/prompt are mutually consistent, the predecessor commit is in Git history, and the live HEAD delta after the predecessor commit is handoff-only.
2. Implement `LAC-B001` completely as defined by `tasks/ACTIVE_TASK.md` and the controlling Gmail/Phase 4 specification.
3. Preserve all binding LAC invariants: no implicit authority, model output never authorization, exact approval binding, pre-dispatch policy re-evaluation, deny precedence, idempotency/duplicate prevention, durable truth, fail-closed behavior, emergency pause, and credential isolation.
4. Use deterministic local/synthetic fixtures for automated tests. Do not put real service credentials in model context, source, logs, test fixtures, receipts, or package artifacts. If live Gmail qualification is genuinely required and no authorized dedicated test account/credential path exists, stop only at the appropriate valid external-authority/dependency gate after completing all implementable local work.
5. Run focused B001 tests and the applicable accepted regression gate; correct in-scope defects before handoff.
6. Produce one owner-executable package that completes B001 and activates fresh `LAC-B002` on success. Stop at `OWNER_EXECUTION_REQUIRED`; do not implement B002 in this conversation.

## Scope discipline

Do not add Calendar, Chief of Staff E2E, OpenClaw, Omarchy Agent OS, unrelated UI, voice, memory architecture, generalized workflow features, new shell executables, or weaker authority semantics.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-B001`
- `PREDECESSOR_RESULT=OWNER_UAT_PASS`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
