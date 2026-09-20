# ADR-010 — Default-Governed Pi Entrypoint

**Status:** OWNER-AUTHORIZED FOR IMPLEMENTATION
**Date:** 2026-09-19

## Context

The accepted v1 release candidate proved a no-bypass LAC-governed Pi profile, but ADR-008 made that profile opt-in through `lac-pi` while ordinary `pi` remained unmanaged. The owner has explicitly amended that product default after Phase 6 acceptance.

## Decision

1. The ordinary LAC-installed `pi` command is governed by default and enters the qualified LAC Pi profile.
2. `lac-pi` remains a compatibility alias for the same governed path.
3. Ungoverned Pi is an explicit owner/debug escape hatch: `pi --dangerously-bypass-lac ...`. The launcher verifies the exact pinned Pi checkout before executing that path and visibly warns that LAC governance is disabled.
4. The dangerous bypass is available only at the top-level owner launcher. It does not become a governed model capability. The governed shell executable allowlist continues to exclude Node, Pi and arbitrary launchers.
5. A pre-existing user-level `pi` command must be backed up before LAC takeover and restored exactly on rollback. The prior LAC install-state record must also be restored byte-for-byte.
6. PI004 changes launch/product defaults only. It does not change canonical LAC authority, policy, approval, identity, lease, receipt, credential or effect semantics.
7. The current custom governed terminal remains the PI004 frontend. Native Pi TUI integration is PI005 and must separately prove that Pi resources/extensions cannot reintroduce ambient authority.
8. When a tool manager such as mise places another `pi` executable ahead of `~/.local/bin/pi`, PI004 installs a small owner-shell function that dispatches `pi` to the LAC launcher by absolute path. This overrides PATH precedence without modifying the tool manager or its Pi installation. The shell integration is backed up exactly and restored/removed on rollback.

## Supersession

This ADR amends ADR-008 Decision 3 only with respect to the default installed command. Ordinary unmanaged Pi may still be used deliberately for debugging/testing, but it is no longer the normal LAC-installed `pi` path.
