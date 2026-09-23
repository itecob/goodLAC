# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 7 COMPLETE — ROADMAP CLOSED

## 1. Role and controlling rule

You are the successor state verifier for the user-owned **Local Agent Controller (LAC)**.

`MODE=ROADMAP_CLOSED`
`SESSION_SEGMENT=NONE`

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

The current owner-authorized roadmap is complete. Do not invent or begin new implementation scope unless the owner explicitly authorizes a new roadmap task.

## 2. Mandatory durable reads

Read first, in this order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read only the files needed for the owner's current request.

## 3. Accepted state

- `PHASE_7_REVIEW_RESULT=PASS`
- `ACCEPTED_RELEASE=1.0.0-rc.11`
- `REVIEW_CANDIDATE_GIT_COMMIT=818ec607e55f73ef93864ec5a86a793a062262ff`
- `IMPLEMENTATION_GIT_COMMIT=8d2ecfa3a839879302729ac2cb6a07bd28b0f79f`
- `REVIEW_ACCEPTANCE_GIT_COMMIT=f8b975b7ea1850b382d702eefa4fcec4119f05b1`
- `BLOCKER_IDS=NONE`
- `ACTIVE_TASK=NONE`
- `ROADMAP_STATUS=CLOSED`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p7_admin_socket_final_unlink_race_remediation_owner_execution.json`
- `INDEPENDENT_REVIEW_EVIDENCE=qualification/evidence/phase7_rc11_independent_review.json`

The live HEAD should be exactly one prompt-only handoff commit after `REVIEW_ACCEPTANCE_GIT_COMMIT`. Verify that delta before relying on this handoff. Any unexpected material delta must be reported rather than silently accepted.

## 4. Phase 7 disposition

The corrected rc.11 candidate closed `P7-B003-ADMIN-SOCKET-FINAL-LSTAT-UNLINK-TOCTOU` by serializing stale classification/removal and every legitimate administrator-socket bind acquisition on the same validated owner-private socket-directory lifecycle lock. Owned exception/close cleanup participates in the same lifecycle serialization. The exact-window regression and retained Phase 7/PI006 gate passed in owner evidence; the independent reviewer had read-only/non-executable tunnel access and did not represent owner-host tests as fresh reviewer execution.

The previously recorded duplicate completed `/lac-resume` toast remains nonblocking.

## 5. Successor behavior

If the owner asks for project status, report that Phase 7 is accepted at `1.0.0-rc.11` and the current roadmap is closed.

If the owner explicitly authorizes new LAC work, treat that owner instruction as the new roadmap authority. Create a bounded durable task/state transition before implementation, preserve the accepted Phase 7 baseline, and use a fresh implementation segment. Do not reopen Phase 7 merely because a future task is added.

If the owner has not authorized new work, there is no implementation task to execute and no further session is required.
