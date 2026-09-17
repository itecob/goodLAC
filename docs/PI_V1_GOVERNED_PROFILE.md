# LAC-Governed Pi v1 Profile

`scripts/lac-pi` is the explicit LAC-governed Pi v1 profile. It reuses the exact qualified
Pi Agent Core 0.85.1 checkout and accepted A004 Bubblewrap boundary, replacing A003/A004's
fixed-ALLOW effect bridge with the accepted Phase 4 capability, standing-permission,
exact-approval, dispatch, receipt and emergency semantics.

Ordinary standalone Pi remains separately runnable. A Pi process not started through
`scripts/lac-pi` is not represented as LAC-governed.

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

Profile startup idempotently registers the canonical `lac-pi-v1 / governed-local-effects`
manifest inside the trusted controller host process through the existing P004 `AdminService`
validation path, before the owner-only administrator socket begins serving requests.
Registration is descriptive and grants zero authority. The public P005 `lacctl` client
remains intentionally narrower and does not gain a `skills.register` operation.

A known but unconfigured first request returns terminal `DENY` plus a pending permission
item. The original request never resumes after configuration; issue a fresh tool request.

Use another owner terminal for administration:

```bash
scripts/lacctl pending list
scripts/lacctl pending show <pending_id>
scripts/lacctl approvals approve <decision_id>
scripts/lacctl approvals reject <decision_id>
```

For `REQUIRE_APPROVAL`, the host prints the exact decision and holds the current Pi tool
execution while polling the **same canonical request**. Approval creation itself does not
dispatch. On trusted retry, LAC re-evaluates current policy, validates the exact one-time
approval, then executes at most once. A current `DENY` still wins.

Visible outcomes distinguish successful execution/receipt, exact approval pending,
permission configuration required, explicit configured denial, and terminal effect
failure.

The deterministic gate is:

```bash
LAC_PI001_RUN_ROOT="$(mktemp -d)" scripts/test-pi001
```

It includes a real pinned-Pi process/tool probe through the production broker, plus the
accepted Phase 4 regression chain. Only local synthetic filesystem effects are used; no
production Gmail/Calendar credentials or external consequential effects are used.
