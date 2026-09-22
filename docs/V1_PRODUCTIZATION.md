# LAC v1 Productization — 1.0.0-rc.9 candidate

`LAC-V001` packages the accepted governed Pi reference path without creating a second authority boundary.
Canonical capability, policy, approval, emergency, identity, lease, receipt, credential and continuation state remains in LAC.

## Installed layout

The user-level installer creates versioned releases under `~/.local/share/local-agent-controller/releases/`, an atomic `current` symlink, owner-private configuration at `~/.config/local-agent-controller/v1/config.json`, and convenience commands in `~/.local/bin`:

- `pi` is the default-governed entrypoint and starts the accepted LAC-governed Pi profile.
- `lac-pi` remains a compatibility alias for the same governed path.
- `pi --dangerously-bypass-lac ...` is an explicit top-level owner escape hatch to the exact pinned upstream Pi CLI and is never represented as governed.
- `lacctl` is the accepted owner-only P005 administration client.
- `lac-owner` provides bounded aliases for pending permissions, approvals, permissions, skills and emergency control through `lacctl`.
- `lac-config` shows or changes only product/runtime path settings; it cannot set policy or authority.
- `lac-doctor` verifies the installed release and local prerequisites.

The ordinary installed `pi` command is governed by default. Ungoverned Pi remains available only through the explicit dangerous-bypass launcher path or direct owner/debug execution outside the LAC-managed command. The governed model cannot obtain the dangerous bypass through its accepted shell capability because Node/Pi launchers are not in the exact shell executable allowlist.

## Configuration

Run `lac-config show`. Supported fields are `workspace`, `state`, `trace`, `pi_checkout`, and `runtime` (`manage` or `external`). The JSON file is owner-private mode `0600`. Configuration contains no permission or approval authority.

## Service lifecycle

V001 installs no persistent controller/admin service and no user-systemd unit. This is deliberate: the accepted governed Pi profile lifecycle-manages the owner-only admin socket and, in managed mode, the qualified FreeToken runtime. Adding a persistent authority daemon would broaden the reviewed runtime boundary without a demonstrated requirement.

## Upgrade, state and migration

Releases are versioned and the `current` pointer changes atomically. Existing owner config is preserved. Before installation, an existing controller SQLite database receives a consistent backup under the V1 productization backup directory. `1.0.0-rc.1` performs no database migration and does not rewrite canonical controller state.

## Rollback and recovery

`python3 <installed-app>/scripts/lac-v1 rollback` (normally invoked by the owner package on failure) restores the prior installed release pointer and owner configuration. Because V001 performs no database migration, rollback does not rewrite the canonical controller database. A preinstall database backup remains available for recovery inspection.

Restart never auto-dispatches D001 workflow continuation. The accepted explicit `/lac-resume <continuation_id>` behavior remains unchanged.

## Portable distribution

`scripts/lac-v1 build --output <archive>` builds a deterministic gzip/tar distribution from the exact staged Git index. File content comes from Git index objects, not mutable unstaged worktree bytes. Archive timestamps/owners are normalized; repeated builds from the same index are byte-identical.

## Release qualification

`scripts/test-v001` runs clean-install, upgrade/rollback, configuration, state-preservation and installed-wrapper acceptance, then runs the complete retained `scripts/test-pi003` chain. The owner package additionally runs the exact V001 lifecycle first in a disposable Git worktree at the expected preinstall commit before mutating the live repository.

## rc.2 default-governed entrypoint

`1.0.0-rc.2` changes the product default, not the authority core. The user-level `pi` command is owned by LAC and routes to the accepted governed profile. A pre-existing user-level `pi` file or symlink is backed up before takeover and restored exactly by rollback. The previous LAC install-state record is also backed up and restored byte-for-byte so an rc.2 rollback returns to the supported rc.1 product state.

The native Pi TUI is intentionally not claimed by PI004. PI005 is the separate security-qualified segment that will bind Pi's real TUI/session/resource loading to the same governed process boundary without granting extension/resource loading an alternate authority path.

## Default-governed Pi and shell precedence

`pi` and `lac-pi` both enter the LAC-governed launcher by default. `pi --dangerously-bypass-lac` is the explicit owner/debug escape hatch and verifies the pinned Pi checkout before bypass.

To prevent a tool-manager PATH entry from silently outranking `~/.local/bin/pi`, rc.2 installs a small shell function for the owner's Bash, Zsh, or Fish startup surface that invokes the LAC launcher by absolute path. PI004 does not modify or execute mise or another tool manager. The shell startup material and LAC shell fragment are part of the exact rollback set.

## rc.3 native governed Pi TUI

`1.0.0-rc.3` replaces the custom governed prompt loop with pinned Pi 0.85.1's native
source CLI/TUI. The Pi process still runs inside the accepted Bubblewrap network-none boundary.
The host workspace, owner admin socket, service credentials and host network are not mounted.
Stock Pi built-in tools are disabled; exactly one trusted LAC extension registers the four existing
controller-backed consequential tools and the LAC model broker. Extension discovery, skills, prompt
templates, themes, context files and session persistence are disabled by explicit CLI flags.
`--dangerously-bypass-lac` remains the explicit top-level owner/debug path and is not exposed to the
governed model.


## rc.4 PI006 restart-recovery stabilization

