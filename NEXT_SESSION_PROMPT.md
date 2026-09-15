# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / A004 OWNER-UAT REVALIDATION

`SESSION_SEGMENT=LAC-A004-UAT`
`MODE=OWNER_VALIDATION_CHECKPOINT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This session owns **only** repeated owner hands-on validation of A004 after remediation of `A004-UAT-B001` and `A004-UAT-B002`. Do not begin Gmail, Calendar, Chief of Staff, or `LAC-B001` implementation.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- `qualification/evidence/a004_owner_execution.json`
- `qualification/evidence/a004_owner_uat_observation.json`
- `qualification/evidence/a004_remediation_execution.json`
- `docs/A004_OWNER_BASELINE_UAT.md`
- only the A004 files/evidence needed to verify the remediation installation.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer / LAC-A004-REMEDIATION`
- `PREDECESSOR_RESULT=REMEDIATION_PACKAGE_PASS`
- `PREDECESSOR_START_GIT_COMMIT=44c20232361ca6d4b923d7e91c7736e91e3950f7`
- `ORIGINAL_A004_IMPLEMENTATION_GIT_COMMIT=94c7db928b3848069d2a7c432316db0d88477871`
- `REVIEWED_PHASE3_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/a004_owner_execution.json`
- `OWNER_UAT_OBSERVATION=qualification/evidence/a004_owner_uat_observation.json`
- `REMEDIATION_EXECUTION_EVIDENCE=qualification/evidence/a004_remediation_execution.json`
- `REMEDIATED_BLOCKER_IDS=A004-UAT-B001,A004-UAT-B002`
- `EXPECTED_PHASE=PHASE_3_5_BASELINE_USER_VALIDATION`
- `EXPECTED_ACTIVE_TASK=LAC-A004-UAT`
- `DEFERRED_TASK=LAC-B001`

The accepted Phase 3 review remains preserved. A004 remains an additive owner-usability checkpoint over the accepted A003 path.

## Required lifecycle

1. Perform bounded predecessor verification. Confirm the remediation evidence is PASS, durable state/task/prompt are mutually consistent, Git contains both the original A004 implementation and the remediation implementation, and `LAC-B001` remains deferred.
2. Do **not** claim owner-UAT success from deterministic tests alone. The owner must perform the interactive validation.
3. Have the owner run `scripts/lac-baseline` and complete `docs/A004_OWNER_BASELINE_UAT.md`.
4. Explicitly re-test:
   - ordinary left/right arrow-key line editing;
   - safe rejection of any residual disallowed terminal control input without killing the session;
   - the workspace-listing request using `/usr/bin/ls`, which must produce `executable=/usr/bin/ls`, `argv=[]`, `cwd=.`, empty environment, and the actual workspace listing.
5. Also repeat the existing create/read/replace, boundary denial, executable denial, post-denial status, clean shutdown, restart, and governed-read checks.
6. If and only if the owner's hands-on UAT passes, record durable PASS evidence and produce one owner-executable handoff package activating fresh `LAC-B001`.
7. If the owner observes any concrete defect, record only those blocker(s), keep `LAC-B001` deferred, and produce one blocked-UAT handoff package for a fresh bounded remediation session.
8. Stop at `OWNER_EXECUTION_REQUIRED` for the resulting workflow package. Do not implement the successor task in this session.

## Scope discipline

Do not add Gmail, Calendar, Chief of Staff, production credentials, host diagnostics, new tools, new executables, new authority semantics, web UI, voice UI, memory architecture, or unrelated UX work.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-A004-UAT`
- `PREDECESSOR_RESULT=REMEDIATION_PACKAGE_PASS`
- `REMEDIATED_BLOCKER_IDS=A004-UAT-B001,A004-UAT-B002`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_CHECKPOINT=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
