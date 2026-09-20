# ACTIVE TASK — LAC-PI005

## Task ID
`LAC-PI005`

## Objective
Replace the custom governed terminal frontend with Pi's native TUI/session surface while preserving the exact LAC-governed authority boundary.

## In scope
- Use the pinned Pi 0.85.1 supported TUI/session/SDK surfaces rather than a competing custom TUI.
- Keep ordinary installed `pi` default-governed through the PI004 launcher.
- Preserve only controller-backed consequential tools and the accepted Bubblewrap ambient-authority boundary.
- Qualify Pi resource/package/extension/skill loading so executable extensions cannot create an alternate consequential-effect path.
- Preserve controller-owned principal/agent/application/skill identity, owner-only administration, permissions, exact approvals, emergency pause, receipts/idempotency and restart/non-auto-dispatch behavior.
- Preserve `pi --dangerously-bypass-lac` only as the explicit top-level owner/debug escape hatch; it must not become a governed-model escalation route.
- Deterministic native-TUI/source/conformance tests and retained PI004/V001 regressions.

## Out of scope
- New harnesses or model providers.
- New authority-core semantics.
- External application workflow logic.
- Generic compatibility facade.
- Expanding consequential tool authority merely to match stock Pi defaults.

## Accepted predecessor
- PI004 implementation commit: `2b26291ba0ca0d2f61c07a47e9c4317396be6420`
- PI004 candidate release: `1.0.0-rc.2`
- Last independently accepted release remains `1.0.0-rc.1`.
- PI004 distribution SHA-256: `6d42e53d46d3be8b844dc5d9da1870728653a8ce9a36cbfd9f70a3db45757b4c`

## Acceptance tests
- Normal `pi` opens the real Pi TUI/session surface through the LAC-governed process boundary.
- Stock Bash/read/write/edit authority is not reintroduced.
- Extensions/resources cannot acquire ambient filesystem/process/network/credential/admin authority outside LAC.
- Existing permission/approval/continuation/emergency/idempotency/receipt semantics remain intact.
- Dangerous bypass remains owner-explicit and unavailable through governed shell/tool authority.
- Applicable PI004/V001 and earlier regression gates pass.

## Package required?
`yes`

## Next task on success
`LAC-PI006` — owner UAT and stabilization of the native default-governed Pi experience.
