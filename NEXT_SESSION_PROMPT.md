# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI006 OWNER UAT AFTER RC.6 ADMIN-SOCKET STABILIZATION

## 1. Role and controlling rule
You are the successor **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This is an `IMPLEMENTATION_SEGMENT`. Execute the remaining owner-UAT portion of `LAC-PI006` only.

## 2. Mandatory reads
Read first, in order: `PROJECT_STATE.json`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `tasks/ACTIVE_TASK.md`, `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`. Then read `decisions/ADR-010_DEFAULT_GOVERNED_PI_ENTRYPOINT.md`, `docs/DEFAULT_GOVERNED_PI_ROADMAP.md`, `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/V1_PRODUCTIZATION.md`, `qualification/evidence/pi006_stabilization_owner_execution.json`, `qualification/evidence/pi006_admin_wrapper_forwarding_owner_execution.json`, `qualification/evidence/pi006_admin_socket_collision_owner_execution.json`, and only native-Pi/UAT files needed for PI006.

## 3. Exact handoff facts
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PI006_ADMIN_SOCKET_COLLISION_STABILIZATION_PASS`
- `PREINSTALL_GIT_COMMIT=fd315d23bb47a4ebfa0182a9864c3db49d19d2f6`
- `PREDECESSOR_IMPLEMENTATION_COMMIT=78cc2d2b005b97e67f8e7a42485c53cf245a9066`
- `HANDOFF_STATE_COMMIT=78cc2d2b005b97e67f8e7a42485c53cf245a9066`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi006_admin_socket_collision_owner_execution.json`
- `PACKAGE_ID=LAC_PI006_ADMIN_SOCKET_OWNERSHIP_STABILIZATION_v0.1.2`
- `PI006_DISTRIBUTION_SHA256=7e14347dc236ee0f64efe378bd32bfed31fecb86612a08777a53f02a157557f7`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `CURRENT_CANDIDATE=1.0.0-rc.6`
- `BLOCKER_IDS=NONE`
- `EXPECTED_NEXT_TASK=LAC-PI006`
- `SESSION_SEGMENT=LAC-PI006`

Live HEAD is expected to be exactly one evidence/prompt commit after `HANDOFF_STATE_COMMIT`; that delta must contain only `NEXT_SESSION_PROMPT.md` and `qualification/evidence/pi006_admin_socket_collision_owner_execution.json`. Prior Phase 6 PASS remains accepted.

## 4. UAT state to resume
Owner UAT already proved fresh-shell default governance, native Pi 0.85.1 inside Bubblewrap/network-none, terminal DENY of the unconfigured `lac_fs_create`, workflow suspension before model continuation, and absence of `pi006-restart.txt`.

Preserved identities:
- pending: `pending:824b435566922f0bdbe552063dfe9d2429cf8b9dabde0968e8b70c28da5b3b4a`
- continuation: `continuation:pi-v1:ee7abacde590ed7a0d04bba385c5ca95f509c12ae589689b65f0a79afd6e5479`

The isolated UAT pointer is `~/.local/state/local-agent-controller/qualification/pi006-owner-uat-current`.

RC.5 fixed `PI006-UAT-ADMIN-WRAPPER-001`. Owner UAT then exposed `PI006-UAT-ADMIN-SOCKET-002`: a second governed Pi launch correctly failed closed on the active owner administrator socket, but the contending server instance could unlink the active endpoint during cleanup and the existing server could terminate when the liveness probe disconnected before request framing. rc.6 binds cleanup to the exact socket device/inode acquired by the server and tolerates expected peer disconnect errors. It does not authorize or resume the denied request.

First verify the UAT pointer/state remains and `pi006-restart.txt` is absent. Restart ordinary governed `pi` against the same isolated workspace/state/trace. Verify startup reports the recoverable continuation and does not dispatch. Use `/lac-continuations`. Then use the installed owner command surface to configure/resolve policy and explicitly recover with `/lac-resume <continuation_id>`. Continue exact approval, emergency pause, receipt/idempotency, multi-turn/four-tool, and top-level `pi --dangerously-bypass-lac` UAT.

Also perform one bounded concurrency regression in owner UAT: while the primary governed Pi is open and its admin endpoint is healthy, a second top-level `pi` launch must fail closed without removing the primary endpoint or terminating its admin service; `lacctl --json pending list` must still work against the primary session afterward.

Pi built-in `/resume` remains reserved for Pi session navigation. Do not broaden the four-tool effect surface or enable arbitrary Pi resources/extensions.

If UAT passes without another mutation, record owner UAT evidence and advance to one fresh independent Phase 7 review. If another in-scope defect appears, remediate only that defect and rerun `scripts/test-pi006`.

## 5. Stop rule
Complete PI006 only. After owner UAT and bounded stabilization, stop for fresh independent Phase 7 review.
