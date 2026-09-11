# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C004 IMPLEMENTATION SEGMENT

## Purpose

This is a **fresh implementation-segment session** for the user-owned Local Agent Controller.

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-C004`

Verify C003 boundedly, complete C004, test and correct C004, prepare the one owner-executable C004 package, then stop at the owner-execution gate. **Do not begin C005 in this conversation.**

## Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and only additional files needed for C004. Durable state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C003 PASS`
- `PREDECESSOR_GIT_COMMIT=d414d8dc2014b7be4c80b09d2cd3bbcbd0bfe9b0`
- `HANDOFF_BASE_GIT_COMMIT=6a6fbc6db7f61b5dc661e5c31cc7fad232f1b2f7`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C003_POLICY_INTERFACE_v0.1.0_20260911_012454.log`
- `EXPECTED_NEXT_TASK=LAC-C004`
- `SESSION_SEGMENT=LAC-C004`

Historical Phase 0 review is already consumed and must not be reopened.

A workflow-only commit may exist after `HANDOFF_BASE_GIT_COMMIT` to install template v0.2.0. Verify `PREDECESSOR_GIT_COMMIT..HEAD`. The only permitted post-C003 paths are:

- `NEXT_SESSION_PROMPT.md`
- `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Any other post-C003 material is a discrepancy to classify under the template.

Read the recorded C003 execution log directly from the authorized Downloads root if needed. Do not require the owner to paste the successful 32-test output again.

## C004 objective

The live `tasks/ACTIVE_TASK.md` is controlling.

Implement durable approval state for exact canonical effect requests after a `REQUIRE_APPROVAL` policy decision, without execution or dispatch.

In scope includes versioned `lac.approval/v1`, approval/request/hash/approver/decision/scope/timestamps, initial `ONCE` scope, explicit `APPROVE`/`REJECT`, expiry validation, durable persistence, binding to an existing canonical request and qualifying policy decision, immutable approval identity, restart persistence, required schema migration, and deterministic tests.

Do not implement C005 exact post-approval binding enforcement, leases, dispatch, effects, emergency pause, sandboxing, credentials, model/harness integration, or external services.

## Required procedure

Follow template v0.2.0.

1. Boundedly verify C003 live installation and evidence.
2. Implement all of C004.
3. Run C004 deterministic tests plus applicable C001-C003 regression tests.
4. Test predecessor-schema migration when relevant.
5. Correct in-scope defects and rerun the gate until PASS or a real blocker exists.
6. Build one owner-executable C004 package.
7. On success that package must install/verify C004, advance durable state to `LAC-C005`, install a populated root prompt for a **fresh C005 implementation session**, record owner execution evidence, and fail closed/roll back on unexpected state or failure.
8. Deliver exactly one owner Bash command.
9. Stop at `OWNER_EXECUTION_REQUIRED`.

Do not start C005 after producing the package.

After successful owner execution, the owner opens a new conversation and uses the stable launcher:

`Use the connected Web-File-Tool. Read and execute the live Local Agent Controller/NEXT_SESSION_PROMPT.md.`

If C004 package execution fails, C004 remains the active segment and must be remediated before any C005 work.

## Required stop status

Report `WHERE_WE_ARE`, `SESSION_SEGMENT=LAC-C004`, `WHAT_WAS_VERIFIED`, `WHAT_WAS_COMPLETED`, `WHAT_REMAINS_IN_CURRENT_PHASE`, `TOTAL_PROJECT_POSITION`, `BLOCKERS`, `STOP_GATE`, and `EXACT_NEXT_SAFE_ACTION`.
