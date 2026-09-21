# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI006 OWNER UAT AFTER RC.4 STABILIZATION

## 1. Role and controlling rule

You are the successor **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This is an `IMPLEMENTATION_SEGMENT`. Execute the remaining owner-UAT portion of `LAC-PI006` only.

## 2. Mandatory reads
Read first, in order: `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `tasks/ACTIVE_TASK.md`, `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`. Then read `decisions/ADR-010_DEFAULT_GOVERNED_PI_ENTRYPOINT.md`, `docs/DEFAULT_GOVERNED_PI_ROADMAP.md`, `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/V1_PRODUCTIZATION.md`, `qualification/evidence/pi006_stabilization_owner_execution.json`, and only the native-Pi/UAT files needed for PI006.

## 3. Exact handoff facts
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=STABILIZATION_OWNER_EXECUTION_PASS`
- `PREINSTALL_GIT_COMMIT=f403962d5ef0dc239cd632efbdad1ca0f9a92a65`
- `PREDECESSOR_IMPLEMENTATION_COMMIT=81ea310e2e1bc43b63323c182ac4ce53917d5bad`
- `HANDOFF_STATE_COMMIT=8c7726d6b4f912825c1050bf420e61769303c2d1`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi006_stabilization_owner_execution.json`
- `PACKAGE_ID=LAC_PI006_NATIVE_RESTART_RECOVERY_STABILIZATION_v0.1.0`
- `PACKAGE_SHA256=13f3b787ec2a15890bd312fd3215cced00725c84f385add4f22d6dcb085c6843`
- `PI006_DISTRIBUTION_SHA256=da28ce1c27d8d69591193dd7374c9f61f450f6e5323910924ccbd85850a75f5d`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `CURRENT_CANDIDATE=1.0.0-rc.4`
- `BLOCKER_IDS=NONE`
- `EXPECTED_NEXT_TASK=LAC-PI006`
- `SESSION_SEGMENT=LAC-PI006`

Live HEAD is expected to be exactly one evidence/prompt commit after `HANDOFF_STATE_COMMIT`; that delta must contain only `NEXT_SESSION_PROMPT.md` and `qualification/evidence/pi006_stabilization_owner_execution.json`. The prior Phase 6 PASS remains accepted.

## 4. Remaining PI006 objective
Run owner UAT against ordinary installed `pi` on rc.4. Validate real native Pi TUI multi-turn use; permission discovery/configuration; exact approval; emergency pause; receipt/idempotency; restart with no auto-dispatch; owner-visible `/lac-continuations`; explicit `/lac-resume <continuation_id>` recovery; and top-level `pi --dangerously-bypass-lac` UX. Pi's built-in `/resume` remains reserved for Pi session navigation. Do not broaden the four-tool model effect surface or enable arbitrary Pi resources/extensions.

If UAT passes without another mutation, record owner UAT evidence and advance to one fresh independent Phase 7 review. If UAT exposes another in-scope defect, remediate only that defect and rerun `scripts/test-pi006`.

## 5. Stop rule
Complete PI006 only. After owner UAT and any bounded stabilization, stop for the fresh independent Phase 7 review. Do not begin post-Phase-7 work in the same session.
