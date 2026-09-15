# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / A004 INTERACTIVE BASELINE HARNESS

`SESSION_SEGMENT=LAC-A004`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. Act as the **Lead Implementation Engineer** for exactly `LAC-A004`. Do not begin Gmail, Calendar, or Chief of Staff implementation in this session.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then inspect the controlling specification sections needed for A004, especially §§17, 19, 20, 33, 38, 49, 50, 54, and 59; `docs/PHASE3_A003_QUALIFICATION.md`; `docs/MODEL_PROVIDER_CONTRACT.md`; the accepted A003 sandbox/model/provider/controller bridge; and A003 runtime/owner evidence.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Owner-approved sequence amendment after accepted Phase 3 review`
- `PREDECESSOR_RESULT=PHASE3_ACCEPTED_A004_INSERTED_BEFORE_B001`
- `REVIEWED_PHASE3_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `PHASE3_TO_PHASE4_HANDOFF_GIT_COMMIT=39a0d5eefa71c7112dc7ae62225d32c1393b0c00`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/a003_owner_execution.json`
- `EXPECTED_PHASE=PHASE_3_5_BASELINE_USER_VALIDATION`
- `EXPECTED_ACTIVE_TASK=LAC-A004`
- `EXPECTED_NEXT_TASK=LAC-A004-UAT`
- `DEFERRED_TASK=LAC-B001`

The accepted Phase 3 implementation/review is not reopened by this owner-requested usability checkpoint. Before implementing A004, inspect the complete `39a0d5eefa71c7112dc7ae62225d32c1393b0c00`-to-live-`HEAD` delta. It must contain only the sequence-amendment files installed by the owner package: `PROJECT_STATE.json`, `tasks/ACTIVE_TASK.md`, `NEXT_SESSION_PROMPT.md`, and `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`. Any unrelated implementation drift is a blocker.

## A004 objective

Give the owner a practical terminal conversation with the baseline platform **before** adding Chief of Staff capabilities:

`owner -> interactive terminal -> H001-sandboxed Pi -> LAC ModelProvider -> pinned FreeToken/gpt-oss-20b -> governed tool proposal -> LAC controller/Dispatcher -> H002/H003 -> H001 -> receipt`

This is a thin usability/access layer over the accepted Phase 3 path, not a redesign.

## Binding implementation requirements

- Reuse the exact accepted Pi, FreeToken, model revision, Bubblewrap backend, PiAgentAdapter, Dispatcher, filesystem/shell adapters, receipts, policy, and sandbox boundary.
- Expose exactly `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, and `lac_shell_exec` to Pi.
- Provide multi-turn terminal interaction and concise observable governed-tool/receipt events without exposing hidden reasoning.
- Use a dedicated bounded baseline-test workspace; do not mount the repository, home directory, controller state/database, or credentials into Pi.
- Provide a reproducible FreeToken launcher. The owner's manual post-Phase-3 launch reached model initialization but failed during JIT build with `RuntimeError: Could not find CUDA installation. Please set CUDA_HOME environment variable.` A004 must discover the actual `nvcc` location, derive and validate the CUDA toolkit root when appropriate, establish only the environment required by the runtime, and fail closed with a useful diagnostic if qualification prerequisites are missing. Do not hard-code an unverified CUDA path.
- Keep FreeToken loopback-only and inference-only.
- Cleanly manage process lifecycle so startup failure or exit does not leave orphaned runtime/agent processes.
- Add deterministic tests for all acceptance criteria in `tasks/ACTIVE_TASK.md` and preserve the full applicable regression gate.
- Produce an owner user-testing guide with a short baseline script covering normal conversation, governed workspace operations, receipt visibility, boundary-denial behavior, and shutdown/restart.

## Required lifecycle

1. Perform bounded predecessor verification only; do not redo the accepted Phase 3 review.
2. Implement A004 completely.
3. Run A004-specific tests and the full applicable regression gate.
4. Correct in-scope defects and rerun affected/full gates.
5. Produce one owner-executable package and exactly one self-contained Bash command.
6. The successful package must advance durable state to `LAC-A004-UAT` and install a populated successor prompt for owner hands-on validation.
7. Stop at `OWNER_EXECUTION_REQUIRED`. Do not begin B001.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-A004`
- `PREDECESSOR_RESULT=PHASE3_ACCEPTED_A004_INSERTED_BEFORE_B001`
- `REVIEWED_PHASE3_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_CHECKPOINT=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
