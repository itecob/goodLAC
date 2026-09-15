# Contracts

## Canonical effect lifecycle

`PROPOSED -> EVALUATING -> {DENIED | PENDING_APPROVAL | AUTHORIZED}`

`PENDING_APPROVAL -> {REJECTED | APPROVED}`

`APPROVED -> AUTHORIZED` only after current-policy re-evaluation.

`AUTHORIZED -> LEASED -> EXECUTING -> {SUCCEEDED | FAILED}`

Additional terminal states: `CANCELLED`, `EXPIRED`, `REVOKED`.

## Effect request

Versioned `lac.effect-request/v1` with request/run/principal/agent identity, action, resource, typed arguments, idempotency key, timestamps, expiry, and canonical SHA-256.

## Policy decision

Versioned `lac.policy-decision/v1` bound to request ID and canonical request hash, with policy revision and deterministic reason codes.

## Approval

Versioned `lac.approval/v1`, bound to the exact canonical request hash and approver. `ONCE` is the initial scope; expiry and consumption are durable.

## Receipt

Versioned `lac.effect-receipt/v1`, bound to request, adapter, input hash, outcome, result hash, timing, and upstream reference where applicable.

## Execution lease

Short-lived, transactional single-machine ownership record keyed by request to prevent concurrent duplicate dispatch and support crash reconciliation.

## H002 filesystem effect contract

The first governed workspace uses adapter `filesystem:v1` and one explicitly configured resource/root, normally `filesystem:workspace`. Paths are canonical relative POSIX paths; absolute paths, traversal, non-canonical aliases, control characters, and symlink traversal fail closed.

Typed actions are:

- `filesystem.read` with exactly `{path}` — read an existing UTF-8 regular file; the workspace is mounted read-only for the effect.
- `filesystem.create` with exactly `{path, content}` — create an absent UTF-8 text file beneath an existing real directory.
- `filesystem.replace` with exactly `{path, content}` — replace an existing UTF-8 regular non-symlink file. Policy can therefore require approval for overwrite independently of create.
- `filesystem.delete` with exactly `{path}` — recognized for deterministic policy denial, but H002 provides no deletion mutation implementation.

Read/create/replace execute through the H001-selected qualified `SandboxBackend`. The sandbox exposes only the configured workspace plus the fixed helper runtime/input required for the operation, with `network=none`, cleared environment, and no arbitrary host filesystem visibility. Mutating PREPARED executions are not guessed during reconciliation; only read reconciliation may be safely repeated.

## H003 shell effect contract

The first governed shell surface uses adapter `shell:v1`, action `shell.exec`, and one explicitly configured resource/root, normally `shell:workspace`. The request arguments are exactly:

```json
{
  "executable": "/absolute/canonical/executable",
  "argv": ["argument-1", "argument-2"],
  "cwd": ".",
  "environment": {"EXPLICIT_ALLOWED_NAME": "request-bound-value"}
}
```

`argv` excludes `argv[0]`. LAC invokes the selected executable directly as `[executable, *argv]`; H003 does not accept a shell command string, invoke `shell=True`, split a command string, or perform wildcard, variable, redirection, command-substitution, pipeline, or other shell expansion. Characters with shell meaning remain ordinary argument bytes when accepted by the target executable.

The adapter constructor supplies the exact executable allowlist, but H004 makes that configuration narrowing-only: an executable must also be a member of the reviewed non-launching leaf-command set at its canonical `/usr/bin/<name>` path. Executables must be canonical existing regular executable files and cannot be symlinks. Shells, general-purpose language interpreters, privilege-escalation tools, namespace/chroot/mount tools, command-launching multiplexers/wrappers, dynamic loaders, arbitrary custom binaries, and other unreviewed executable classes are rejected even if proposed for the allowlist. Expanding the generic shell executable class requires a code-reviewed classification and regression tests; runtime/user configuration cannot broaden it. Unsupported executables fail before host execution.

`cwd` is `.` or one canonical relative POSIX directory beneath the configured working root. Absolute paths, parent traversal, aliases, missing directories, and symlink traversal fail closed. The workspace is the only host project mount exposed to the command and is mounted at `/workspace`.

The sandbox environment is constructed deterministically. Bubblewrap clears the inherited process environment. H003 then supplies fixed non-secret runtime values (`HOME=/nonexistent`, `LC_ALL=C`, `PATH=/usr/bin`) plus only request environment names explicitly allowlisted by the adapter. Reserved runtime names and credential-shaped names are not request-settable. Shell receipts record environment key names but do not echo request environment values.

Execution uses the H001-selected qualified `SandboxBackend`, a minimal per-effect runtime containing only the exact executable and its required dynamic libraries, `network=none`, isolated process/network namespaces, dropped capabilities, and bounded execution time. The command cannot obtain ambient host filesystem, process, network, or credential authority from the adapter.

A generic shell effect can mutate workspace state. Therefore an ambiguous `PREPARED` shell execution is not automatically re-run or guessed during reconciliation; it remains fail-closed for explicit reconciliation rather than risking a duplicated consequential effect.


## Phase 4 capability and permission contracts

### Capability manifest

A versioned canonical capability/skill manifest describes application/skill identity, manifest version, declared actions, resource types/selectors, bounded argument schemas, and deterministic security properties. Registration is descriptive only and grants zero authority.

Capability security properties are controller/manifest metadata, never model-generated authorization judgments.

### Pending permission request

Unknown/new action, resource scope, unsupported capability version, or material argument shape terminates the current effect as `DENY`. A bounded durable pending-permission record may then be created for administrator review. The pending record is not executable authority and cannot resume the closed effect.

Equivalent repeats aggregate with bounded first/last-seen/count metadata. Credential material is prohibited from pending-permission records.

### Standing permission policy

Standing policy may scope rules by principal, application/agent, skill, action, resource selector, and deterministic conditions. Final authority outcomes remain `ALLOW`, `REQUIRE_APPROVAL`, or `DENY`; UI label `ASK` maps to `REQUIRE_APPROVAL`.

Non-overridable invariants are evaluated first. Registered capability/resource validity is required. For standing-policy v1, rule specificity is the number of constrained scope dimensions plus the number of matched deterministic conditions. The highest-specificity matching rule set wins; equal-specificity conflict resolves `DENY > REQUIRE_APPROVAL > ALLOW`. Configured application/skill default follows only when no rule matches; absence of a matching fallback is `DENY`.

### Administrative mutation contract

Capability registration and standing-policy mutation are unavailable through the runtime agent interface. For Linux v0.1 they are accepted only through the isolated local administration surface, authenticated using controller-observed OS peer identity and protected from governed agent sandboxes.

Every registry/policy mutation is atomic, revisioned, and audited. A policy mutation never changes or revives a terminal effect request.

### External consumer contract

Chief of Staff and other products are external consumers. They may register/declare capabilities through the generic controller contract and submit runtime requests, but they do not own canonical policy, approval, credentials, leases, receipts, or administration state.
