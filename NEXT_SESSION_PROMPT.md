# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C009 IMPLEMENTATION SEGMENT

## Purpose

This is a **fresh implementation-segment session** for the user-owned Local Agent Controller.

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-C009`

Verify C008 boundedly, complete C009, test and correct C009, prepare the one owner-executable C009 package, then stop at the owner-execution gate. **Do not begin C010 in this conversation.**

## Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and only additional files needed for C009. Durable state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C008 PASS`
- `PREDECESSOR_GIT_COMMIT=d5efe63a71ca9c11de346dc6b0ccb2ca84132807`
- `HANDOFF_BASE_GIT_COMMIT=d5efe63a71ca9c11de346dc6b0ccb2ca84132807`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C008_SIMULATED_ADAPTER_v0.1.0_20260912_143650.log`
- `EXPECTED_NEXT_TASK=LAC-C009`
- `SESSION_SEGMENT=LAC-C009`

Historical Phase 0 review is already consumed and must not be reopened.

One handoff commit is expected after `PREDECESSOR_GIT_COMMIT`. Verify `PREDECESSOR_GIT_COMMIT..HEAD`. The only permitted post-C008 path is:

- `NEXT_SESSION_PROMPT.md`

Any other post-C008 material is a discrepancy to classify under the template.

Read the recorded C008 execution log directly from the authorized Downloads root if needed. Do not require the owner to paste successful deterministic output again.

## C009 objective

The live `tasks/ACTIVE_TASK.md` is controlling.

Implement the durable local emergency pause required by INV-011. While paused, new Phase 1 simulated effects must not reach adapter invocation, while existing controller state remains available for read-only inspection. Pause/resume state must survive restart and must not become an alternate authorization source.

Do not implement C010 receipt/audit expansion or duplicate-effect reconciliation. Do not implement any real filesystem, shell, network, email, calendar, credential, sandbox, model/harness, or external-service capability.

## Required procedure

Follow template v0.2.0.

1. Boundedly verify C008 live installation and evidence.
2. Implement all of C009.
3. Run C009 deterministic tests plus applicable C001-C008 regression tests.
4. Test predecessor-to-current schema/data migration if C009 requires one.
5. Correct in-scope defects and rerun the gate until PASS or a real blocker exists.
6. Build one owner-executable C009 package.
7. On success that package must install/verify C009, advance durable state to `LAC-C010`, install a populated root prompt for a **fresh C010 implementation session**, record owner execution evidence, and fail closed/roll back on unexpected state or failure.
8. Deliver exactly one owner Bash command.
9. Stop at `OWNER_EXECUTION_REQUIRED`.

Do not start C010 after producing the package.

After successful owner execution, the owner opens a new conversation and uses the stable launcher:

`Use the connected Web-File-Tool. Read and execute the live Local Agent Controller/NEXT_SESSION_PROMPT.md.`

If C009 package execution fails, C009 remains the active segment and must be remediated before any C010 work.

## Required stop status

Report `WHERE_WE_ARE`, `SESSION_SEGMENT=LAC-C009`, `WHAT_WAS_VERIFIED`, `WHAT_WAS_COMPLETED`, `WHAT_REMAINS_IN_CURRENT_PHASE`, `TOTAL_PROJECT_POSITION`, `BLOCKERS`, `STOP_GATE`, and `EXACT_NEXT_SAFE_ACTION`.
