# ACTIVE TASK — LAC-P7-REVIEW

## Task ID
`LAC-P7-REVIEW`

## Mode
`PHASE_BOUNDARY_INDEPENDENT_REVIEW`

## Objective
Independently review the corrected Phase 7 `1.0.0-rc.11` candidate after bounded remediation of `P7-B003-ADMIN-SOCKET-FINAL-LSTAT-UNLINK-TOCTOU`.

The binding rule remains:

> **AI proposes. Deterministic software determines authorization and effects.**

## Review scope
- verify the exact candidate Git identity and clean handoff state;
- verify the final administrator-socket stale-cleanup validation-to-unlink race is closed for competing legitimate LAC starters;
- verify the deterministic exact-window regression actually synchronizes after A's final identity/type/owner validation and before destructive removal, starts B through the normal LAC path, and proves B's acquired pathname identity and owner `skills.list` remain intact after A resumes;
- retain rc.10 replacement-before-final-check, rc.9 failed-bind, sequential active-server collision, wrong-peer-UID, insecure-runtime-directory, owner UID, mode `0600`, owner-private runtime directory, and `SO_PEERCRED` coverage;
- verify the complete retained PI006/PI005/PI004/V001/earlier gate and the exact four model tools;
- verify default-governed `pi`, explicit pinned `--dangerously-bypass-lac`, emergency pause, exact approval, continuation, idempotency, credential isolation, and Bubblewrap/network-none semantics remain unchanged;
- verify product/package/evidence/version claims for `1.0.0-rc.11`.

## Out of scope
- remediation during the review;
- authority-core redesign;
- unrelated cleanup/refactoring;
- new harnesses, providers, adapters, or product scope.

## Required evidence
- `qualification/evidence/p7_admin_socket_final_unlink_race_remediation_owner_execution.json`
- predecessor blocked review `qualification/evidence/phase7_rc10_independent_review.json`
- live implementation/tests/docs and Git history.

## Result rule
Return exactly `PASS` or `BLOCKED`. Only concrete violations of binding Phase 7 requirements may block. Do not self-remediate.

## On PASS
Record `1.0.0-rc.11` as the accepted Phase 7 candidate and close the current owner-authorized Phase 7 roadmap unless durable state contains a further explicit owner task.

## On BLOCKED
Create a fresh remediation handoff containing only the concrete blocker IDs and remain within Phase 7.
