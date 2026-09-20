# ACTIVE TASK — LAC-PI006

## Task ID
`LAC-PI006`

## Objective
Run owner UAT and bounded stabilization for the native default-governed Pi experience delivered by PI005, without broadening LAC authority or the approved tool/resource surface.

## In scope
- Owner UAT of ordinary installed `pi` entering pinned Pi 0.85.1's native TUI through LAC by default.
- Multi-turn native TUI use with the existing four controller-backed consequential tools.
- Owner permission discovery/configuration, exact approval, emergency pause, receipt/idempotency and D001 continuation/restart behavior through the native TUI path.
- Verify restart remains non-auto-dispatch and recovered continuations require an explicit owner event.
- Verify `pi --dangerously-bypass-lac` remains an explicit top-level owner/debug escape hatch and is unavailable through governed model/tool authority.
- Bounded stabilization only for defects discovered by this UAT; rerun PI005 and retained regressions after any remediation.
- Prepare the resulting candidate for the fresh independent Phase 7 review after owner UAT passes.

## Out of scope
- New harnesses or model providers.
- New authority-core semantics.
- Broader consequential tool authority.
- Re-enabling arbitrary Pi extensions/resources in the governed profile.
- Generic compatibility facade or external application workflow logic.

## Accepted predecessor
- PI005 implementation commit: `35dde36cbb63227cdea5ea77552aa1a6f2bcf450`
- PI005 candidate release: `1.0.0-rc.3`
- Last independently accepted release remains `1.0.0-rc.1`.
- PI005 distribution SHA-256: `094bec442836a0cb1ea09738863554d3ca9a86cdc7defaa816c66e9893ab94f8`

## Acceptance tests
- Owner confirms ordinary `pi` visibly opens the real Pi native TUI and remains LAC-governed.
- Permission discovery/configuration and exact approval complete through the unchanged owner-only administration path.
- Emergency pause, receipt/idempotency and D001 continuation/restart semantics remain unchanged.
- Native TUI resource/extension confinement remains passing.
- Dangerous bypass remains explicit and top-level only.
- PI005 and all applicable retained regression gates pass after any stabilization change.

## Package required?
`yes` if stabilization mutation is required; otherwise record owner UAT evidence and advance to fresh independent Phase 7 review without inventing a code change.

## Next task on success
Fresh independent Phase 7 review of the rc.3 candidate.
