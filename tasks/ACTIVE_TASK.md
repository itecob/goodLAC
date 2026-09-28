# ACTIVE TASK — POSTV1 R5 INTEGRATED OWNER UAT / RELEASE QUALIFICATION

## Status
`ACTIVE`

R5-R001 multi-Pi administrator control-plane remediation passed deterministic qualification at
implementation commit `3cb10d94e349df2f1da76f298ceb0d80b4d322be`. This does **not** accept `1.0.0-rc.12`.

## Fresh owner-UAT requirements
Run from at least two ordinary project directories through the installed default-governed `pi` path.

1. Start Pi A and leave it running.
2. Start Pi B while Pi A remains alive; verify both are usable and share one canonical administrator/control-plane service.
3. Verify their controller-derived project application identities are distinct.
4. Exercise Allow once, Always allow, Ask every time, Deny once, Always deny, overwrite/replace, scope display, and exact project isolation.
5. Prove Project A policy, continuation, approval, and challenge material cannot authorize Project B.
6. Exercise restart/recovery and prove no effect auto-resumes.
7. Pause emergency state and prove both sessions block before dispatch; resume must dispatch neither.
8. Terminate Pi A and verify Pi B and the shared service remain operational.
9. Perform a bounded owner-owned shared-service restart and verify durable state remains and no continuation/effect auto-resumes.
10. Verify the model surface remains exactly four consequential tools and the sandbox cannot access the owner admin endpoint.

If an explicitly owned temporary administrator process is needed by the UAT harness, source
`scripts/post-v1-r5-admin-harness`; call `admin_start` directly in the parent shell. Never invoke
`admin_start` from command substitution or a pipeline. Cleanup may signal only the captured
`ADMIN_PID` and must never unlink a socket.

After fresh owner UAT PASS, record bounded R5 evidence and stage an exact `1.0.0-rc.12` review
candidate for a future independent review. Do not activate R6 in advance and do not represent
`1.0.0-rc.12` as accepted.
