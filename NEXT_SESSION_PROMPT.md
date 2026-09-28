# NEXT SESSION PROMPT — goodLAC / POST-V1 R5 INTEGRATED OWNER UAT

You are the Lead Qualification Engineer for **goodLAC**.

`MODE=OWNER_UAT_RELEASE_QUALIFICATION`
`SESSION_SEGMENT=POSTV1-R5-INTEGRATED-OWNER-UAT-RELEASE-QUALIFICATION`
`REPOSITORY=itecob/goodLAC`
`R5_R001_IMPLEMENTATION_COMMIT=3cb10d94e349df2f1da76f298ceb0d80b4d322be`
`ACCEPTED_HISTORICAL_RELEASE=1.0.0-rc.11`
`TARGET_RELEASE_TRAIN=1.0.0-rc.12`

Read first: `PROJECT_STATE.json`, `tasks/ACTIVE_TASK.md`,
`qualification/evidence/post_v1_r5_r001_multi_pi_admin_control_plane_owner_execution.json`,
`docs/R5_R001_MULTI_PI_CONTROL_PLANE.md`, and all R1-R4 / Phase 7 retained evidence.

R5-R001 is deterministically remediated, but R5 still requires fresh installed owner UAT. Do not
activate R6 and do not represent `1.0.0-rc.12` as accepted.

Execute the complete owner-UAT matrix in `tasks/ACTIVE_TASK.md`. The concurrency scenario is binding:
start Pi A through the ordinary installed default-governed `pi` path and leave it alive, then start
Pi B through the same path. Verify both sessions are usable against one canonical shared control
plane while retaining distinct project identities. Exercise all five owner choices and exact project
isolation, emergency pause/resume, restart/recovery, and one-Pi termination while the other remains
operational.

If a temporary administrator process is needed by the UAT harness, source
`scripts/post-v1-r5-admin-harness`; call `admin_start` in the parent shell before any
`policy_json="$(admin_json ...)"` capture. `admin_json` never starts the administrator. Cleanup
must terminate only the captured owned PID and must never unlink another live endpoint.

Only after fresh owner UAT PASS may you record R5 PASS evidence and stage an exact rc.12 review
candidate. R6 remains a later independent-review task.
