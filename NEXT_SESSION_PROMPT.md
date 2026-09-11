# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C006 IMPLEMENTATION SEGMENT

## Purpose

This is a **fresh implementation-segment session** for the user-owned Local Agent Controller.

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-C006`

Verify C005 boundedly, complete C006, test and correct C006, prepare the one owner-executable C006 package, then stop at the owner-execution gate. **Do not begin C007 in this conversation.**

## Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and only additional files needed for C006. Durable state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C005 PASS`
- `PREDECESSOR_GIT_COMMIT=909edc05805eaae1694cdf80b5accb080801d470`
- `HANDOFF_BASE_GIT_COMMIT=909edc05805eaae1694cdf80b5accb080801d470`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C005_EXACT_APPROVAL_BINDING_v0.1.0_20260911_194944.log`
- `EXPECTED_NEXT_TASK=LAC-C006`
- `SESSION_SEGMENT=LAC-C006`

Historical Phase 0 review is already consumed and must not be reopened.

One handoff commit is expected after `PREDECESSOR_GIT_COMMIT`. Verify `PREDECESSOR_GIT_COMMIT..HEAD`. The only permitted post-C005 path is:

- `NEXT_SESSION_PROMPT.md`

Any other post-C005 material is a discrepancy to classify under the template.

Read the recorded C005 execution log directly from the authorized Downloads root if needed. Do not require the owner to paste successful deterministic output again.

## C006 objective

The live `tasks/ACTIVE_TASK.md` is controlling.

Implement the deterministic durable execution-lease primitive for canonical effect requests. On one machine, at most one current unexpired executor lease may own a request at a time; lease state must persist and expiry/reacquisition must be deterministic.

Lease acquisition is **not authorization**. Do not implement current-policy pre-dispatch re-evaluation, dispatch, simulated or real effects, approval consumption as an execution transition, emergency pause, receipts/audit expansion, sandboxing, credentials, model/harness integration, or external services.

## Required procedure

Follow template v0.2.0.

1. Boundedly verify C005 live installation and evidence.
2. Implement all of C006.
3. Run C006 deterministic tests plus applicable C001-C005 regression tests.
4. Test predecessor-to-current schema/data migration if C006 requires one.
5. Correct in-scope defects and rerun the gate until PASS or a real blocker exists.
6. Build one owner-executable C006 package.
7. On success that package must install/verify C006, advance durable state to `LAC-C007`, install a populated root prompt for a **fresh C007 implementation session**, record owner execution evidence, and fail closed/roll back on unexpected state or failure.
8. Deliver exactly one owner Bash command.
9. Stop at `OWNER_EXECUTION_REQUIRED`.

Do not start C007 after producing the package.

After successful owner execution, the owner opens a new conversation and uses the stable launcher:

`Use the connected Web-File-Tool. Read and execute the live Local Agent Controller/NEXT_SESSION_PROMPT.md.`

If C006 package execution fails, C006 remains the active segment and must be remediated before any C007 work.

## Required stop status

Report `WHERE_WE_ARE`, `SESSION_SEGMENT=LAC-C006`, `WHAT_WAS_VERIFIED`, `WHAT_WAS_COMPLETED`, `WHAT_REMAINS_IN_CURRENT_PHASE`, `TOTAL_PROJECT_POSITION`, `BLOCKERS`, `STOP_GATE`, and `EXACT_NEXT_SAFE_ACTION`.
