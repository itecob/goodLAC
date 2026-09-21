# LAC-Governed Pi v1 Profile

`scripts/lac-pi` is the LAC-governed Pi v1 profile used by the default installed `pi` command.
PI005 runs pinned Pi 0.85.1's native source CLI/TUI through the checkout-local TypeScript runtime with Pi's root tsconfig inside the accepted A004 Bubblewrap
boundary, loading exactly one explicit trusted LAC extension. The effect bridge remains the accepted Phase 4
capability, standing-permission, exact-approval, dispatch, receipt and emergency path; the TUI does
not become an authority boundary.

Upstream standalone Pi remains separately runnable only through the explicit top-level
`pi --dangerously-bypass-lac` owner/debug escape hatch (or direct owner execution outside the
LAC-managed command). A Pi process not started through the governed launcher is not represented
as LAC-governed.

## Start

```bash
scripts/lac-pi
```

Defaults:

```text
workspace: ~/.local/share/local-agent-controller/pi-v1-workspace
state:     ~/.local/state/local-agent-controller/pi-v1/controller.db
```

The model-facing consequential tool surface remains exactly `lac_fs_read`,
`lac_fs_create`, `lac_fs_replace`, and `lac_shell_exec`. Pi has no direct workspace mount,
service credential, owner runtime directory/admin socket, host network, or general host
process authority.

The native Pi process is launched through pinned `packages/coding-agent/src/cli.ts` using the
checkout-local `tsx` runtime and root `tsconfig.json`, with built-in tools disabled and an exact allowlist containing only the four LAC tools.
All ambient extension/resource discovery and session persistence are disabled; only the explicit
read-only `/lac/pi_native_tui.mjs` extension is loaded. Host-side model/effect RPC uses one owner-private Unix-domain broker socket created inside the
private Bubblewrap runtime root before launch. The socket survives the checkout-local `tsx` process
boundary without exposing the owner admin socket or host filesystem, so native Pi UI/resource features
cannot create a second host effect path.

Profile startup idempotently registers the canonical `lac-pi-v1 / governed-local-effects`
manifest inside the trusted controller host process through the existing P004 `AdminService`
validation path, before the owner-only administrator socket begins serving requests.
Registration is descriptive and grants zero authority. The public P005 `lacctl` client
remains intentionally narrower and does not gain a `skills.register` operation.

## Permission-gated workflow continuation

A known but unconfigured first request is still terminally `DENY`. Its canonical request
identity is never revived. D001 adds a bounded, non-authoritative continuation record that
captures the immutable effect intent and the pending-permission identity after that terminal
denial.

While the owner is configuring the permission, the trusted Pi host keeps the synchronous
effect RPC blocked. The denied result is not returned to the Pi worker, so the model cannot
continue the turn, retry the effect, mutate it, or improvise an alternate consequential route
while the owner decision is outstanding.

Owner configuration remains out-of-band through the authenticated administration surface:

```bash
scripts/lacctl pending list
scripts/lacctl pending show <pending_id>
scripts/lacctl permissions set <policy-json-file>
scripts/lacctl pending resolve <pending_id> POLICY_UPDATED
# or explicitly:
scripts/lacctl pending resolve <pending_id> NO_CHANGE
scripts/lacctl pending dismiss <pending_id>
```

After an authorizing administrative disposition (`POLICY_UPDATED`, `CAPABILITY_UPDATED`, or
`POLICY_AND_CAPABILITY_UPDATED`), the host may allocate exactly one fresh request identity
from the captured immutable intent. That fresh request traverses the ordinary Phase 4
`ExternalConsumerRuntime`; capability validation, current policy, emergency state, exact
approval, lease, sandbox, receipt and idempotency checks are all performed again. The owner
administrative disposition is not authority and does not imply `ALLOW`.

If current policy returns `REQUIRE_APPROVAL`, the fresh request remains the exact approval
subject and is not replaced by another continuation request. If current policy denies,
`NO_CHANGE` is selected, or the pending item is dismissed, no effect occurs. A fresh request
that encounters another configuration-required denial does not recursively create another
automatic continuation; the one-shot continuation budget is exhausted and the workflow ends
non-authorizing. If the fresh request is blocked by the durable emergency pause, the Pi edge
returns explicit `DENY / DENIED / EMERGENCY_PAUSED`; lifting the pause does not retry that
continuation because its one-shot fresh-request budget has already been consumed.

Security-relevant mutation of the original tool name, arguments, resource, run identity,
request identity or idempotency binding invalidates same-process continuation. Equivalent
pending-permission aggregation never merges distinct continuation identities. Each continuation
also records the pending item's resolution revision at capture time, so an old resolution from a
prior equivalent request cannot authorize a later blocked workflow.

## Restart recovery

Continuation state is durable in the controller database. The native Pi TUI startup path
checks only for recoverable continuation metadata and never dispatches an effect. When blocked
work exists, the trusted LAC extension shows an owner-visible notice. Recovery requires an
explicit owner event through LAC-namespaced native TUI commands:

```text
/lac-continuations
/lac-resume <continuation_id>
```

Pi's built-in `/resume` command remains untouched for Pi session navigation. `/lac-resume` uses
the stored immutable intent and can consume the one-shot fresh-request budget. If the fresh
request requires exact approval, approval alone does not dispatch; the owner must invoke
`/lac-resume <continuation_id>` again after the approval decision. This recovery completes the
captured effect workflow; it does not treat restart or approval as authority and does not
reconstruct a lost model transcript.

## Exact approval

For ordinary `REQUIRE_APPROVAL`, and for a fresh D001 continuation request that evaluates to
`REQUIRE_APPROVAL`, the host prints the exact decision and holds the current Pi tool execution
while polling the **same canonical request**. Approval creation itself does not dispatch. On
trusted retry, LAC re-evaluates current policy, validates the exact one-time approval, then
executes at most once. A current `DENY` still wins.

Visible outcomes distinguish successful execution/receipt, exact approval pending,
permission configuration wait, explicit configured denial/non-authorization, expiration,
and terminal effect failure.

The D001 deterministic gate is:

```bash
LAC_PI002_D001_RUN_ROOT="$(mktemp -d)" scripts/test-pi002-d001
```

It includes direct continuation acceptance coverage, a real pinned-Pi process/tool probe,
and the complete retained `scripts/test-pi001` gate, which in turn includes the accepted
Phase 4 regression chain. Only local synthetic filesystem effects are used; no production
Gmail/Calendar credentials or external consequential effects are used.


## PI003 native-contract conformance

The Pi v1 edge now translates Pi tool calls into the stabilized native local-consumer request
and delegates result/permission-continuation behavior to `NativeLocalConsumerRuntime`. The
accepted `ExternalConsumerRuntime` remains the authority path underneath it; Pi does not own
policy, approval, identity, continuation authorization, lease, credential or dispatch logic.
A separate stdlib-only fixture proves the same native contract without becoming an additional
harness integration. `scripts/test-pi003` runs that conformance plus the complete retained D001,
PI001 and accepted Phase 4 regression chain.
