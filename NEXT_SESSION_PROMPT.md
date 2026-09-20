# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI006 OWNER UAT AND STABILIZATION

## 1. Role and controlling rule

You are the successor **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This is an `IMPLEMENTATION_SEGMENT`. Execute `LAC-PI006` only.

## 2. Mandatory reads
Read first, in order: `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `tasks/ACTIVE_TASK.md`, `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`. Then read `decisions/ADR-010_DEFAULT_GOVERNED_PI_ENTRYPOINT.md`, `docs/DEFAULT_GOVERNED_PI_ROADMAP.md`, `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/V1_PRODUCTIZATION.md`, `qualification/evidence/pi005_owner_execution.json`, and only the native-Pi/productization/UAT files needed for PI006.

## 3. Exact handoff facts
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREINSTALL_GIT_COMMIT=d2d67276c17c659fcb8462e2d1fc63405a00fd2e`
- `PREDECESSOR_IMPLEMENTATION_COMMIT=35dde36cbb63227cdea5ea77552aa1a6f2bcf450`
- `HANDOFF_STATE_COMMIT=a27c0e335d1293e0b6c9a2cc7a48b36d0da526bd`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi005_owner_execution.json`
- `PACKAGE_ID=LAC_PI005_NATIVE_GOVERNED_PI_TUI_v0.1.12`
- `PACKAGE_SHA256=5e315699569fe49a11ff55f9ab58be59ad5f93b6894e26b8d69012315acd0c0f`
- `PI005_DISTRIBUTION_SHA256=094bec442836a0cb1ea09738863554d3ca9a86cdc7defaa816c66e9893ab94f8`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `CURRENT_CANDIDATE=1.0.0-rc.3`
- `BLOCKER_IDS=NONE`
- `EXPECTED_NEXT_TASK=LAC-PI006`
- `SESSION_SEGMENT=LAC-PI006`

Live HEAD is expected to be exactly one evidence/prompt commit after `HANDOFF_STATE_COMMIT`; that delta must contain only `NEXT_SESSION_PROMPT.md` and `qualification/evidence/pi005_owner_execution.json`. The prior Phase 6 PASS remains accepted; PI004-PI006 are the owner-authorized forward Phase 7 roadmap.

## 4. PI006 objective
Run the owner UAT and bounded stabilization defined by `tasks/ACTIVE_TASK.md`. Validate the ordinary installed `pi` command against the real native Pi TUI, permission/approval/emergency/continuation/restart behavior, and explicit dangerous-bypass UX. Do not broaden the four-tool model effect surface or re-enable arbitrary Pi resources/extensions. If UAT exposes an in-scope defect, remediate only that defect and re-run PI005 plus retained gates. If UAT passes without mutation, record evidence and advance to one fresh independent Phase 7 review.

## 5. Stop rule
Complete PI006 only. After owner UAT and any bounded stabilization, stop for the fresh independent Phase 7 review. Do not begin any post-Phase-7 roadmap work in the same session.
