# ACTIVE TASK — LAC-PI006

## Task ID
`LAC-PI006`

## Objective
Complete owner UAT for the native default-governed Pi experience after the bounded rc.4 restart-recovery stabilization and bounded rc.5 installed administrator-wrapper forwarding stabilization, without broadening LAC authority or the approved tool/resource surface.

## Stabilization state
- PI006 pre-UAT source inspection found that PI005's native TUI no longer exposed the prior explicit D001 restart-recovery owner controls.
- Bounded stabilization implementation commit: `81ea310e2e1bc43b63323c182ac4ce53917d5bad`.
- Candidate release: `1.0.0-rc.8`.
- Native owner recovery controls are `/lac-continuations` and `/lac-resume <continuation_id>` because Pi owns built-in `/resume` for Pi session navigation.
- Owner UAT exposed `PI006-UAT-ADMIN-WRAPPER-001`: installed `lacctl`/`lac-owner` option-style arguments were rejected by outer product argparse before P005 parsing. rc.5 forwards those passthrough commands before outer argparse; admin authority semantics are unchanged.
- Owner UAT then exposed `PI006-UAT-ADMIN-SOCKET-002`: launching a second governed Pi while the first owner admin endpoint was active failed closed as intended, but the contending server cleanup could unlink the active endpoint and the existing server could terminate on the probe's early disconnect. rc.6 binds socket cleanup to the listener identity actually acquired by that server and tolerates the expected disconnect without changing authority semantics.
- Owner UAT then exposed `PI006-UAT-INTERACTIVE-IDLE-003`: the interactive broker host treated 3,600 seconds without a broker RPC as fatal inactivity and could tear down a healthy governed Pi TUI. rc.7 removes only the interactive idle deadline, keeps probe mode bounded, keeps the one-hour continuation TTL fail-closed, and regression-tests that the separate pending-permission backlog remains durable for late owner review and future fresh requests.
- Owner UAT then exposed `PI006-UAT-DANGEROUS-BYPASS-004`: the explicit top-level dangerous bypass still targeted the historical prebuilt Pi bundle, which is absent from the accepted pinned source checkout. rc.8 verifies the accepted pin and launches the exact pinned Pi 0.85.1 source CLI through the checkout-local tsx runtime; installed qualification exercises the real bypass help path. Default Pi governance and authority semantics are unchanged.
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
- Candidate release: `1.0.0-rc.8`.
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
Fresh independent Phase 7 review of the rc.8 candidate.
