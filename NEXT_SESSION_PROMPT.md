# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C005 IMPLEMENTATION SEGMENT

## Purpose

This is a **fresh implementation-segment session** for the user-owned Local Agent Controller.

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-C005`

Verify C004 boundedly, complete C005, test and correct C005, prepare the one owner-executable C005 package, then stop at the owner-execution gate. **Do not begin C006 in this conversation.**

## Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and only additional files needed for C005. Durable state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C004 PASS`
- `PREDECESSOR_GIT_COMMIT=40106940fdf72e1f3f8f50007e0aea0a5966fe66`
- `HANDOFF_BASE_GIT_COMMIT=40106940fdf72e1f3f8f50007e0aea0a5966fe66`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C004_APPROVAL_STATE_v0.1.0_20260911_145728.log`
- `EXPECTED_NEXT_TASK=LAC-C005`
- `SESSION_SEGMENT=LAC-C005`

Historical Phase 0 review is already consumed and must not be reopened.

One handoff commit is expected after `PREDECESSOR_GIT_COMMIT`. Verify `PREDECESSOR_GIT_COMMIT..HEAD`. The only permitted post-C004 path is:

- `NEXT_SESSION_PROMPT.md`

Any other post-C004 material is a discrepancy to classify under the template.

Read the recorded C004 execution log directly from the authorized Downloads root if needed. Do not require the owner to paste successful deterministic output again.

## C005 objective

The live `tasks/ACTIVE_TASK.md` is controlling.

Implement deterministic exact post-approval binding validation for the current canonical effect request. An approval must fail closed if the request identity/hash differs, if the request was security-relevantly mutated, if the approval is not `APPROVE`/`ONCE`, if it is expired or already consumed, or if its qualifying durable `REQUIRE_APPROVAL` policy-decision binding is no longer valid.

Do not implement current-policy pre-dispatch re-evaluation, approval consumption as an execution transition, execution leases, dispatch, effects, emergency pause, sandboxing, credentials, model/harness integration, or external services.

## Required procedure

Follow template v0.2.0.

1. Boundedly verify C004 live installation and evidence.
2. Implement all of C005.
3. Run C005 deterministic tests plus applicable C001-C004 regression tests.
4. Test schema/data migration if C005 genuinely requires one.
5. Correct in-scope defects and rerun the gate until PASS or a real blocker exists.
6. Build one owner-executable C005 package.
7. On success that package must install/verify C005, advance durable state to `LAC-C006`, install a populated root prompt for a **fresh C006 implementation session**, record owner execution evidence, and fail closed/roll back on unexpected state or failure.
8. Deliver exactly one owner Bash command.
9. Stop at `OWNER_EXECUTION_REQUIRED`.

Do not start C006 after producing the package.

After successful owner execution, the owner opens a new conversation and uses the stable launcher:

`Use the connected Web-File-Tool. Read and execute the live Local Agent Controller/NEXT_SESSION_PROMPT.md.`

If C005 package execution fails, C005 remains the active segment and must be remediated before any C006 work.

## Required stop status

Report `WHERE_WE_ARE`, `SESSION_SEGMENT=LAC-C005`, `WHAT_WAS_VERIFIED`, `WHAT_WAS_COMPLETED`, `WHAT_REMAINS_IN_CURRENT_PHASE`, `TOTAL_PROJECT_POSITION`, `BLOCKERS`, `STOP_GATE`, and `EXACT_NEXT_SAFE_ACTION`.
