# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / A004 OWNER-UAT REMEDIATION

`SESSION_SEGMENT=LAC-A004-REMEDIATION`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** remediation of the two A004 owner-UAT blockers recorded in `qualification/evidence/a004_owner_uat_observation.json`. Do not begin Gmail, Calendar, or Chief of Staff implementation.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `qualification/evidence/a004_owner_execution.json`
- `qualification/evidence/a004_owner_uat_observation.json`
- `docs/A004_OWNER_BASELINE_UAT.md`
- `scripts/a004_terminal.py`
- `scripts/a004_agent_worker.mjs`
- `packages/adapters/pi/governed_pi.mjs`
- only the additional A004/H003 files and tests needed to remediate the two findings.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Owner Validation Checkpoint / LAC-A004-UAT`
- `PREDECESSOR_RESULT=BLOCKED_A004_UAT_DEFECTS`
- `PREDECESSOR_IMPLEMENTATION_GIT_COMMIT=94c7db928b3848069d2a7c432316db0d88477871`
- `HANDOFF_BASE_GIT_COMMIT=fe66c7c8537c10287ecced2d2e899244d6a157ca`
- `REVIEWED_PHASE3_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/a004_owner_execution.json`
- `OWNER_UAT_OBSERVATION=qualification/evidence/a004_owner_uat_observation.json`
- `BLOCKER_IDS=A004-UAT-B001,A004-UAT-B002`
- `EXPECTED_PHASE=PHASE_3_5_BASELINE_USER_VALIDATION`
- `EXPECTED_ACTIVE_TASK=LAC-A004-REMEDIATION`
- `EXPECTED_NEXT_TASK_ON_REMEDIATION_PASS=LAC-A004-UAT`
- `DEFERRED_TASK=LAC-B001`

The accepted Phase 3 review remains preserved. A004 is an additive usability layer over the accepted A003 path.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm the UAT observation is durably recorded, the two blocker IDs match `tasks/ACTIVE_TASK.md`, current state/prompt/task are mutually consistent, and the original A004 implementation commit remains in history.
2. Remediate **only** `A004-UAT-B001` and `A004-UAT-B002`.
3. Add the smallest deterministic tests that reproduce/close each defect.
4. Run affected tests and the full applicable `scripts/test-a004` regression gate. Correct in-scope failures before handoff.
5. Do not add host hardware diagnostics, new tools, new executables, new authority semantics, Phase 4 features, or unrelated UX work.
6. Create one owner-executable remediation package. On success it must:
   - install the corrected A004 files/tests;
   - record deterministic evidence;
   - set durable state back to `LAC-A004-UAT`;
   - install the owner-UAT task and a populated fresh UAT successor `NEXT_SESSION_PROMPT.md`;
   - leave `LAC-B001` deferred.
7. Stop at `OWNER_EXECUTION_REQUIRED`. A fresh session owns the repeated owner UAT after the package succeeds.

## Remediation requirements

### A004-UAT-B001

Ordinary terminal arrow-key editing must not inject raw control sequences into the model prompt and crash the session. Use the smallest Linux-terminal-appropriate line-editing/input hardening. Residual disallowed control characters must fail safely without killing the interactive session.

### A004-UAT-B002

The model-facing shell contract must unambiguously state that `argv` contains only arguments **after** the executable and excludes `argv[0]`. The baseline workspace listing request must resolve to:

- `executable=/usr/bin/ls`
- `argv=[]`
- `cwd=.`
- empty environment unless explicitly required

Do not change the accepted H003 shell authority surface merely to accommodate the model.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-A004-REMEDIATION`
- `PREDECESSOR_RESULT=BLOCKED_A004_UAT_DEFECTS`
- `BLOCKER_IDS=A004-UAT-B001,A004-UAT-B002`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_CHECKPOINT=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
