# LAC v1 Productization — 1.0.0-rc.1

`LAC-V001` packages the accepted governed Pi reference path without creating a second authority boundary.
Canonical capability, policy, approval, emergency, identity, lease, receipt, credential and continuation state remains in LAC.

## Installed layout

The user-level installer creates versioned releases under `~/.local/share/local-agent-controller/releases/`, an atomic `current` symlink, owner-private configuration at `~/.config/local-agent-controller/v1/config.json`, and convenience commands in `~/.local/bin`:

- `lac-pi` starts only the explicit accepted governed Pi profile.
- `lacctl` is the accepted owner-only P005 administration client.
- `lac-owner` provides bounded aliases for pending permissions, approvals, permissions, skills and emergency control through `lacctl`.
- `lac-config` shows or changes only product/runtime path settings; it cannot set policy or authority.
- `lac-doctor` verifies the installed release and local prerequisites.

Ordinary standalone Pi remains outside LAC governance and is never represented as governed.

## Configuration

Run `lac-config show`. Supported fields are `workspace`, `state`, `trace`, `pi_checkout`, and `runtime` (`manage` or `external`). The JSON file is owner-private mode `0600`. Configuration contains no permission or approval authority.

## Service lifecycle

V001 installs no persistent controller/admin service and no user-systemd unit. This is deliberate: the accepted governed Pi profile lifecycle-manages the owner-only admin socket and, in managed mode, the qualified FreeToken runtime. Adding a persistent authority daemon would broaden the reviewed runtime boundary without a demonstrated requirement.

## Upgrade, state and migration

Releases are versioned and the `current` pointer changes atomically. Existing owner config is preserved. Before installation, an existing controller SQLite database receives a consistent backup under the V1 productization backup directory. `1.0.0-rc.1` performs no database migration and does not rewrite canonical controller state.

## Rollback and recovery

`python3 <installed-app>/scripts/lac-v1 rollback` (normally invoked by the owner package on failure) restores the prior installed release pointer and owner configuration. Because V001 performs no database migration, rollback does not rewrite the canonical controller database. A preinstall database backup remains available for recovery inspection.

Restart never auto-dispatches D001 workflow continuation. The accepted explicit `/resume <continuation_id>` behavior remains unchanged.

## Portable distribution

`scripts/lac-v1 build --output <archive>` builds a deterministic gzip/tar distribution from the exact staged Git index. File content comes from Git index objects, not mutable unstaged worktree bytes. Archive timestamps/owners are normalized; repeated builds from the same index are byte-identical.

## Release qualification

`scripts/test-v001` runs clean-install, upgrade/rollback, configuration, state-preservation and installed-wrapper acceptance, then runs the complete retained `scripts/test-pi003` chain. The owner package additionally runs the exact V001 lifecycle first in a disposable Git worktree at the expected preinstall commit before mutating the live repository.
