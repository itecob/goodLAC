# ACTIVE TASK — LAC-P7-R003-ADMIN-SOCKET-FINAL-UNLINK-RACE

## Task ID
`LAC-P7-R003-ADMIN-SOCKET-FINAL-UNLINK-RACE`

## Mode
`IMPLEMENTATION_SEGMENT`

## Objective
Remediate only `P7-B003-ADMIN-SOCKET-FINAL-LSTAT-UNLINK-TOCTOU` in the Phase 7 `1.0.0-rc.10` administrator-socket lifecycle, then produce one corrected candidate for a fresh Phase 7 independent re-review.

The binding rule remains:

> **AI proposes. Deterministic software determines authorization and effects.**

## Concrete blocker
`packages/admin/transport.py` currently re-validates the stale pathname with `lstat()` and then performs a separate pathname `unlink()`. A second legitimate LAC starter can replace and bind the administrator socket after that final validation but before the unlink, allowing the first contender to remove the second server's live endpoint.

The rc.10 synchronized regression pauses before `_unlink_stale_socket_if_same_identity()` performs its final `lstat()`. It therefore does not cover the remaining final `lstat() -> unlink(pathname)` interleaving.

## In scope
- `packages/admin/transport.py`
- `tests/integration/test_admin_transport.py`
- only the minimal product/version/docs/test/evidence changes required for a corrected Phase 7 candidate
- package/handoff state needed to send that corrected candidate to one fresh Phase 7 re-review

## Out of scope
- authority-core redesign
- policy, approval, continuation, idempotency, credential, sandbox, or tool-surface changes
- additional harness/model/provider work
- unrelated cleanup or refactoring

## Binding remediation requirements
1. Remove the final stale-cleanup check-to-unlink race. A contender that has classified stale socket S must not be able to unlink a different live endpoint B that appears after any validation step and before destructive pathname removal.
2. Do not treat another pre-unlink `lstat()` as sufficient closure. The destructive stale-removal operation must be protected from a competing legitimate LAC start/bind through the critical interval, or use an equivalent mechanism that makes replacement-safe cleanup deterministic.
3. Preserve the rc.10 `ENOENT` rule: disappearance during probing or cleanup grants no authority to unlink a later pathname.
4. Preserve owner UID, real-socket, mode `0600`, validated owner-private runtime directory, and `SO_PEERCRED` behavior.
5. Retain the rc.9 failed-`bind()` race regression and the sequential active-server collision regression.
6. Add a deterministic regression that synchronizes contender A **after A's final identity/type/owner validation and before its destructive unlink**, lets contender B replace and bind the pathname, then resumes A. The test must prove B's pathname still exists with B's acquired identity and B accepts an owner `skills.list`.
7. `scripts/test-pi006` and its complete retained PI005/PI004/V001/earlier regression chain must pass.
8. The governed Pi model-facing surface must remain exactly `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.
9. Ordinary installed `pi` remains governed by default; `--dangerously-bypass-lac` remains explicit, pinned, and unavailable to the governed model.
10. Produce a new corrected candidate version (normally `1.0.0-rc.11`) and send it to one fresh Phase 7 independent re-review. Do not self-accept Phase 7.

## Required implementation discipline
Use the live durable files and Git as truth. Inspect the exact predecessor delta before editing. Run task-specific tests and the complete retained gate. Correct all in-scope deterministic failures before handoff. Release-qualify the complete owner package lifecycle against the exact expected predecessor bytes and metadata.

## Next task on PASS
Fresh `LAC-P7-REVIEW` of the corrected candidate.

## Next task on BLOCKED
Remain in this remediation segment until this blocker is actually closed or a genuine architecture/authority gate is reached.
