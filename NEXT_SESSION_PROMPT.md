# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C008 IMPLEMENTATION SEGMENT

## Purpose

This is a **fresh implementation-segment session** for the user-owned Local Agent Controller.

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one segment:

`SESSION_SEGMENT=LAC-C008`

Verify C007 boundedly, complete C008, test and correct C008, prepare the one owner-executable C008 package, then stop at the owner-execution gate. **Do not begin C009 in this conversation.**

## Mandatory first reads

Read exactly these first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and only additional files needed for C008. Durable state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C007 PASS`
- `PREDECESSOR_GIT_COMMIT=4c930eee2eb1290965efd1cf471c4151814b2630`
- `HANDOFF_BASE_GIT_COMMIT=4c930eee2eb1290965efd1cf471c4151814b2630`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C007_DISPATCHER_v0.1.0_20260912_062040.log`
- `EXPECTED_NEXT_TASK=LAC-C008`
- `SESSION_SEGMENT=LAC-C008`

Historical Phase 0 review is already consumed and must not be reopened.

One handoff commit is expected after `PREDECESSOR_GIT_COMMIT`. Verify `PREDECESSOR_GIT_COMMIT..HEAD`. The only permitted post-C007 path is:

- `NEXT_SESSION_PROMPT.md`

Any other post-C007 material is a discrepancy to classify under the template.

Read the recorded C007 execution log directly from the authorized Downloads root if needed. Do not require the owner to paste successful deterministic output again.

## C008 objective

The live `tasks/ACTIVE_TASK.md` is controlling.

Implement the first concrete deterministic simulated effect adapter behind the C007 `EffectAdapter` boundary. It must support only an explicitly declared simulated request shape, produce a deterministic non-consequential simulated result, and be exercised through the C007 dispatcher so DENY, exact approval, and lease ordering remain authoritative.

Do not implement any real filesystem, shell, network, email, calendar, credential, or other external effect. Do not implement emergency pause, receipt/audit expansion, sandboxing, model/harness integration, or external services.

## Required procedure

Follow template v0.2.0.

1. Boundedly verify C007 live installation and evidence.
2. Implement all of C008.
3. Run C008 deterministic tests plus applicable C001-C007 regression tests.
4. Test predecessor-to-current schema/data migration if C008 requires one.
5. Correct in-scope defects and rerun the gate until PASS or a real blocker exists.
6. Build one owner-executable C008 package.
7. On success that package must install/verify C008, advance durable state to `LAC-C009`, install a populated root prompt for a **fresh C009 implementation session**, record owner execution evidence, and fail closed/roll back on unexpected state or failure.
8. Deliver exactly one owner Bash command.
9. Stop at `OWNER_EXECUTION_REQUIRED`.

Do not start C009 after producing the package.

After successful owner execution, the owner opens a new conversation and uses the stable launcher:

`Use the connected Web-File-Tool. Read and execute the live Local Agent Controller/NEXT_SESSION_PROMPT.md.`

If C008 package execution fails, C008 remains the active segment and must be remediated before any C009 work.

## Required stop status

Report `WHERE_WE_ARE`, `SESSION_SEGMENT=LAC-C008`, `WHAT_WAS_VERIFIED`, `WHAT_WAS_COMPLETED`, `WHAT_REMAINS_IN_CURRENT_PHASE`, `TOTAL_PROJECT_POSITION`, `BLOCKERS`, `STOP_GATE`, and `EXACT_NEXT_SAFE_ACTION`.
