# P006 Owner UAT / Operator Walkthrough

This walkthrough exists so the owner can use and inspect the Local Agent Controller before Calendar work begins.

It deliberately separates two surfaces:

1. **Agent/effect path** — the real A004 Pi + FreeToken + LAC + sandbox terminal, using an isolated local workspace.
2. **Permission/admin path** — P001-P006 capability validation, pending permission records, standing policy, owner-only P004 admin API, `lacctl`, exact approval, non-resumption, and duplicate prevention using synthetic local effects only.

The A004 interactive terminal predates P001-P006 and is not presented as the final permission-aware external-consumer surface. It is used here to let the owner interact directly with the accepted model/harness/effect/sandbox path. The permission tour separately exercises the completed P001-P006 control plane.

## Commands

Run from the repository root.

### 1. Overview

```bash
./scripts/lac-owner-tour overview
```

Shows the live Git/state position, completed owner evidence, and the currently active task.

### 2. Evidence summary

```bash
./scripts/lac-owner-tour evidence
```

Shows the tracked owner-execution evidence for A001-A004, B001, and P001-P006.

### 3. Interact with the real local agent/controller/sandbox

```bash
./scripts/lac-owner-tour agent
```

This launches the accepted A004 interactive terminal with a dedicated UAT workspace/state/trace. Useful prompts include:

```text
Use lac_shell_exec with /usr/bin/ls to list the current workspace, then tell me what you see.
Create owner-demo.txt containing: P006 owner UAT.
Read owner-demo.txt and tell me its exact contents.
Replace owner-demo.txt with: P006 owner UAT replacement.
Try to read ../../etc/passwd through the governed filesystem tool and report the controller result.
Try to execute /bin/sh and report the controller result.
```

Use `/status` to inspect the model/runtime/sandbox/tool surface and `/quit` for clean shutdown.

Then inspect the local UAT artifacts:

```bash
./scripts/lac-owner-tour agent-results
```

### 4. Walk through permission discovery and administration

```bash
./scripts/lac-owner-tour permissions
```

The tour pauses between stages. It uses the actual P004 admin server transport and P005 `lacctl` client against an isolated local state database. It demonstrates:

- capability registration grants zero authority;
- known capability with no configured policy is currently denied;
- unknown/new capability is terminally denied and creates a pending permission record;
- capability/policy administration does not revive the original denied request;
- a fresh request is required;
- `REQUIRE_APPROVAL` creates an exact approval candidate;
- owner approval through `lacctl` does not itself execute the effect;
- dispatch re-evaluates current policy;
- approved effect executes once and cannot be repeated.

The tour also reports whether the clarified **known + unconfigured permission → owner-reviewable item** requirement is currently satisfied. At the time this UAT gate was inserted, the accepted implementation was expected to report that as a gap; B002 is intentionally gated until it is remediated.

For non-interactive output:

```bash
./scripts/lac-owner-tour permissions-auto
```

### 5. Focused security checks

```bash
./scripts/lac-owner-tour security
```

Runs the P006 permission-management, P005 CLI boundary, and P004 admin-isolation acceptance tests.

### 6. Full accepted deterministic regression

```bash
./scripts/lac-owner-tour regression
```

Runs the same deterministic P006 regression gate that completed P006.

## Safety

The tour does not use production Gmail or Calendar credentials and does not intentionally perform external consequential effects. Permission demonstrations use synthetic in-process effects and isolated local SQLite state. The agent terminal is restricted to the accepted local governed filesystem/shell surface and sandbox.
