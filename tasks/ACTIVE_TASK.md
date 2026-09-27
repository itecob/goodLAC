# ACTIVE TASK — POSTV1-R5 INTEGRATED OWNER UAT AND RELEASE QUALIFICATION

## Task ID
`POSTV1-R5-INTEGRATED-OWNER-UAT-RELEASE-QUALIFICATION`

## Mode
`OWNER_UAT_AND_RELEASE_QUALIFICATION`

## Historical accepted authority/runtime baseline
- accepted release: `1.0.0-rc.11`
- prior Phase 7 review: `PASS`
- prior authority/runtime roadmap: `CLOSED`

## R4 predecessor
- implementation commit: `6838dbf80c4d9a2572194891d3b355f39a6efbce`
- result: `PASS`
- ordinary terminal path: `lac-owner decide <choice> <continuation_id> <pending_id>`
- canonical authority path: owner-only `permissions.decide`
- low-level full-snapshot policy path remains administrator/scripting only
- no new model permission-management capability or dispatch path

## Active qualification scope
Run real owner UAT from at least two ordinary project directories. Exercise Allow once,
Always allow, Ask every time, Deny once, Always deny, overwrite/replace, restart/recovery,
trusted project-scope display, exact approval behavior, emergency/deny re-evaluation where
applicable, and exact Project A / Project B isolation. Record bounded owner evidence.

Only after the integrated R5 gate passes may the repository stage the `1.0.0-rc.12` review
candidate for a fresh independent R6 security/product review.

## Target release train
`1.0.0-rc.12` — not accepted until R6 fresh independent review PASS.

## Blockers
None recorded.
