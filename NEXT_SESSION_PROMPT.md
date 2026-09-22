# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI006 OWNER UAT AFTER RC.7 INTERACTIVE-IDLE STABILIZATION

## 1. Role and controlling rule
You are the successor **Lead Implementation Engineer** for the user-owned **Local Agent Controller (LAC)**.

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
This remains an `IMPLEMENTATION_SEGMENT`. Continue the remaining owner-UAT portion of `LAC-PI006`; do not start Phase 7 review until owner UAT passes.

## 2. Mandatory reads
Read first, in order: `PROJECT_STATE.json`, `tasks/ACTIVE_TASK.md`, `docs/ARCHITECTURE.md`, `UPSTREAM_LOCK.json`, `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`. Then read `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/V1_PRODUCTIZATION.md`, `qualification/evidence/pi006_admin_socket_collision_owner_execution.json`, `qualification/evidence/pi006_interactive_idle_backlog_stabilization_owner_execution.json`, and only native-Pi/UAT files needed for PI006.

## 3. Exact handoff facts
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PI006_INTERACTIVE_IDLE_BACKLOG_STABILIZATION_PASS`
- `PREDECESSOR_IMPLEMENTATION_COMMIT=444f5b8594d5ecbd2878f3cde70b1ed0233af848`
- `HANDOFF_STATE_COMMIT=444f5b8594d5ecbd2878f3cde70b1ed0233af848`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi006_interactive_idle_backlog_stabilization_owner_execution.json`
- `PACKAGE_ID=LAC_PI006_INTERACTIVE_IDLE_AND_PERMISSION_BACKLOG_STABILIZATION_v0.1.3`
- `PACKAGE_SHA256=cda8bd4e2914e061fcd6942941946eda6b505bea07ee0c7381357e3caa689cec`
- `PI006_DISTRIBUTION_SHA256=250d6aab4d1c442aef1a91a9892680b086d01708728e6ca5c997ae3583f1447b`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `CURRENT_CANDIDATE=1.0.0-rc.7`
- `BLOCKER_IDS=NONE`
- `EXPECTED_NEXT_TASK=LAC-PI006`
- `SESSION_SEGMENT=LAC-PI006`

Live HEAD is expected to be exactly one evidence/handoff commit after `HANDOFF_STATE_COMMIT`; that delta should contain only handoff/evidence state. Prior Phase 6 PASS remains accepted.

## 4. What rc.7 fixes
Owner UAT exposed `PI006-UAT-INTERACTIVE-IDLE-003`. `scripts/pi_native_tui_host.py` used `receive_timeout = 45.0 if probe else 3600.0`, so a healthy interactive Pi could be terminated only because no broker RPC arrived for one hour. rc.7 makes interactive `_recv` wait without an idle deadline while retaining 250 ms child-liveness polling and the 45-second probe timeout.

Do **not** change the D001 continuation TTL: it remains 3,600 seconds and expired continuation requests remain non-authorizing/non-resumable. The informational P002/P006 pending-permission queue has no TTL; regression coverage now proves it remains owner-reviewable after continuation expiry and that a later policy decision applies only to future fresh requests.

## 5. Owner-UAT evidence already established
Before rc.7 stabilization, owner UAT established:
- fresh-shell ordinary `pi` resolves to the LAC-managed launcher;
- native Pi 0.85.1 runs Bubblewrap/network-none with exactly `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`;
- second governed Pi fails closed on an active administrator socket without killing/removing the primary endpoint;
- restart reports one recoverable continuation and does not auto-dispatch;
- exact `REQUIRE_APPROVAL` policy and `POLICY_UPDATED` resolution do not dispatch;
- `/lac-resume` creates one fresh request; exact approval alone does not dispatch; second explicit resume succeeds;
- one durable execution/receipt exists and the one-time approval is consumed;
- repeated completed `/lac-resume` produced no visible duplicate completion toast, but durable state remained exactly-once and `/lac-continuations` remained responsive. Record this as a nonblocking TUI notification-visibility finding unless independent review says otherwise;
- emergency-pause UAT configured an exact ALLOW for `pi006-emergency.txt`, then emergency pause overrode it with `authority=DENY`, `state=DENIED`, `reason=EMERGENCY_PAUSED`, no receipt, no continuation, and no effect.

## 6. Exact next owner-UAT work
The preserved isolated UAT pointer is `~/.local/state/local-agent-controller/qualification/pi006-owner-uat-current`.

After rc.7 installation, start ordinary governed `pi` against that same workspace/state/trace. First verify:
- `lacctl --json emergency status` still reports `paused:true`;
- `pi006-emergency.txt` is absent;
- the rc.7 governed Pi remains open across ordinary inactivity (do not wait an hour manually; automated regression now covers the deadline removal).

Then complete emergency-pause UAT: resume emergency state through owner admin, verify pause state is false, issue a new narrowly authorized fresh action and prove it succeeds only after the pause is lifted. Continue the remaining multi-turn/four-tool native TUI checks and explicit top-level `pi --dangerously-bypass-lac` check. Do not broaden policy unnecessarily; use exact UAT paths/arguments.

If the remaining UAT passes without another mutation, record final PI006 owner-UAT evidence and advance to one fresh independent Phase 7 review of rc.7. If another in-scope defect appears, remediate only that defect and rerun `scripts/test-pi006` plus the retained chain.

## 7. Stop rule
Complete PI006 owner UAT and any bounded stabilization only. Then stop for fresh independent Phase 7 review.
