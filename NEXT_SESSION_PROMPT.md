# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI005 NATIVE GOVERNED PI TUI

## 1. Role and controlling rule

You are the successor **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This is an `IMPLEMENTATION_SEGMENT`. Execute `LAC-PI005` only.

## 2. Mandatory reads
Read first, in order: `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `tasks/ACTIVE_TASK.md`, `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`. Then read `decisions/ADR-010_DEFAULT_GOVERNED_PI_ENTRYPOINT.md`, `docs/DEFAULT_GOVERNED_PI_ROADMAP.md`, `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/V1_PRODUCTIZATION.md`, `qualification/evidence/pi004_owner_execution.json`, and only the Pi/TUI/productization files needed for PI005.

## 3. Exact handoff facts
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=OWNER_EXECUTION_PASS`
- `PREINSTALL_GIT_COMMIT=d2ab7fe98b21e3ee27a70d8568d7d491219a77b4`
- `PREDECESSOR_IMPLEMENTATION_COMMIT=2b26291ba0ca0d2f61c07a47e9c4317396be6420`
- `HANDOFF_STATE_COMMIT=df281520a430c95b9106c111102131d69526a280`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi004_owner_execution.json`
- `PACKAGE_ID=LAC_PI004_DEFAULT_GOVERNED_PI_ENTRYPOINT_v0.1.5`
- `PACKAGE_SHA256=1d16a3b4a4994a2b6a76bab38ec0a29d9039fb6e5dca769f90c7bb483acb1728`
- `PI004_DISTRIBUTION_SHA256=6d42e53d46d3be8b844dc5d9da1870728653a8ce9a36cbfd9f70a3db45757b4c`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `CURRENT_CANDIDATE=1.0.0-rc.2`
- `BLOCKER_IDS=NONE`
- `EXPECTED_NEXT_TASK=LAC-PI005`
- `SESSION_SEGMENT=LAC-PI005`

Live HEAD is expected to be exactly one evidence/prompt commit after `HANDOFF_STATE_COMMIT`; that delta must contain only `NEXT_SESSION_PROMPT.md` and `qualification/evidence/pi004_owner_execution.json`. The prior Phase 6 PASS remains accepted; PI004 is a forward owner-authorized roadmap amendment.

## 4. PI005 objective
Use Pi's actual pinned 0.85.1 TUI/session/SDK surfaces for the governed frontend. Do not grant stock Pi ambient Bash/read/write/edit authority merely to obtain the TUI. Resource/package/extension loading is security-sensitive because extensions execute inside the Pi process; qualify it so no extension/resource path can bypass LAC's sandbox/effect boundary. Preserve PI004's default `pi` governance and explicit top-level `--dangerously-bypass-lac` escape hatch.

## 5. Stop rule
Complete PI005 only, run deterministic and retained gates, release-qualify one owner package if mutation is required, then stop for owner execution. Do not begin PI006 in the same session.
