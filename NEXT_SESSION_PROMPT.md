# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI006 FINAL OWNER UAT AFTER RC.8 DANGEROUS-BYPASS STABILIZATION

## Role and controlling rule
You are the successor Lead Implementation Engineer for the user-owned Local Agent Controller (LAC).
AI proposes. Deterministic software determines authorization and effects.
Continue LAC-PI006 only; do not start Phase 7 review until final owner-UAT evidence is recorded.

## Mandatory reads
Read PROJECT_STATE.json, tasks/ACTIVE_TASK.md, docs/ARCHITECTURE.md, UPSTREAM_LOCK.json, docs/NEXT_SESSION_PROMPT_TEMPLATE.md, docs/PI_V1_GOVERNED_PROFILE.md, docs/V1_PRODUCTIZATION.md, qualification/evidence/pi006_interactive_idle_backlog_stabilization_owner_execution.json, and qualification/evidence/pi006_dangerous_bypass_source_cli_stabilization_owner_execution.json.

## Exact handoff facts
- PREDECESSOR_RESULT=PI006_DANGEROUS_BYPASS_SOURCE_CLI_STABILIZATION_PASS
- PREDECESSOR_IMPLEMENTATION_COMMIT=430eafc4fc2bf9ea578390efbbcbfa8edf3bc7af
- HANDOFF_STATE_COMMIT=430eafc4fc2bf9ea578390efbbcbfa8edf3bc7af
- CURRENT_CANDIDATE=1.0.0-rc.8
- LAST_ACCEPTED_RELEASE=1.0.0-rc.1
- BLOCKER_IDS=NONE
- EXPECTED_NEXT_TASK=LAC-PI006
- OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi006_dangerous_bypass_source_cli_stabilization_owner_execution.json
- PACKAGE_ID=LAC_PI006_DANGEROUS_BYPASS_SOURCE_CLI_STABILIZATION_v0.1.1
- PACKAGE_SHA256=3b8bfe8b089cbe1ec34e5227ac9aedaedb66baef17ac00cb8de8bc9cd5daa9f1
- PI006_DISTRIBUTION_SHA256=74945c5813414b38fc405e684e42c9bd612d7b9733bfb8dfda7c95ff7ee6d756

## What rc.8 fixes
Owner UAT exposed PI006-UAT-DANGEROUS-BYPASS-004. The explicit dangerous bypass still targeted packages/coding-agent/dist/bundle/cli.js. The accepted pinned Pi checkout uses packages/coding-agent/src/cli.ts through checkout-local tsx. rc.8 verifies the accepted pin, checks coding-agent version 0.85.1, requires source/config/package metadata and a checkout-local tsx runtime, and then launches the source CLI. The default Pi path remains governed.

## Owner UAT already established
The preserved isolated UAT pointer is ~/.local/state/local-agent-controller/qualification/pi006-owner-uat-current. Owner UAT has already passed native governed launch, restart/no-auto-dispatch, exact approval, durable idempotency, emergency pause override and persistence, post-resume create, filesystem read, filesystem replace, and shell exec. The live four-tool receipt IDs are recorded in the rc.8 stabilization evidence. RC.8 installation qualification also ran the real explicit dangerous-bypass --help path successfully.

## Exact next work
Run one read-only durable verifier over the preserved UAT controller database/workspace to confirm emergency pause is false, pi006-emergency.txt contains exactly PI006_REPLACE_PASS, the recorded four live receipt IDs exist and remain SUCCEEDED, and the earlier exact-approval restart receipt remains unique/consumed. If that passes, record final PI006 owner-UAT evidence and move the rc.8 candidate to one fresh independent Phase 7 review. Do not add features or broaden policy.

## Stop rule
Finish PI006 owner UAT evidence only, then stop for fresh independent Phase 7 review.
