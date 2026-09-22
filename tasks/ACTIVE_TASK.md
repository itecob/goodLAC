# ACTIVE TASK — LAC-P7-REVIEW

## Task ID
`LAC-P7-REVIEW`

## Mode
`PHASE_BOUNDARY_INDEPENDENT_REVIEW`

## Objective
Perform one fresh independent Phase 7 review of the `1.0.0-rc.8` default-governed Pi UX candidate after completed PI006 owner UAT.

The reviewer must independently determine whether the Phase 7 delta preserves the controlling rule:

> **AI proposes. Deterministic software determines authorization and effects.**

## Candidate scope
Review the complete Phase 7 extension from the last independently accepted `1.0.0-rc.1` baseline through the rc.8 candidate:

- PI004 default-governed ordinary `pi` entrypoint with explicit top-level `--dangerously-bypass-lac`;
- PI005 pinned Pi 0.85.1 native source CLI/TUI inside Bubblewrap/network-none with exactly four LAC tools and ambient resource/extension loading closed;
- PI006 explicit native restart recovery through `/lac-continuations` and `/lac-resume`;
- rc.5 administrator-wrapper forwarding stabilization;
- rc.6 administrator-socket collision/ownership stabilization;
- rc.7 interactive-idle and permission-backlog stabilization;
- rc.8 dangerous-bypass source-CLI stabilization;
- final PI006 owner-UAT durable evidence.

## Exact candidate facts
- Candidate release: `1.0.0-rc.8`.
- Last independently accepted release: `1.0.0-rc.1`.
- rc.8 implementation commit: `430eafc4fc2bf9ea578390efbbcbfa8edf3bc7af`.
- rc.8 stabilization handoff HEAD before final-UAT recording: `bdfc6a10ab020fb9d600bc04b3215f21a124ebd2`.
- rc.8 deterministic distribution SHA-256: `74945c5813414b38fc405e684e42c9bd612d7b9733bfb8dfda7c95ff7ee6d756`.
- Final owner-UAT evidence: `qualification/evidence/pi006_final_owner_uat.json`.
- Blockers entering review: `NONE`.
- Exact review-candidate Git commit is installed into root `NEXT_SESSION_PROMPT.md` by the finalization package.

## Binding review checks
- Ordinary installed `pi` is governed by default.
- Ungoverned Pi requires the explicit top-level dangerous flag and uses the accepted pinned source CLI.
- Governed Pi exposes exactly `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.
- Model/tool authority cannot reach the dangerous bypass, owner admin socket, host credentials, ambient host filesystem, arbitrary executables, or host network.
- Restart never auto-dispatches; owner recovery is explicit and one fresh request only.
- Exact approval remains request/hash/policy bound and single-use.
- Emergency pause retains deny precedence and resume itself never dispatches.
- Idempotency and durable receipts remain exactly-once.
- Interactive TUI has no one-hour inactivity shutdown; synchronous continuation TTL remains one hour and expired continuations remain fail-closed.
- Pending-permission backlog remains durable for later owner review but never revives an expired/original request.
- rc.8 removed the obsolete prebuilt-bundle dependency without weakening the dangerous-bypass separation.
- `scripts/test-pi006` and retained regression chain pass.
- Final PI006 owner-UAT evidence is internally consistent with the preserved isolated UAT database/workspace.

## Reviewer constraints
The reviewer is independent and does not remediate. Classify only concrete binding violations as blockers. Record non-gating cleanup separately.

## Package required?
No implementation package is part of this task. If the review result requires a durable state transition, follow the phase-boundary review workflow and hand the result to the owner without implementing future product scope in the same review.

## Next task on PASS
Record Phase 7 acceptance of the exact reviewed rc.8 candidate and return the project to a closed/accepted roadmap state unless the owner separately authorizes new scope.

## Next task on BLOCKED
Create a fresh bounded remediation segment containing only the review blocker IDs, then require one fresh Phase 7 re-review.
