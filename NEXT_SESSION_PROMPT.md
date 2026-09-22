# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / FRESH PHASE 7 INDEPENDENT RE-REVIEW OF RC.9

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

Then read at minimum:

- `packages/admin/transport.py`
- `tests/integration/test_admin_transport.py`
- `scripts/test-pi006`
- `tests/acceptance/test_pi006_native_tui_restart.py`
- `qualification/evidence/p7_admin_socket_bind_race_remediation_owner_execution.json`
- `qualification/evidence/pi006_final_owner_uat.json`
- `docs/PI_V1_GOVERNED_PROFILE.md`
- `docs/V1_PRODUCTIZATION.md`
- relevant PI004/PI005/PI006 implementation/tests and earlier accepted evidence needed to verify the complete Phase 7 delta.

Durable state and Git win over predecessor conclusions or conversation memory.

## 3. Exact handoff facts

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=LAC-P7-R001_REMEDIATION_PASS`
- `PREDECESSOR_GIT_COMMIT=594e523d59962336a846f06775aedef5c96a2423`
- `HANDOFF_BASE_GIT_COMMIT=ff193ac32e8f0c12bb6e07e25c9e43bed57fa771`
- `BLOCKED_REVIEW_CANDIDATE_GIT_COMMIT=fcd77f2548e8f6a6f90400b0cd6caf8dadb4bd92`
- `REVIEW_CANDIDATE_GIT_COMMIT=d798db68016de665e54d2c53558af320daa98b31`
- `CURRENT_CANDIDATE=1.0.0-rc.9`
- `LAST_ACCEPTED_RELEASE=1.0.0-rc.1`
- `REMEDIATION_DISTRIBUTION_SHA256=e1b0482a97101693bbad17a39d5eef3917ad67941eccb2385f40aaa32e78aa03`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p7_admin_socket_bind_race_remediation_owner_execution.json`
- `OWNER_PACKAGE_SHA256=a32a01c6da53d4ddb12df1c72cea476be76317c31cf617b1635af8671c1654fa`
- `PREDECESSOR_BLOCKER_REMEDIATED=P7-B001-ADMIN-SOCKET-BIND-RACE-UNLINK`
- `BLOCKER_IDS=NONE`
- `EXPECTED_NEXT_TASK=LAC-P7-REVIEW`
- `SESSION_SEGMENT=LAC-P7-REVIEW`

Live `HEAD` is expected to be exactly one prompt-only handoff commit after `REVIEW_CANDIDATE_GIT_COMMIT`. Verify that `REVIEW_CANDIDATE_GIT_COMMIT..HEAD` changes only `NEXT_SESSION_PROMPT.md`. Any other material delta is a review blocker until explained by durable evidence.

## 4. Remediation that must be independently verified

The prior review found `P7-B001-ADMIN-SOCKET-BIND-RACE-UNLINK`. rc.8's normal already-active-server path and normal identity-bound `close()` path were safe, but the exception path around `listener.bind(...)` unconditionally unlinked the administrator socket pathname. A contender that passed stale inspection, then lost `bind()` after another owner server created the endpoint, could unlink that winning live endpoint.

rc.9 must be treated as a claim to verify, not accepted evidence. Confirm that:

1. failed `bind()` establishes no pathname cleanup authority;
2. exception cleanup can unlink only a socket whose exact `(st_dev, st_ino)` identity was acquired by that server after successful bind;
3. the deterministic test synchronizes the missing ordering rather than relying on timing or a sequential second-server check;
4. after A loses the bind race and runs cleanup, B's pathname remains and B accepts a legitimate owner `skills.list` administration request;
5. the earlier sequential collision test remains present and passing;
6. owner UID, mode `0600`, runtime-directory validation and `SO_PEERCRED` authority semantics are unchanged.

## 5. Complete retained Phase 7 review scope

Independently re-review the full Phase 7 default-governed Pi UX extension from rc.1 through rc.9:

- PI004: ordinary installed `pi` is governed by default; ungoverned execution requires explicit top-level `--dangerously-bypass-lac`; shell takeover and rollback preserve supported prior state.
- PI005: pinned Pi 0.85.1 native source CLI/TUI runs inside accepted Bubblewrap/network-none confinement; stock tools and ambient resources/extensions are closed; exactly four LAC tools are exposed.
- PI006: restart inspection never dispatches; `/lac-continuations` is read-only; only explicit `/lac-resume` can attempt one fresh request; Pi built-in `/resume` remains untouched.
- rc.5: installed `lacctl`/`lac-owner` option forwarding remains correct without moving administration into model authority.
- rc.6: sequential competing governed Pi launch remains fail-closed and active endpoint cleanup remains identity-bound.
- rc.7: interactive Pi has no broker idle shutdown; probe remains bounded; one-hour continuation TTL remains fail-closed; informational permission backlog remains durable without reviving old requests.
- rc.8: explicit dangerous bypass verifies the accepted Pi pin and launches `packages/coding-agent/src/cli.ts` through checkout-local `tsx`; the obsolete bundle dependency remains absent.
- rc.9: the administrator-socket stale-inspection/bind TOCTOU loser cannot unlink the winning owner endpoint.
- Final rc.8 owner UAT remains relevant for unchanged approval/idempotency, emergency pause, restart recovery, four-tool effects, final workspace state, and dangerous-bypass smoke claims.

The known duplicate completed `/lac-resume` toast visibility issue remains nonblocking unless independent evidence shows a binding acceptance or authority failure.

## 6. Required independent verification

At minimum:

1. Verify exact Git candidate identity, clean state, and the candidate-to-live-HEAD prompt-only delta.
2. Inspect the exact blocked-rc.8-to-rc.9 remediation delta and the material rc.1-to-rc.9 Phase 7 delta.
3. Run `python3 -m unittest tests.integration.test_admin_transport -v` fresh.
4. Run `LAC_PI006_RUN_ROOT="$(mktemp -d)" scripts/test-pi006` fresh unless a concrete environmental constraint prevents it; if prevented, state exactly what could not be rerun and why.
5. Verify `qualification/evidence/p7_admin_socket_bind_race_remediation_owner_execution.json` is tracked in the review candidate and internally consistent.
6. Confirm rc.9 did not broaden the four-tool model surface, move administration into Pi/model authority, weaken emergency/approval/policy/continuation/idempotency semantics, expose credentials, or weaken sandbox/ambient-resource restrictions.
7. Confirm `1.0.0-rc.1` remains the last accepted release until this fresh review passes.

## 7. Review output and stop rule

Return exactly one result for `REVIEW_CANDIDATE_GIT_COMMIT=d798db68016de665e54d2c53558af320daa98b31`:

### If PASS
Durably record Phase 7 acceptance of the exact rc.9 candidate, identify any nonblocking findings, advance the accepted release consistently, install the appropriate closed-roadmap successor prompt/state under the phase-boundary workflow, and stop. Do not implement new product scope.

### If BLOCKED
Return `BLOCKED` with concrete blocker IDs and provide one fresh bounded remediation-segment prompt. Do not remediate in this review session.
