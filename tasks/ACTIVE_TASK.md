# ACTIVE TASK — POSTV1-R3 PI TUI OWNER PERMISSION GATE

## Task ID
`POSTV1-R3-PI-TUI-OWNER-PERMISSION-GATE`

## Mode
`IMPLEMENTATION_SEGMENT`

## Historical accepted authority/runtime baseline
- accepted release: `1.0.0-rc.11`
- prior Phase 7 review: `PASS`
- prior authority/runtime roadmap: `CLOSED`

## R2 predecessor
- implementation commit: `97c93d6386d689216cf166c1ba81d3ef4ee7011a`
- result: `PASS`
- project-aware scope: controller-derived project-specific Pi application identity
- ordinary workspace precedence: explicit governed `--workspace` -> configured `fixed` workspace -> canonical launch CWD
- cross-project continuation recovery: fail-closed

## Active implementation scope
Implement the controller-owned owner permission decision gate inside the trusted pinned Pi TUI extension using the exact R1 choices and R2 project-aware scope. The model must receive no permission-management tool or owner-decision authority. General owner admin socket remains outside the sandbox. Use bounded opaque challenges with exact session/continuation/pending binding, expiry, one-use consumption, and fail-closed cancellation/disconnect/restart behavior.

## Target release train
`1.0.0-rc.12` — not accepted until R5 integrated owner UAT and R6 fresh independent review PASS.

## Blockers
None recorded.
