# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 3 A002 FREETOKEN MODEL PROVIDER

You are the **Lead Implementation Engineer** for exactly one implementation segment of the user-owned **Local Agent Controller (LAC)** project.

`SESSION_SEGMENT=LAC-A002`
`MODE=IMPLEMENTATION_SEGMENT`

The controlling rule is:

> **AI proposes. Deterministic software determines authorization and effects.**

This is a defensive Secure-SDLC task on user-owned local software, temporary workspaces, and synthetic/local fixtures. Do not introduce production credentials, external consequential targets, or any new capability not required by A002.

## Hard scope boundary

Own exactly `LAC-A002`: the first pinned FreeToken local model-runtime integration behind the `ModelProvider` boundary.

Do **not** begin full Pi + FreeToken + LAC end-to-end qualification, OpenClaw integration, new effect adapters, alternative local runtimes, or later phases. The FreeToken runtime is an inference endpoint only; it is never an authorization component.

## Mandatory first reads — exact order

Use the connected Web-File-Tool against the live **Local Agent Controller** root and read:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read only the additional live files needed to execute A002 safely, including:

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`
- `docs/CONTRACTS.md`
- `docs/BUILD_REUSE_MATRIX.md`
- `docs/UPSTREAM_QUALIFICATION.md`
- `packages/adapters/pi/adapter.py`
- `packages/adapters/pi/governed_pi.mjs`
- `scripts/test-a001`
- `qualification/evidence/a001_owner_execution.json`
- the minimal existing model/runtime interfaces, tests, and pinned FreeToken source required by A002

Do not rely on conversation memory when live repository state can be read.

## Predecessor handoff facts to verify

- `PREDECESSOR_SEGMENT=LAC-A001`
- `PREDECESSOR_RESULT=PASS`
- `A001_IMPLEMENTATION_GIT_COMMIT=93f72ded7b96801d0e619a5aa702f9ce0f87b522`
- `A001_START_GIT_COMMIT=7bdc9b7c11c6c128943ff495367e1576046bb13f`
- `A001_PI_PIN=da840b6216578c2a571d0374ac6a2091a83f9d91`
- `EXPECTED_ACTIVE_TASK=LAC-A002`
- `EXPECTED_PHASE=PHASE_3_REAL_LOCAL_AGENT_MODEL`
- `EXPECTED_FREETOKEN_PIN=af71ba43206e124f5ff6419b47ee36c6e9981078`
- `BLOCKER_IDS=NONE`

Verify the live owner-execution evidence and Git history before mutation. If the repository is dirty, durable state disagrees with this handoff, the A001 evidence is missing/failed, or the pinned FreeToken checkout does not match, stop fail-closed and report the exact discrepancy.

## A001 contract that must remain true

The completed Pi integration is a proposal/translation layer only:

```text
Pi Agent Core
  -> only lac_fs_read / lac_fs_create / lac_fs_replace / lac_shell_exec
  -> PiAgentAdapter
  -> canonical EffectRequest persisted in controller state
  -> existing Dispatcher
  -> reviewed filesystem:v1 or shell:v1 adapter
  -> H001 sandbox
```

The model cannot supply approval, decision, lease, request, principal, agent, executor, or idempotency authority fields. No stock unrestricted Pi coding-agent Bash/read/edit/write route is part of the governed harness.

A002 must not weaken or bypass this contract.

## A002 implementation objective

Use the exact qualified FreeToken revision:

- Repository: `FlashML-org/FreeToken`
- Commit: `af71ba43206e124f5ff6419b47ee36c6e9981078`
- Qualified version: `0.1.2`
- License: Apache-2.0
- Qualified local checkout: `${HOME}/.cache/local-agent-controller/phase0/upstream/freetoken`

Implement the minimum model-runtime integration required to let LAC/Pi call FreeToken as an inference endpoint while preserving runtime independence.

Required boundary:

```text
Pi / AgentAdapter
    |
    v
ModelProvider abstraction
    |
    v
FreeToken local inference endpoint

NO authority edge from FreeToken to:
- policy decisions
- approvals
- execution leases
- Dispatcher
- effect adapters
- host credentials
```

Prefer a thin adapter over forking or modifying FreeToken. Inspect the pinned source first and reuse its documented/native endpoint or Python API if it satisfies the boundary. Do not invent a second authority path.

## Deterministic validation minimum

Before packaging, prove at least:

1. exact FreeToken pin and expected interface are verified fail-closed;
2. request translation into the runtime is deterministic;
3. response translation back to the model/agent layer is deterministic;
4. unavailable runtime fails closed;
5. malformed runtime response fails closed;
6. timeout/cancellation behavior is bounded and tested where the selected interface permits it;
7. FreeToken cannot approve, lease, dispatch, or directly invoke any LAC effect adapter;
8. no service credential is placed in model-visible request/context by the adapter;
9. A001 governed Pi tool-surface tests remain green;
10. `scripts/test-h004` remains green;
11. `scripts/test-h003` remains green;
12. `scripts/test-h002` remains green;
13. `scripts/test-h001` remains green;
14. Phase 1 unit/integration/acceptance regression remains green;
15. new A002 tests are green;
16. no full Phase 3 end-to-end run is started;
17. Git is clean after successful owner workflow.

## Session lifecycle

1. Verify predecessor state and evidence.
2. Inspect the pinned FreeToken source/interface.
3. Implement only A002.
4. Run deterministic A002 tests.
5. Correct any A002 defects found in this session.
6. Run the applicable full regression.
7. Build **one** owner-executable package.
8. **STOP** at `OWNER_EXECUTION_REQUIRED`.

Do not ask the owner to create files manually. The owner package must be self-contained and must:

- fail closed on unexpected Git/state/task/pin conditions;
- verify its own payload hashes;
- install only the tested A002 changes;
- run deterministic verification and regressions;
- record durable A002 execution evidence;
- advance durable state to the next task only after success;
- install a fresh root `NEXT_SESSION_PROMPT.md` for the successor session;
- print explicit PASS/FAIL and resulting Git commits.

## Required final status fields

End the session with these exact labels:

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-A002`
- `A001_IMPLEMENTATION_GIT_COMMIT=93f72ded7b96801d0e619a5aa702f9ce0f87b522`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`

On successful preparation, `STOP_GATE=OWNER_EXECUTION_REQUIRED` and the next safe action is exactly one Bash command that verifies and runs the package. Do not continue into later scope in the same session.
