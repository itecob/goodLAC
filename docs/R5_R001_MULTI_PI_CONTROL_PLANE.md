# R5-R001 Multi-Pi Administrator Control Plane

R5-R001 separates administrator socket ownership from Pi-session lifecycle. One owner-only
`UnixAdminServer` remains the canonical local administration endpoint for one canonical SQLite
controller state. Governed Pi hosts attach to that shared machine/controller-scoped service and
validate exact state path plus device/inode identity before proceeding. Concurrent legitimate
starters continue to rely on the accepted Phase 7 lifecycle lock; a bind loser never gains
pathname-cleanup authority.

Project capability registration is performed during the trusted controller-side session
initialization path from the controller-derived canonical project root. It is not exposed as a
model tool and does not grant the model administrator authority. Stopping one Pi does not stop
the shared control plane or another Pi. A missing/unavailable or cross-bound shared endpoint
fails closed.

The model-facing consequential surface remains exactly `lac_fs_read`, `lac_fs_create`,
`lac_fs_replace`, and `lac_shell_exec`. Permission challenges, exact approvals, policy/emergency
re-evaluation, durable continuations, idempotency, receipts, and project isolation retain their
accepted semantics.

`1.0.0-rc.11` remains the accepted historical release. R5-R001 is remediation on the
`1.0.0-rc.12` target train and does not itself accept that release. R6 is not activated.
