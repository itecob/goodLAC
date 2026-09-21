# ACTIVE TASK — LAC-PI006

## Task ID
`LAC-PI006`

## Objective
Complete owner UAT for the native default-governed Pi experience after the bounded rc.4 restart-recovery stabilization, without broadening LAC authority or the approved tool/resource surface.

## Stabilization state
- PI006 pre-UAT source inspection found that PI005's native TUI no longer exposed the prior explicit D001 restart-recovery owner controls.
- Bounded stabilization implementation commit: `81ea310e2e1bc43b63323c182ac4ce53917d5bad`.
- Candidate release: `1.0.0-rc.4`.
- Native owner recovery controls are `/lac-continuations` and `/lac-resume <continuation_id>` because Pi owns built-in `/resume` for Pi session navigation.
- Startup recovery inspection is read-only and never dispatches. Approval alone never dispatches a recovered continuation.
- Model-facing consequential effect surface remains exactly `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.
- Authority core, capability semantics, policy, approval, identity, credentials, leases, receipts and sandbox semantics are unchanged.

## In scope
- Owner UAT of ordinary installed `pi` entering pinned Pi 0.85.1's native TUI through LAC by default.
- Multi-turn native TUI use with the existing four controller-backed consequential tools.
- Owner permission discovery/configuration, exact approval, emergency pause, receipt/idempotency and D001 continuation/restart behavior through the native TUI path.
- Verify restart remains non-auto-dispatch and recovered continuations require an explicit owner event through `/lac-resume`.
- Verify `pi --dangerously-bypass-lac` remains an explicit top-level owner/debug escape hatch and is unavailable through governed model/tool authority.
- Bounded stabilization only for any additional defect discovered by this UAT; rerun PI006/PI005 retained gates after any further remediation.
- Prepare the resulting candidate for the fresh independent Phase 7 review after owner UAT passes.

## Out of scope
- New harnesses or model providers.
- New authority-core semantics.
- Broader consequential tool authority.
- Re-enabling arbitrary Pi extensions/resources in the governed profile.
- Generic compatibility facade or external application workflow logic.

## Accepted predecessor
- PI005 implementation commit: `35dde36cbb63227cdea5ea77552aa1a6f2bcf450`.
- PI005 owner-pass live handoff commit: `f403962d5ef0dc239cd632efbdad1ca0f9a92a65`.
- PI006 stabilization implementation commit: `81ea310e2e1bc43b63323c182ac4ce53917d5bad`.
- Candidate release: `1.0.0-rc.4`.
- Last independently accepted release remains `1.0.0-rc.1`.

## Acceptance tests
- Owner confirms ordinary `pi` visibly opens the real Pi native TUI and remains LAC-governed.
- Permission discovery/configuration and exact approval complete through the unchanged owner-only administration path.
- Emergency pause, receipt/idempotency and D001 continuation/restart semantics remain unchanged.
- A recoverable continuation is reported on restart without dispatch, and only explicit `/lac-resume <continuation_id>` may attempt the one fresh request.
- Native TUI resource/extension confinement remains passing.
- Dangerous bypass remains explicit and top-level only.
- `scripts/test-pi006` and its retained PI005/earlier regression chain pass after stabilization.

## Package required?
`yes` only if owner UAT exposes another in-scope stabilization defect; otherwise record owner UAT evidence and advance to fresh independent Phase 7 review without inventing another code change.

## Next task on success
Fresh independent Phase 7 review of the rc.4 candidate.
