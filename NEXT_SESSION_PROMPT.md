# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / FRESH PHASE 7 INDEPENDENT RE-REVIEW OF RC.10

## 1. Role and mode

You are the **Fresh Independent Reviewer** for the user-owned **Local Agent Controller (LAC)**.

`MODE=PHASE_BOUNDARY_INDEPENDENT_REVIEW`
`SESSION_SEGMENT=LAC-P7-REVIEW`

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.
Do not remediate in this session. Return exactly `PASS` or `BLOCKED` for the Phase 7 candidate, with concrete blocker IDs only for binding violations.

## 2. Mandatory durable reads

Read first, in exactly this order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read at minimum `packages/admin/transport.py`, `tests/integration/test_admin_transport.py`, `scripts/test-pi006`, `tests/acceptance/test_pi006_native_tui_restart.py`, `qualification/evidence/p7_admin_socket_stale_cleanup_race_remediation_owner_execution.json`, `qualification/evidence/p7_admin_socket_bind_race_remediation_owner_execution.json`, `qualification/evidence/pi006_final_owner_uat.json`, `docs/PI_V1_GOVERNED_PROFILE.md`, `docs/V1_PRODUCTIZATION.md`, and relevant PI004/PI005/PI006 files/evidence needed for the complete Phase 7 delta.

Durable state and Git win over predecessor conclusions or conversation memory.

## 3. Exact handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-P7-R002_REMEDIATION_PASS`
- `PREDECESSOR_GIT_COMMIT=cfd648dc3273a64c80a529fd8688f621b02cbfc1`
- `HANDOFF_BASE_GIT_COMMIT=0fce7fead1ef4290da556434355ecc4d735a1ff2`
- `BLOCKED_REVIEW_CANDIDATE_GIT_COMMIT=d798db68016de665e54d2c53558af320daa98b31`
- `REVIEW_CANDIDATE_GIT_COMMIT=9ca498c5abff6dc1e55c63d45c5e140618d9c8eb`
- `CURRENT_CANDIDATE=1.0.0-rc.10`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `REMEDIATION_DISTRIBUTION_SHA256=268be5b8e62a2eee352a565f6a2e6867aed3f5a7d4f9f5779f93c9f3d46ad47d`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p7_admin_socket_stale_cleanup_race_remediation_owner_execution.json`
- `OWNER_PACKAGE_SHA256=94e9250f11702f537d9ad26ba243da8ece5d027f47f56e9158d176f83ce85d5d`
- `PREDECESSOR_BLOCKER_REMEDIATED=P7-B002-ADMIN-SOCKET-STALE-CLEANUP-TOCTOU-UNLINK`
- `BLOCKER_IDS=NONE`
- `EXPECTED_NEXT_TASK=LAC-P7-REVIEW`
- `SESSION_SEGMENT=LAC-P7-REVIEW`

Live `HEAD` is expected to be exactly one prompt-only handoff commit after `REVIEW_CANDIDATE_GIT_COMMIT`. Verify that `REVIEW_CANDIDATE_GIT_COMMIT..HEAD` changes only `NEXT_SESSION_PROMPT.md`. Any other material delta is a review blocker until explained by durable evidence.

## 4. Remediation that must be independently verified

The rc.9 stale cleanup path recorded the initial owner socket identity, but after a failed liveness probe it unconditionally unlinked the pathname. A replacement live owner endpoint could therefore be removed between stale classification and unlink. rc.10 must be treated as a claim to verify, not accepted evidence. Confirm that:

1. stale classification captures the exact `(st_dev, st_ino)` of the owner socket before removal authority exists;
2. `ENOENT` during probing returns without unlinking any later pathname;
3. after `ECONNREFUSED`, final cleanup re-establishes exact socket type, owner UID and identity before unlink;
4. disappearance during final cleanup is non-authorizing and does not unlink a later pathname;
5. identity/type/owner replacement fails closed without unlinking the replacement;
6. the deterministic regression synchronizes A after classification and before final identity-bound removal, then lets B replace/bind and proves B retains identity and serves owner `skills.list`;
7. rc.9 failed-bind identity-bound cleanup and sequential collision behavior remain intact.

## 5. Complete retained Phase 7 review scope

Independently re-review the full Phase 7 default-governed Pi UX extension from rc.1 through rc.10: PI004 default-governed entrypoint, PI005 native governed Pi TUI, PI006 restart recovery, rc.5 admin-wrapper forwarding, rc.6 socket lifecycle stabilization, rc.7 idle/backlog stabilization, rc.8 dangerous-bypass source stabilization, rc.9 bind-race remediation, and rc.10 stale-cleanup replacement-race remediation. Final rc.8 owner UAT remains relevant for unchanged approval/idempotency, emergency pause, restart recovery, four-tool effects, final workspace state, and dangerous-bypass smoke claims.

## 6. Required independent verification

At minimum:

1. Verify exact Git candidate identity, clean state, and candidate-to-live-HEAD prompt-only delta.
2. Inspect the exact rc.9-to-rc.10 remediation delta and the material rc.1-to-rc.10 Phase 7 delta.
3. Run `python3 -m unittest tests.integration.test_admin_transport -v` fresh.
4. Run `LAC_PI006_RUN_ROOT="$(mktemp -d)" scripts/test-pi006` fresh unless a concrete environmental constraint prevents it; if prevented, state exactly what could not be rerun and why.
5. Verify `qualification/evidence/p7_admin_socket_stale_cleanup_race_remediation_owner_execution.json` is tracked in the review candidate and internally consistent.
6. Confirm rc.10 did not broaden the four-tool model surface, move administration into Pi/model authority, weaken emergency/approval/policy/continuation/idempotency semantics, expose credentials, or weaken sandbox/ambient-resource restrictions.
7. Confirm `1.0.0-rc.1` remains the last accepted release until this fresh review passes.

## 7. Review output and stop rule

Return exactly one result for `REVIEW_CANDIDATE_GIT_COMMIT=9ca498c5abff6dc1e55c63d45c5e140618d9c8eb`. On PASS, durably record Phase 7 acceptance and close the roadmap unless separately authorized scope exists. On BLOCKED, return concrete blocker IDs and one fresh bounded remediation prompt. Do not remediate in the review session.
