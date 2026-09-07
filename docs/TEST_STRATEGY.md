# Test Strategy

## Phase 0 deterministic gate

Required for the bootstrap qualification candidate:

1. every upstream checkout matches its pinned commit;
2. each planned-for-reuse candidate's checked-out license matches the expected license family;
3. Waggle remains code-reuse-disabled unless an authoritative root license is found and explicitly re-qualified;
4. Airlock source-path probes confirm the actual policy/HITL/execute sequence and the exact-binding/pre-dispatch-recheck gap that drives `AIRLOCK_WRAPPED`;
5. targeted upstream Airlock tests for HITL and core middleware pass on the pinned revision;
6. OpenClaw source contains explicit approval-binding mismatch tests/patterns;
7. Pi source exposes modular tool construction compatible with a controller-backed tool surface;
8. no Phase 1+ implementation is present.

If a required deterministic gate cannot run, Phase 0 is BLOCKED rather than inferred PASS.

## Permanent conformance direction

Subsequent phases must retain deterministic tests for authorization, approval integrity, idempotent effects, crash/restart state, emergency pause, credential isolation, and sandbox escape. Security tests verify whether a forbidden effect actually occurred, not merely whether policy returned DENY.

## Review discipline

Builder iterations run deterministic tests. One fresh independent review occurs at the phase boundary. Only concrete violated invariants/acceptance criteria/security boundaries/required functionality/package or data-integrity failures are blockers. Optional improvements are nonblocking backlog.
