# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / A004 OWNER BASELINE UAT

`SESSION_SEGMENT=LAC-A004-UAT`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns the **owner validation checkpoint only**. Do not begin Gmail, Calendar, or Chief of Staff implementation.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read `qualification/evidence/a004_owner_execution.json`, `docs/A004_OWNER_BASELINE_UAT.md`, and only the installed A004 files needed to verify the handoff.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer / LAC-A004`
- `PREDECESSOR_RESULT=A004_IMPLEMENTED_OWNER_UAT_REQUIRED`
- `PREDECESSOR_IMPLEMENTATION_GIT_COMMIT=94c7db928b3848069d2a7c432316db0d88477871`
- `A004_START_GIT_COMMIT=cca4ef5478b90e270ec717e740b3041230176036`
- `REVIEWED_PHASE3_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/a004_owner_execution.json`
- `BLOCKER_IDS=NONE`
- `EXPECTED_PHASE=PHASE_3_5_BASELINE_USER_VALIDATION`
- `EXPECTED_ACTIVE_TASK=LAC-A004-UAT`
- `EXPECTED_NEXT_TASK_ON_OWNER_PASS=LAC-B001`

The accepted Phase 3 review remains preserved. A004 is an additive usability layer over the accepted A003 path.

## Required lifecycle

1. Perform bounded predecessor verification: confirm the A004 owner execution evidence is PASS, the installed Git/state/task/prompt are mutually consistent, and the A004 implementation commit exists in current history.
2. Guide the owner through `docs/A004_OWNER_BASELINE_UAT.md`. The owner runs `scripts/lac-baseline`; do not infer usability acceptance from deterministic package tests alone.
3. Evaluate actual owner observations against `tasks/ACTIVE_TASK.md`.
4. If any concrete A004 defect is observed, classify it precisely, keep `LAC-B001` deferred, and prepare only an A004 remediation handoff/package as needed.
5. If and only if the owner explicitly accepts A004 UAT, create one minimal owner-executable transition package that advances durable state to `LAC-B001`, installs a populated B001 successor prompt, and performs no B001 implementation.
6. Stop after the transition package at `OWNER_EXECUTION_REQUIRED`. A fresh session owns B001 after that package succeeds.

## UAT entrypoint

From the project root the owner uses:

```bash
scripts/lac-baseline
```

Do not ask the owner to edit project source, manually set `CUDA_HOME`, manually launch FreeToken, or assemble infrastructure commands.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-A004-UAT`
- `PREDECESSOR_RESULT=A004_IMPLEMENTED_OWNER_UAT_REQUIRED`
- `PREDECESSOR_IMPLEMENTATION_GIT_COMMIT=94c7db928b3848069d2a7c432316db0d88477871`
- `WHAT_WAS_VERIFIED=`
- `OWNER_UAT_RESULT=`
- `WHAT_REMAINS_IN_CURRENT_CHECKPOINT=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
