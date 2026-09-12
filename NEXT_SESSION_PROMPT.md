# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C010 IMPLEMENTATION SEGMENT

## Purpose

This is a **fresh implementation-segment session** for the user-owned Local Agent Controller.

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-C010`

Verify C009 boundedly, complete C010, test and correct C010, prepare the one owner-executable C010 package, then stop at the owner-execution gate. **Do not begin the Phase 1 independent review or Phase 2 implementation in this conversation.**

## Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and only additional files needed for C010. Durable state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C009 PASS`
- `PREDECESSOR_GIT_COMMIT=edf34912fdba638abd66379848d7e09be447f166`
- `HANDOFF_BASE_GIT_COMMIT=edf34912fdba638abd66379848d7e09be447f166`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C009_EMERGENCY_PAUSE_v0.1.1_20260912_151320.log`
- `EXPECTED_NEXT_TASK=LAC-C010`
- `SESSION_SEGMENT=LAC-C010`

Historical Phase 0 review is already consumed and must not be reopened.

One handoff commit is expected after `PREDECESSOR_GIT_COMMIT`. Verify `PREDECESSOR_GIT_COMMIT..HEAD`. The only permitted post-C009 path is:

- `NEXT_SESSION_PROMPT.md`

Any other post-C009 material is a discrepancy to classify under the template.

Read the recorded C009 execution log directly from the authorized Downloads root if needed. Do not require the owner to paste successful deterministic output again.

## C010 objective

The live `tasks/ACTIVE_TASK.md` is controlling.

Complete the Phase 1 walking skeleton with durable effect receipts/audit and duplicate-effect reconciliation for the governed simulated-effect path. Receipt/audit state must reflect canonical effect state and outcomes, survive restart, distinguish relevant crash windows, and never become an alternate authorization source.

Do not implement Phase 2 filesystem/shell/package/service enforcement or any real network, email, calendar, Slack, Git, deploy, credential, sandbox, model/harness, or external-service capability.

## Required procedure

Follow template v0.2.0.

1. Boundedly verify C009 live installation and evidence.
2. Implement all of C010.
3. Run C010 deterministic tests plus applicable C001-C009 regression tests.
4. Implement and test the predecessor-to-current schema/data migration required by C010, including restart and failure behavior.
5. Correct in-scope defects and rerun the gate until PASS or a real blocker exists.
6. Build one owner-executable C010 package.
7. On success that package must install/verify C010, advance durable state to a Phase 1 review candidate, install a populated root prompt for one **fresh independent Phase 1 boundary review**, record owner execution evidence, and fail closed/roll back on unexpected state or failure.
8. Deliver exactly one owner Bash command.
9. Stop at `OWNER_EXECUTION_REQUIRED`.

Do not perform the independent review or start Phase 2 after producing the package.

After successful owner execution, the owner opens a new conversation and uses the stable launcher:

`Use the connected Web-File-Tool. Read and execute the live Local Agent Controller/NEXT_SESSION_PROMPT.md.`

If C010 package execution fails, C010 remains the active segment and must be remediated before any Phase 1 review or Phase 2 work.

## Required stop status

Report `WHERE_WE_ARE`, `SESSION_SEGMENT=LAC-C010`, `WHAT_WAS_VERIFIED`, `WHAT_WAS_COMPLETED`, `WHAT_REMAINS_IN_CURRENT_PHASE`, `TOTAL_PROJECT_POSITION`, `BLOCKERS`, `STOP_GATE`, and `EXACT_NEXT_SAFE_ACTION`.
