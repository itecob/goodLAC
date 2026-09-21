# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI006 STABILIZATION RECOVERY

## 1. Role and controlling rule
You are the successor **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This is an `IMPLEMENTATION_SEGMENT`. Continue `LAC-PI006` only.

## 2. Mandatory reads
Read first, in order: `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `tasks/ACTIVE_TASK.md`, `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`. Then read `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/V1_PRODUCTIZATION.md`, and the PI006 stabilization diff/tests.

## 3. Recovery facts
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=STABILIZATION_IMPLEMENTED_AWAITING_OWNER_INSTALL_OR_EVIDENCE`
- `PREINSTALL_GIT_COMMIT=f403962d5ef0dc239cd632efbdad1ca0f9a92a65`
- `PREDECESSOR_IMPLEMENTATION_COMMIT=81ea310e2e1bc43b63323c182ac4ce53917d5bad`
- `EXPECTED_NEXT_TASK=LAC-PI006`
- `SESSION_SEGMENT=LAC-PI006`
- `CURRENT_CANDIDATE=1.0.0-rc.4`

The source stabilization restores native-TUI D001 restart recovery with `/lac-continuations` and `/lac-resume`, leaving Pi's built-in `/resume` untouched and preserving the exact four model-facing tools. Determine whether rc.4 installation/evidence completed. If not, remediate/complete only that package lifecycle. If it did, proceed directly to owner UAT.

## 4. Stop rule
Complete PI006 only. Do not begin the independent Phase 7 review in this implementation session.