`1.0.0-rc.4` is a bounded PI006 stabilization of the native governed Pi TUI. It adds
owner-only, LAC-namespaced `/lac-continuations` and `/lac-resume <continuation_id>` commands
through the single trusted LAC extension so D001 restart recovery remains available after the
PI005 native-TUI transition. Startup continuation inspection is read-only and never dispatches.
Pi's built-in `/resume` session command is not intercepted. The model-facing consequential tool
surface remains exactly the existing four controller-backed tools; authority-core, policy,
approval, identity, credential, lease, receipt and sandbox semantics are unchanged.

## rc.5 PI006 installed administrator-wrapper forwarding stabilization

`1.0.0-rc.5` is a bounded PI006 owner-UAT stabilization. Owner UAT exposed that the
installed `lacctl` and `lac-owner` wrappers routed passthrough arguments through the outer
`lac-v1` argparse surface before delegation. Supported nested option forms such as
`lacctl --json pending list` and `lacctl permissions set --file <policy.json>` could
therefore be rejected before the accepted P005 client parsed them.

rc.5 delegates `ctl` and `owner` passthrough surfaces before outer argparse. The accepted
owner-only admin socket, peer-UID checks, P004/P005 protocol, canonical authority state,
permission and approval semantics, emergency pause, continuation semantics, sandbox, and
four-tool model effect surface are unchanged. Installed-wrapper acceptance now exercises
option-style forwarding without requiring an administrator socket.

## rc.6 PI006 administrator-socket collision stabilization

`1.0.0-rc.6` is a bounded PI006 owner-UAT stabilization. A second governed Pi launch while
an existing governed Pi administrator endpoint was active correctly failed closed, but the
contending `UnixAdminServer` instance could subsequently unlink the endpoint pathname even
though it never acquired that listener. The connect-and-close liveness probe could also cause
the active single-request server to encounter a disconnected peer while sending its error
response.

rc.6 binds socket cleanup to the exact device/inode identity acquired by that server instance
and treats expected peer disconnect errors as a non-authorizing completed connection. The
owner-only peer-UID boundary, authority semantics, policy, approvals, continuation behavior,
sandbox and four-tool model effect surface are unchanged.

## rc.7 PI006 interactive idle and permission-backlog stabilization

`1.0.0-rc.7` is a bounded PI006 owner-UAT stabilization. Owner UAT exposed that the
interactive native-Pi broker inherited a one-hour idle receive timeout intended as a
bounded host wait. If the governed Pi child remained healthy but produced no broker RPC
for 3,600 seconds, the host treated ordinary inactivity as a fatal timeout and tore down
the TUI.

rc.7 keeps deterministic probe mode bounded at 45 seconds but removes the idle deadline
from interactive broker service. The host continues polling the child process at bounded
intervals, so a real child exit is still detected promptly while owner or agent inactivity
does not terminate the governed TUI. The D001 workflow-continuation TTL remains 3,600
seconds: an unresolved synchronous workflow still expires fail-closed and cannot later be
revived. The separate P002/P006 pending-permission queue remains durable and has no TTL,
so an owner can review and configure a permission after hours or days; that late review
affects only future fresh requests and never revives the expired original request.

Authority-core semantics, policy/approval binding, emergency pause, idempotency, receipts,
sandboxing and the exact four-tool model effect surface are unchanged.

## rc.8 PI006 dangerous-bypass pinned-source stabilization

`1.0.0-rc.8` is a bounded PI006 owner-UAT stabilization. The explicit
`pi --dangerously-bypass-lac` owner/debug path still targeted the historical prebuilt
`packages/coding-agent/dist/bundle/cli.js` entrypoint even though PI005 moved the accepted
pinned Pi 0.85.1 runtime to the source CLI at `packages/coding-agent/src/cli.ts`. The
accepted pinned checkout does not require that historical bundle to exist, so the explicit
bypass could fail before Pi started.

rc.8 keeps the bypass explicit and ungoverned, verifies the accepted Pi pin first, then
launches the exact pinned source CLI through the checkout-local `tsx` runtime and root
TypeScript configuration. It rejects missing or symlinked source/config/package metadata,
rejects a coding-agent version other than 0.85.1, and requires the selected `tsx` runtime
to resolve inside the pinned checkout. Installed qualification now runs a real
`--dangerously-bypass-lac --help` smoke check against the accepted checkout.

The default `pi` path remains governed. Authority-core semantics, policy/approval binding,
emergency pause, continuation behavior, idempotency, receipts, sandboxing, and the exact
four-tool governed model surface are unchanged.

## rc.9 Phase 7 administrator-socket bind-race remediation

`1.0.0-rc.9` remediates the Phase 7 independent-review blocker
`P7-B001-ADMIN-SOCKET-BIND-RACE-UNLINK`. The rc.6 lifecycle already prevented an instance
that never acquired a listener from unlinking another endpoint during normal `close()`, but the
`UnixAdminServer.start()` exception path still unlinked the pathname unconditionally. If another
owner server bound the administrator socket after stale-path inspection and before a contender's
`bind()`, the losing contender could therefore remove the winning server's live pathname.

rc.9 records pathname device/inode ownership only after a successful `bind()` and permits
exception cleanup only when the current pathname still matches that acquired identity. A failed
`bind()` establishes no cleanup authority. Deterministic integration coverage synchronizes the
missing TOCTOU ordering, proves the winning socket pathname remains present, and proves the
winning server still accepts an authenticated owner administration request afterward. The existing
sequential collision regression is retained.

Owner UID checks, mode `0600`, runtime-directory validation, `SO_PEERCRED`, emergency pause,
policy and approval semantics, continuation behavior, idempotency, receipts, credential isolation,
sandboxing, ambient-resource restrictions, and the exact four-tool governed model surface are
unchanged.
