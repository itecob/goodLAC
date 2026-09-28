# NEXT SESSION PROMPT — goodLAC / POST-V1 R5-R001 MULTI-PI ADMIN CONTROL PLANE

## 1. Role and controlling rule

You are the Lead Remediation Engineer for the owner-authorized R5 blocker remediation of **goodLAC**.

`MODE=BLOCKER_REMEDIATION_IMPLEMENTATION`
`SESSION_SEGMENT=POSTV1-R5-R001-MULTI-PI-ADMIN-CONTROL-PLANE`
`REPOSITORY=itecob/goodLAC`
`R5_BLOCKED_SOURCE_HEAD=7d4730ec430ab95ad42446af81568570e02577ea`
`ACCEPTED_HISTORICAL_RELEASE=1.0.0-rc.11`
`TARGET_RELEASE_TRAIN=1.0.0-rc.12`

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Web-File-Tool for repository inspection. Any repository mutation must
be delivered as one owner-executable package and one self-contained Bash command.

## 2. Mandatory durable reads

Read first, in order:

1. `PROJECT_STATE.json`
2. `tasks/ACTIVE_TASK.md`
3. `README.md`
4. `SECURITY.md`
5. `docs/ARCHITECTURE.md`
6. `docs/ADMIN_API.md`
7. `docs/LACCTL.md`
8. `docs/POST_V1_REMEDIATION_ROADMAP.md`
9. `UPSTREAM_LOCK.json`
10. R1-R4 owner execution evidence
11. all Phase 7 admin-socket remediation evidence/tests
12. `packages/admin/transport.py`
13. `packages/admin/service.py`
14. `packages/lacctl/client.py`
15. `scripts/lac-admin-server`
16. `scripts/pi_v1_admin_server.py`
17. `scripts/pi_v1_terminal.py`
18. `scripts/pi_native_tui_host.py`
19. `scripts/pi_v1_controller_bridge.py`
20. productization/installed-wrapper source and tests.

## 3. Owner-UAT facts that are binding

R5 retained regression passed, candidate build/install passed, installed static doctor passed,
installed dynamic doctor passed with exact Pi and FreeToken pins, and the accepted external
FreeToken endpoint became ready.

Before any owner permission choice, Scenario B failed when installed governed Pi attempted to
start `pi_v1_admin_server.py` and received:

`AdminTransportError: administrator socket is already active`

The retained UAT root showed a live listener at:

`$XDG_RUNTIME_DIR/lac/admin-v1.sock`

owned by a Python process. R5 source proved it had previously executed:

`policy_json="$(admin_json permissions list)"`

where `admin_json` invokes `admin_start`. Bash command substitution ran that function in a
subshell, so `ADMIN_PID=$!` never propagated to the parent R5 shell. The owner admin process
therefore survived and collided with the native Pi host.

A separate ordinary installed `pi` invocation also failed on an already-active admin socket.
This exposed a product-level limitation: native Pi startup currently launches a per-Pi
`pi_v1_admin_server.py`, while the owner CLI uses the same fixed `UnixAdminServer` socket.

## 4. Product requirement

Multiple simultaneous goodLAC-governed Pi sessions must be supported on one machine/server,
subject to real hardware/model-runtime capacity.

The intended authority topology is one canonical controller/admin truth capable of governing
many concurrent Pi sessions/projects, not one global socket owner per Pi process.

Do not assume that FreeToken/GPU execution must be single-request. Model-runtime concurrency and
capacity are separate from goodLAC authority concurrency.

## 5. Required design properties

Design and implement the smallest architecture that satisfies all of these:

- one canonical durable controller state may govern Pi A, Pi B, Pi C concurrently;
- owner administration remains owner-only and outside the model sandbox;
- concurrent Pi sessions do not compete to bind the same owner socket;
- project/application identity remains controller-derived;
- project A authority cannot cross-bind to project B;
- permission challenges remain opaque, expiring, one-use, exact-session/project bound;
- exact approval creation alone never dispatches;
- current policy and emergency state are re-evaluated before dispatch;
- emergency pause applies coherently to all sessions sharing canonical controller state;
- continuations remain durable, fresh-request-only, explicit on restart, and project-isolated;
- stopping/crashing Pi A does not stop Pi B or the shared admin/control plane;
- existing Phase 7 socket ownership/race protections remain intact;
- model-facing consequential tool surface remains exactly four tools;
- no administrator socket/credentials enter the sandbox;
- fail closed on missing/unavailable shared control-plane service.

Strongly prefer separating machine/controller-scoped admin service ownership from Pi-session
lifecycle. If project registration currently occurs as a side effect of per-Pi admin-server
startup, move/bootstrap that responsibility through a controller-owned trusted path without
granting the model authority. Do not create per-session independent canonical policy universes
unless there is a demonstrated security reason and exact owner semantics remain coherent.

## 6. Required tests

Add deterministic tests proving at minimum:

1. Two governed Pi/native hosts can be alive simultaneously against the same canonical state.
2. Both can independently perform governed requests.
3. Project A `ALWAYS_ALLOW` cannot authorize Project B.
4. Project A continuation/approval/challenge cannot be consumed by Project B.
5. Emergency pause blocks pre-dispatch effects in both sessions.
6. Resume does not itself dispatch either session.
7. Terminating one Pi leaves the other operational.
8. Shared admin service restart preserves durable state and no effect auto-resumes.
9. A competing second admin server still fails safely and cannot unlink/steal the active socket.
10. Model/sandbox still cannot access the admin endpoint.
11. R5 harness does not orphan an administrator process when using JSON capture or on failure.
12. Full retained R4/Phase 7 regression chain passes.

Also add a bounded interactive owner-UAT concurrency scenario that leaves Pi A running while Pi B
starts and proves both are usable through the installed default governed path.

## 7. R5 integration-harness repair

Repair the command-substitution lifecycle defect. Do not rely on a PID assignment made in a
subshell. Administrator startup/shutdown ownership must remain explicit and deterministic.

Qualification cleanup must terminate only processes it owns and must never unlink another live
owner endpoint.

## 8. Release/state rules

This remediation is a blocker child of R5. Do not activate R6.

`1.0.0-rc.11` remains the accepted historical release.
`1.0.0-rc.12` remains only the target release train.

After implementation and deterministic qualification PASS:
- record bounded remediation evidence;
- commit the implementation separately;
- reinstall an R5 integrated owner-UAT successor prompt/package;
- leave R5 active for fresh owner execution;
- do not mark R5 PASS from automated tests alone.

If any binding security invariant cannot be preserved, stop with a BLOCKED disposition rather
than weakening it.
