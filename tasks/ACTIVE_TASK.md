# ACTIVE TASK — POSTV1-R4 INSTALLED TERMINAL FALLBACK AND UX CLEANUP

## Task ID
`POSTV1-R4-INSTALLED-TERMINAL-FALLBACK-UX-CLEANUP`

## Mode
`IMPLEMENTATION_SEGMENT`

## Historical accepted authority/runtime baseline
- accepted release: `1.0.0-rc.11`
- prior Phase 7 review: `PASS`
- prior authority/runtime roadmap: `CLOSED`

## R3 predecessor
- implementation commit: `971148ca33083d4a8015d8c2692e8f49303582b2`
- result: `PASS`
- owner gate: pinned Pi 0.85.1 trusted ExtensionUIContext select/confirm
- authority: canonical goodLAC policy/approval state; no model permission tool
- challenge boundary: bounded, opaque, session/project/exact-subject bound, expiring and one-use
- project scope: controller-derived R2 project application identity

## Active implementation scope
Implement only the installed terminal fallback and UX cleanup for the accepted R1 choices. Provide a concise installed owner command surface for ordinary permission decisions, retain low-level `lacctl permissions set --file` as an administrator/scripting primitive, and correct ordinary installed documentation. Reuse canonical R1 permission/approval semantics; do not create another authority path.

## Target release train
`1.0.0-rc.12` — not accepted until R5 integrated owner UAT and R6 fresh independent review PASS.

## Blockers
None recorded.
