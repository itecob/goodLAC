# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 6 V1 PRODUCTIZATION INDEPENDENT REVIEW

## 1. Role and controlling rule

You are the successor **Fresh Independent Reviewer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This is `PHASE_BOUNDARY_INDEPENDENT_REVIEW`. Review the exact Phase 6 candidate only. Do not remediate and do not begin future roadmap work.

## 2. Mandatory reads

Read first, in order:
1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read `qualification/evidence/v001_owner_execution.json`, Phase 6 and package-verification sections of the controlling specification, `docs/V1_PRODUCTIZATION.md`, `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/NATIVE_LOCAL_CONSUMER_CONTRACT.md`, `docs/CONTRACTS.md`, `scripts/test-v001`, and the V001 implementation/tests.

## 3. Exact handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREINSTALL_GIT_COMMIT=6743d4cc4b4cf5359e23ed6450c69f13bec9b0a8`
- `PREDECESSOR_IMPLEMENTATION_COMMIT=e76856cd151eefa8ae4ede7c473005eafb762e8a`
- `HANDOFF_STATE_COMMIT=1c87a8e67c8a7aad89cefd9daaa9bf8e3ea23220`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/v001_owner_execution.json`
- `PACKAGE_ID=LAC_V001_V1_PRODUCTIZATION_v0.2.0`
- `PACKAGE_SHA256=ad52ff7f221294eced884cca9a3cb87a2f4e6adb34dbfb89ab8ad922df9d4546`
- `PORTABLE_DISTRIBUTION_SHA256=a8bdbe7f894ab2ed27d2432f89cb3ce99d3a8a16665eb8a9cbec22bd43c9ff34`
- `EXPECTED_NEXT_TASK=LAC-P6-REVIEW`
- `SESSION_SEGMENT=LAC-P6-REVIEW`
- `BLOCKER_IDS=NONE`

Live `HEAD` is expected to be exactly one evidence/prompt-install commit after `HANDOFF_STATE_COMMIT`. Require that delta to contain only `NEXT_SESSION_PROMPT.md` and `qualification/evidence/v001_owner_execution.json`.

## 4. Review target

Determine whether LAC-V001 productizes the accepted Pi reference path without moving canonical authority or weakening accepted Phase 5 semantics. Verify user-level portable installation, bounded configuration, owner UX over the accepted admin API, the deliberate absence of a new persistent authority daemon, upgrade/database backup behavior, exact supported rollback/recovery, deterministic distribution construction, clean-target install, and retained security/conformance behavior.

The V001 owner package is required to have qualified the exact preinstall tree in a disposable Git worktree before live mutation, including complete `scripts/test-v001` -> `scripts/test-pi003` regressions and explicit forced outer-package rollback.

## 5. Review rules

Inspect implementation and deterministic evidence rather than trusting predecessor claims. Use local synthetic fixtures only; no production credentials or consequential external effects. Return exactly `PASS` or `BLOCKED`. A finding blocks only for a concrete binding requirement/invariant/security/package/data-integrity failure. Record optional improvements as NONBLOCKING. Do not remediate.

If PASS, prepare the durable pass handoff needed to record the independently accepted v1 release candidate and close the active v1 build roadmap. If BLOCKED, identify exact blocker IDs and prepare a fresh remediation-session handoff limited to those blockers.
