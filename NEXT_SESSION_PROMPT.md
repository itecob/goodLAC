# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 7 RC.11 INDEPENDENT RE-REVIEW

## 1. Role and controlling rule

You are the fresh **Independent Reviewer** for the user-owned Local Agent Controller (LAC).

`MODE=PHASE_BOUNDARY_INDEPENDENT_REVIEW`
`SESSION_SEGMENT=LAC-P7-REVIEW`

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

Do not remediate. Independently determine whether the corrected Phase 7 candidate satisfies the binding Phase 7 requirements and whether the concrete rc.10 blocker is actually closed. Return exactly `PASS` or `BLOCKED`.

## 2. Mandatory durable reads

Read first, in this order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read the controlling specification and, at minimum:

- `packages/admin/transport.py`
- `tests/integration/test_admin_transport.py`
- `scripts/test-pi006`
- `tests/acceptance/test_pi006_native_tui_restart.py`
- `qualification/evidence/p7_admin_socket_final_unlink_race_remediation_owner_execution.json`
- `qualification/evidence/phase7_rc10_independent_review.json`
- `qualification/evidence/p7_admin_socket_stale_cleanup_race_remediation_owner_execution.json`
- `qualification/evidence/p7_admin_socket_bind_race_remediation_owner_execution.json`
- `qualification/evidence/pi006_final_owner_uat.json`
- `docs/PI_V1_GOVERNED_PROFILE.md`
- `docs/V1_PRODUCTIZATION.md`

## 3. Exact handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PASS`
- `PREDECESSOR_GIT_COMMIT=818ec607e55f73ef93864ec5a86a793a062262ff`
- `IMPLEMENTATION_GIT_COMMIT=8d2ecfa3a839879302729ac2cb6a07bd28b0f79f`
- `HANDOFF_BASE_GIT_COMMIT=818ec607e55f73ef93864ec5a86a793a062262ff`
- `REVIEW_CANDIDATE_GIT_COMMIT=818ec607e55f73ef93864ec5a86a793a062262ff`
- `REVIEW_CANDIDATE_RELEASE=1.0.0-rc.11`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `REMEDIATED_BLOCKER_IDS=P7-B003-ADMIN-SOCKET-FINAL-LSTAT-UNLINK-TOCTOU`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p7_admin_socket_final_unlink_race_remediation_owner_execution.json`
- `EXPECTED_NEXT_TASK=LAC-P7-REVIEW`
- `SESSION_SEGMENT=LAC-P7-REVIEW`

The live HEAD should be exactly one prompt-only handoff commit after `REVIEW_CANDIDATE_GIT_COMMIT`. Verify that delta before review. Any unexpected material delta is a blocker.

## 4. Review target

The rc.10 blocker was a final TOCTOU between `_unlink_stale_socket_if_same_identity()` validating the stale socket pathname and the subsequent pathname `unlink()`.

The corrected rc.11 implementation claims to use one owner-private administrator socket-directory lifecycle lock for both stale classification/removal and each bind acquisition. Stale cleanup and bind remain separate serialized phases, allowing ordinary contenders to race for bind only after stale removal is complete. Owned exception/close pathname cleanup also participates in the same lifecycle serialization.

Independently verify the mechanism rather than trusting this description.

## 5. Binding review requirements

1. Verify a competing legitimate LAC starter cannot install a live endpoint between A's final stale identity/type/owner validation and A's destructive stale unlink.
2. Verify closure is not merely another pathname `lstat()` before `unlink()`; the synchronization must protect the destructive interval and every legitimate competing bind must participate in the same exclusion protocol.
3. Verify the deterministic regression synchronizes A **after final identity/type/owner validation and before destructive removal**, starts B through the normal LAC startup path, proves B cannot acquire lifecycle serialization during A's critical interval, then after A resumes forces B to win the separately serialized bind race and proves B retains its exact pathname identity and serves owner `skills.list`.
4. Verify rc.10's earlier replacement-before-final-check regression remains meaningful, including its intentional test-only raw replacement that challenges identity validation independently of cooperative startup serialization.
5. Verify rc.9 failed-bind race regression, sequential active-server collision regression, wrong-peer-UID rejection, insecure-runtime-directory fail-closed behavior, `ENOENT` non-authority, owner UID, real-socket validation, owner-private runtime directory, mode `0600`, and `SO_PEERCRED` remain intact.
6. Run fresh when executable access is available:
   - `python3 -m unittest tests.integration.test_admin_transport -v`
   - `LAC_PI006_RUN_ROOT="$(mktemp -d)" scripts/test-pi006`
7. Preserve the complete Phase 7 scope: default-governed `pi`, explicit pinned dangerous bypass, exact four LAC model tools, admin isolation, emergency pause, exact approval, continuation, idempotency, credentials, and Bubblewrap/network-none semantics.
8. Verify release/version/evidence claims for `1.0.0-rc.11`, including the recorded deterministic distribution SHA and exact owner execution evidence.
9. Do not create new architecture scope. Findings are only `BLOCKER` or `NONBLOCKING` under the controlling review rules.

If the connected project root is read-only/non-executable, do not represent owner-host tests as fresh reviewer execution. Inspect the live source, Git/evidence, and use only bounded synthetic local fixtures needed to validate the concurrency claim.

## 6. Result and handoff

Return exactly one phase result:

- `PASS`: record rc.11 as the accepted Phase 7 candidate and close the current owner-authorized Phase 7 roadmap unless durable state contains a further explicit owner task. Install a recoverable successor prompt reflecting that state.
- `BLOCKED`: identify only concrete binding blocker IDs and install a fresh bounded remediation prompt for those blockers. Do not remediate in the review session.

The duplicate completed `/lac-resume` toast remains a previously recorded nonblocking UI finding unless new evidence makes it materially violate a binding requirement.
