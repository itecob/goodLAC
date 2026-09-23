# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / BOUNDED PHASE 7 RC.10 FINAL-UNLINK RACE REMEDIATION

## 1. Role and controlling rule

You are the fresh **Lead Implementation Engineer** for the user-owned Local Agent Controller (LAC).

`MODE=IMPLEMENTATION_SEGMENT`
`SESSION_SEGMENT=LAC-P7-R003-ADMIN-SOCKET-FINAL-UNLINK-RACE`

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

Do not broaden the product. Remediate only the concrete Phase 7 blocker below, run the complete retained gate, produce one owner-executable package, and stop at owner execution.

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
- `qualification/evidence/phase7_rc10_independent_review.json`
- `qualification/evidence/p7_admin_socket_stale_cleanup_race_remediation_owner_execution.json`
- `qualification/evidence/p7_admin_socket_bind_race_remediation_owner_execution.json`
- `qualification/evidence/pi006_final_owner_uat.json`
- `docs/PI_V1_GOVERNED_PROFILE.md`
- `docs/V1_PRODUCTIZATION.md`

## 3. Exact handoff facts

- `PREDECESSOR_ROLE=Fresh Independent Reviewer`
- `PREDECESSOR_RESULT=BLOCKED`
- `PREDECESSOR_GIT_COMMIT=47fa58699e91a521dbfdf07c6b774644d7364381`
- `HANDOFF_BASE_GIT_COMMIT=47fa58699e91a521dbfdf07c6b774644d7364381`
- `BLOCKED_REVIEW_CANDIDATE_GIT_COMMIT=9ca498c5abff6dc1e55c63d45c5e140618d9c8eb`
- `BLOCKED_REVIEW_CANDIDATE_RELEASE=1.0.0-rc.10`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `BLOCKER_IDS=P7-B003-ADMIN-SOCKET-FINAL-LSTAT-UNLINK-TOCTOU`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/phase7_rc10_independent_review.json`
- `EXPECTED_NEXT_TASK=LAC-P7-R003-ADMIN-SOCKET-FINAL-UNLINK-RACE`
- `SESSION_SEGMENT=LAC-P7-R003-ADMIN-SOCKET-FINAL-UNLINK-RACE`

The live HEAD should be exactly one prompt-only handoff commit after `PREDECESSOR_GIT_COMMIT`. Verify that delta before implementation. Any unexpected material delta is a blocker.

## 4. Concrete blocker to remediate

`P7-B003-ADMIN-SOCKET-FINAL-LSTAT-UNLINK-TOCTOU`

rc.10's stale cleanup records the classified socket identity and later calls `_unlink_stale_socket_if_same_identity()`. That helper performs a final `lstat()` identity/type/owner check and then a separate pathname `unlink()`.

This leaves a final TOCTOU window:

```text
A: final lstat(path) confirms stale socket S
B: unlink S
B: bind live administrator socket B at path
A: unlink(path)
=> A removes B's live endpoint
```

The rc.10 synchronized regression does not exercise this ordering. It pauses before the helper's final identity check, so a replacement already present when A resumes is detected. It does not prove safety after A's final validation but before its destructive unlink.

## 5. Binding remediation requirements

1. Close the final validation-to-unlink race for competing legitimate LAC starters.
2. Do not claim closure by adding another pathname `lstat()` before `unlink()`.
3. Use the smallest deterministic synchronization or equivalent replacement-safe mechanism that prevents another LAC contender from installing a live endpoint inside the stale-removal critical interval.
4. Preserve `ENOENT` as non-authorizing: disappearance never grants authority to unlink a later pathname.
5. Preserve owner UID, real-socket validation, owner-private runtime directory, mode `0600`, and `SO_PEERCRED`.
6. Add a deterministic regression synchronized **after A's final identity/type/owner validation and before destructive removal**. Let B replace/bind; after A resumes, prove B's pathname identity remains and B successfully serves owner `skills.list`.
7. Retain:
   - rc.10 earlier replacement-before-final-check regression;
   - rc.9 failed-`bind()` race regression;
   - sequential active-server collision regression;
   - wrong-peer-UID rejection;
   - insecure-runtime-directory fail-closed behavior.
8. Run fresh:
   - `python3 -m unittest tests.integration.test_admin_transport -v`
   - `LAC_PI006_RUN_ROOT="$(mktemp -d)" scripts/test-pi006`
9. Preserve the complete Phase 7 scope: default-governed `pi`, explicit pinned dangerous bypass, exact four LAC model tools, admin isolation, emergency pause, exact approval, continuation, idempotency, credentials, and Bubblewrap/network-none semantics.
10. Advance only to a corrected candidate (normally `1.0.0-rc.11`) for one fresh Phase 7 independent re-review. Do not self-accept the phase.

## 6. Package/release qualification

Follow `docs/NEXT_SESSION_PROMPT_TEMPLATE.md` exactly. Before release, qualify the complete owner-facing package lifecycle against the exact expected predecessor state, including Git delta verification, `git diff --check`, syntax, generated evidence/tracking, exact owner Bash command, rollback, final clean worktree, commit membership, and successor prompt installation.

Any package failure is still this same remediation segment.

## 7. Stop rule

Stop only at a valid gate. The normal successful gate is `OWNER_EXECUTION_REQUIRED`.

On successful owner execution, the package must install a fresh `LAC-P7-REVIEW` root prompt for the corrected candidate. Do not perform that re-review in the remediation session.
