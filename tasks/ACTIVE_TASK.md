# ACTIVE TASK — LAC-P7-REVIEW

## Task ID
`LAC-P7-REVIEW`

## Mode
`PHASE_BOUNDARY_INDEPENDENT_REVIEW`

## Objective
Perform one fresh independent Phase 7 re-review of the corrected `1.0.0-rc.10` default-governed Pi UX candidate after bounded remediation of `P7-B002-ADMIN-SOCKET-STALE-CLEANUP-TOCTOU-UNLINK`.

The reviewer must independently determine whether the complete Phase 7 candidate preserves the controlling rule:

> **AI proposes. Deterministic software determines authorization and effects.**

## Candidate scope
Review the complete Phase 7 extension from the last independently accepted `1.0.0-rc.1` baseline through the corrected `1.0.0-rc.10` candidate, including PI004, PI005, PI006, rc.5 through rc.10, and retained final PI006 owner-UAT evidence where unaffected.

## Exact candidate facts
- Corrected candidate release: `1.0.0-rc.10`.
- Last independently accepted release: `1.0.0-rc.1`.
- Prior corrected rc.9 review candidate: `d798db68016de665e54d2c53558af320daa98b31`.
- P7-R002 remediation implementation commit: `cfd648dc3273a64c80a529fd8688f621b02cbfc1`.
- Remediation distribution SHA-256: `268be5b8e62a2eee352a565f6a2e6867aed3f5a7d4f9f5779f93c9f3d46ad47d`.
- Remediation owner execution evidence: `qualification/evidence/p7_admin_socket_stale_cleanup_race_remediation_owner_execution.json`.
- Prior blocker `P7-B001-ADMIN-SOCKET-BIND-RACE-UNLINK`: `REMEDIATED_PENDING_FRESH_REVIEW`.
- New blocker `P7-B002-ADMIN-SOCKET-STALE-CLEANUP-TOCTOU-UNLINK`: `REMEDIATED_PENDING_FRESH_REVIEW`.
- Blockers entering re-review: `NONE`.
- Exact corrected review-candidate Git commit is installed into root `NEXT_SESSION_PROMPT.md` by the remediation package.

## Binding re-review checks
- Reproduce/inspect the deterministic stale-cleanup replacement race: A classifies exact stale socket S; B replaces and binds; A resumes final stale cleanup; A does not unlink B; B's pathname identity remains; B accepts owner `skills.list`.
- Confirm `ENOENT` during probing grants no authority to unlink a later pathname.
- Retain the rc.9 synchronized failed-`bind()` race regression and the earlier sequential active-server collision regression.
- Retain wrong-peer-UID rejection, mode `0600`, owner request success and insecure-runtime-directory fail-closed behavior.
- Ordinary installed `pi` remains governed by default; bypass remains explicit and pinned.
- Governed Pi exposes exactly `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.
- Restart, approval, emergency pause, continuation, idempotency, credential and sandbox semantics remain unchanged.
- `scripts/test-pi006` and its retained PI005/PI004/V001/earlier regression chain pass.

## Reviewer constraints
The reviewer is independent and does not remediate. Review the complete retained Phase 7 scope, not only rc.10. Classify only concrete binding violations as blockers. The known duplicate completed `/lac-resume` toast visibility issue remains nonblocking unless new evidence establishes a binding violation.

## Next task on PASS
Durably record Phase 7 acceptance of the exact corrected `1.0.0-rc.10` candidate and return the project to a closed/accepted roadmap state unless the owner separately authorizes new scope.

## Next task on BLOCKED
Create one fresh bounded remediation segment containing only the new concrete blocker IDs, then require another fresh Phase 7 re-review.
