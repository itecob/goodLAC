# ACTIVE TASK — LAC-P7-REVIEW

## Task ID
`LAC-P7-REVIEW`

## Mode
`PHASE_BOUNDARY_INDEPENDENT_REVIEW`

## Objective
Perform one fresh independent Phase 7 re-review of the corrected `1.0.0-rc.9` default-governed Pi UX candidate after bounded remediation of `P7-B001-ADMIN-SOCKET-BIND-RACE-UNLINK`.

The reviewer must independently determine whether the complete Phase 7 candidate preserves the controlling rule:

> **AI proposes. Deterministic software determines authorization and effects.**

## Candidate scope
Review the complete Phase 7 extension from the last independently accepted `1.0.0-rc.1` baseline through the corrected `1.0.0-rc.9` candidate:

- PI004 default-governed ordinary `pi` entrypoint with explicit top-level `--dangerously-bypass-lac`;
- PI005 pinned Pi 0.85.1 native source CLI/TUI inside Bubblewrap/network-none with exactly four LAC tools and ambient resource/extension loading closed;
- PI006 explicit native restart recovery through `/lac-continuations` and `/lac-resume`;
- rc.5 administrator-wrapper forwarding stabilization;
- rc.6 administrator-socket collision/ownership stabilization;
- rc.7 interactive-idle and permission-backlog stabilization;
- rc.8 dangerous-bypass source-CLI stabilization;
- rc.9 deterministic administrator-socket bind-race ownership remediation;
- final PI006 owner-UAT durable evidence retained from rc.8 where unaffected by rc.9.

## Exact candidate facts
- Corrected candidate release: `1.0.0-rc.9`.
- Last independently accepted release: `1.0.0-rc.1`.
- Blocked rc.8 review candidate: `fcd77f2548e8f6a6f90400b0cd6caf8dadb4bd92`.
- Remediation implementation commit: `594e523d59962336a846f06775aedef5c96a2423`.
- Remediation distribution SHA-256: `e1b0482a97101693bbad17a39d5eef3917ad67941eccb2385f40aaa32e78aa03`.
- Remediation owner execution evidence: `qualification/evidence/p7_admin_socket_bind_race_remediation_owner_execution.json`.
- Predecessor blocker `P7-B001-ADMIN-SOCKET-BIND-RACE-UNLINK`: `REMEDIATED_PENDING_FRESH_REVIEW`.
- Blockers entering re-review: `NONE`.
- Exact corrected review-candidate Git commit is installed into root `NEXT_SESSION_PROMPT.md` by the remediation package.

## Binding re-review checks
- Reproduce or inspect the deterministic bind-race regression: contender A passes stale inspection; server B binds; A loses `bind()`; A cleanup runs; B's pathname remains; B still handles a legitimate owner request.
- Confirm failed `bind()` grants no unlink authority and successful cleanup remains identity-bound to the endpoint acquired by that server instance.
- Retain the existing sequential active-server collision behavior.
- Ordinary installed `pi` remains governed by default.
- Ungoverned Pi still requires the explicit top-level dangerous flag and uses the accepted pinned source CLI.
- Governed Pi exposes exactly `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.
- Model/tool authority cannot reach the dangerous bypass, owner admin socket, host credentials, ambient host filesystem, arbitrary executables, or host network.
- Restart never auto-dispatches; owner recovery is explicit and one fresh request only.
- Exact approval remains request/hash/policy bound and single-use.
- Emergency pause retains deny precedence and resume itself never dispatches.
- Idempotency and durable receipts remain exactly-once.
- Interactive TUI has no one-hour inactivity shutdown; continuation TTL remains fail-closed; pending-permission backlog remains informational and durable.
- `scripts/test-pi006` and the retained PI005/PI004/V001/earlier regression chain pass.

## Reviewer constraints
The reviewer is independent and does not remediate. Review the complete retained Phase 7 scope, not only rc.9. Classify only concrete binding violations as blockers. Record non-gating cleanup separately. The known duplicate-completion-toast visibility issue remains nonblocking unless new evidence establishes a binding violation.

## Package required?
No implementation package is part of this task. If the review result requires a durable state transition, follow the phase-boundary review workflow without implementing future product scope in the same review.

## Next task on PASS
Durably record Phase 7 acceptance of the exact corrected `1.0.0-rc.9` candidate and return the project to a closed/accepted roadmap state unless the owner separately authorizes new scope.

## Next task on BLOCKED
Create one fresh bounded remediation segment containing only the new concrete blocker IDs, then require another fresh Phase 7 re-review.
