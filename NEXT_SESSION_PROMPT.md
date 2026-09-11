# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C004 CONTINUATION

## Purpose

Continue the user-owned Local Agent Controller from live durable state. This is ordinary Phase 1 implementation continuation, not a phase-boundary review.

Use the connected read-only Tunnel/Web-File-Tool.

Project root label:

`Local Agent Controller`

## Mandatory first reads

Read exactly these project files first, in order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`

Then read:

5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Read the controlling specification and only the additional files needed for the active task. Durable project state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C003 PASS`
- `PREDECESSOR_GIT_COMMIT=d414d8dc2014b7be4c80b09d2cd3bbcbd0bfe9b0`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C003_POLICY_INTERFACE_v0.1.0_20260911_012454.log`
- `EXPECTED_NEXT_TASK=LAC-C004`

The C003 implementation commit is intentionally followed by one session-control-only handoff commit changing root `NEXT_SESSION_PROMPT.md`. Verify the complete Git delta from `PREDECESSOR_GIT_COMMIT..HEAD`; expected delta: exactly `NEXT_SESSION_PROMPT.md`. Any other path is a discrepancy under the installed workflow.

## Required behavior

Follow `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`.

1. Boundedly verify C003 against live code, state, Git identity, and deterministic tests.
2. Do not create an independent review for C003.
3. If valid, continue immediately into `LAC-C004` in the same session.
4. Keep C004 limited to durable approval state and binding to the existing request/policy-decision records. Do not implement C005 post-approval binding enforcement, leases, dispatch, effects, pause, sandbox, credentials, model/harness integration, or external services early.
5. Use deterministic tests during implementation.
6. If owner-side mutation is required, advance C004 as far as possible first, then produce one meaningful package and exactly one self-contained Bash command.
7. Do not stop after status or predecessor verification. Continue until a legitimate external stop gate is reached.
8. Before any legitimate stop, provide all required durable status fields and the complete successor handoff.
