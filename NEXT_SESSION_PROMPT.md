# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 1 C002 CONTINUATION

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
the active task.

Durable project state and Git are authoritative.

## Handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-C001 PASS`
- `PREDECESSOR_GIT_COMMIT=ddd0bf819948f611ea1d463dd9d09597a9f9e66e`
- `REVIEWED_GIT_COMMIT=NONE`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=${HOME}/Downloads/LAC_P1_C001_STATE_STORE_v0.1.0_20260910_145126.log`
- `EXPECTED_NEXT_TASK=LAC-C002`

Historical phase-boundary fact:

- Phase 0 fresh independent review passed commit `41dd4173ce62b311a1ab6fdde107937237940c2d`.
- That Phase 0 review was already consumed to advance into Phase 1 and is not
  an instruction to reopen Phase 0.

The C001 implementation commit is intentionally followed by one
session-control-only handoff commit that changes root `NEXT_SESSION_PROMPT.md`.
Verify the complete Git delta from `PREDECESSOR_GIT_COMMIT..HEAD`; the expected
delta is exactly `NEXT_SESSION_PROMPT.md`. Treat any other path as a discrepancy
to classify under the template.

## Required behavior

Follow `docs/NEXT_SESSION_PROMPT_TEMPLATE.md` as the operating protocol.

1. Establish the current Phase 1 position and boundedly verify C001 against
   live code and deterministic tests.
2. Do not create a fresh independent review for C001.
3. If C001 is valid, continue immediately into the active `LAC-C002` work in
   the same session.
4. Keep C002 limited to canonical effect-request semantics, deterministic
   canonical hashing, validation, persistence, and tests. Do not start policy,
   approval, lease, dispatch, sandbox, model, credential, or external-effect
   work early.
5. Use deterministic tests during implementation.
6. If owner-side mutation is required, advance C002 as far as possible first,
   then produce one meaningful package and exactly one self-contained Bash
   command under the package contract.
7. Do not stop after status, predecessor verification, or merely determining
   C002 requirements. Continue until a legitimate external stop gate in the
   installed template is reached.
8. Before any legitimate stop, provide the required durable status fields and
   complete successor handoff.
