# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C007 IMPLEMENTATION SEGMENT

## Purpose

This is a **fresh implementation-segment session** for the user-owned Local Agent Controller.

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-C007`

Verify C006 boundedly, complete C007, test and correct C007, prepare the one owner-executable C007 package, then stop at the owner-execution gate. **Do not begin C008 in this conversation.**

## Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and only additional files needed for C007. Durable state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C006 PASS`
- `PREDECESSOR_GIT_COMMIT=f4dc6266ea454dce254ed81a1e26e127adf6e5fa`
- `HANDOFF_BASE_GIT_COMMIT=f4dc6266ea454dce254ed81a1e26e127adf6e5fa`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C006_EXECUTION_LEASE_v0.1.0_20260911_222314.log`
- `EXPECTED_NEXT_TASK=LAC-C007`
- `SESSION_SEGMENT=LAC-C007`

Historical Phase 0 review is already consumed and must not be reopened.

One handoff commit is expected after `PREDECESSOR_GIT_COMMIT`. Verify `PREDECESSOR_GIT_COMMIT..HEAD`. The only permitted post-C006 path is:

- `NEXT_SESSION_PROMPT.md`

Any other post-C006 material is a discrepancy to classify under the template.

Read the recorded C006 execution log directly from the authorized Downloads root if needed. Do not require the owner to paste successful deterministic output again.

## C007 objective

The live `tasks/ACTIVE_TASK.md` is controlling.

Implement the deterministic pre-dispatch dispatcher boundary. Immediately before any adapter invocation, current policy must be re-evaluated; `DENY` must fail closed; `REQUIRE_APPROVAL` must satisfy the exact C005 approval binding and one-time transition; and a C006 execution lease must be acquired before the adapter can be invoked.

C007 may use an injected deterministic test double to prove ordering and denial semantics. Do not implement the production simulated adapter, any real external effect, emergency pause, receipt/audit expansion, sandboxing, credentials, model/harness integration, or external services.

## Required procedure

Follow template v0.2.0.

1. Boundedly verify C006 live installation and evidence.
2. Implement all of C007.
3. Run C007 deterministic tests plus applicable C001-C006 regression tests.
4. Test predecessor-to-current schema/data migration if C007 requires one.
5. Correct in-scope defects and rerun the gate until PASS or a real blocker exists.
6. Build one owner-executable C007 package.
7. On success that package must install/verify C007, advance durable state to `LAC-C008`, install a populated root prompt for a **fresh C008 implementation session**, record owner execution evidence, and fail closed/roll back on unexpected state or failure.
8. Deliver exactly one owner Bash command.
9. Stop at `OWNER_EXECUTION_REQUIRED`.

Do not start C008 after producing the package.

After successful owner execution, the owner opens a new conversation and uses the stable launcher:

`Use the connected Web-File-Tool. Read and execute the live Local Agent Controller/NEXT_SESSION_PROMPT.md.`

If C007 package execution fails, C007 remains the active segment and must be remediated before any C008 work.

## Required stop status

Report `WHERE_WE_ARE`, `SESSION_SEGMENT=LAC-C007`, `WHAT_WAS_VERIFIED`, `WHAT_WAS_COMPLETED`, `WHAT_REMAINS_IN_CURRENT_PHASE`, `TOTAL_PROJECT_POSITION`, `BLOCKERS`, `STOP_GATE`, and `EXACT_NEXT_SAFE_ACTION`.
