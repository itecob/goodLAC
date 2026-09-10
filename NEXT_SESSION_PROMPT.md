# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C003 CONTINUATION

## Purpose

Continue the user-owned Local Agent Controller from live durable state. This
is ordinary Phase 1 implementation continuation, not a phase-boundary review.

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

Read the controlling specification and only the additional files needed for
the active task. Durable project state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C002 PASS`
- `PREDECESSOR_GIT_COMMIT=a7c982835d8de813e9b3cf63712be933552014bd`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C002_EFFECT_REQUEST_v0.1.0_20260910_160551.log`
- `EXPECTED_NEXT_TASK=LAC-C003`

The C002 implementation commit is intentionally followed by one
session-control-only handoff commit changing root `NEXT_SESSION_PROMPT.md`.
Verify the complete Git delta from `PREDECESSOR_GIT_COMMIT..HEAD`; expected
delta: exactly `NEXT_SESSION_PROMPT.md`. Any other path is a discrepancy under
the installed workflow.

## Required behavior

Follow `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`.

1. Boundedly verify C002 against live code, state, Git identity, and
   deterministic tests.
2. Do not create an independent review for C002.
3. If valid, continue immediately into `LAC-C003` in the same session.
4. Keep C003 limited to deterministic policy-decision domain/interface,
   precedence, request/hash binding, minimal persistence, and tests.
5. Do not start approvals, leases, dispatch, effects, pause, sandbox,
   credentials, model/harness integration, or external services early.
6. Use deterministic tests during implementation.
7. If owner-side mutation is required, advance C003 as far as possible first,
   then produce one meaningful package and exactly one self-contained Bash
   command.
8. Do not stop after status or predecessor verification. Continue until a
   legitimate external stop gate is reached.
9. Before any legitimate stop, provide all required durable status fields and
   the complete successor handoff.
