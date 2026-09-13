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

The adapter constructor supplies the exact executable allowlist. Executables must be canonical existing regular executable files and cannot be symlinks. Shells, general-purpose language interpreters, privilege-escalation tools, namespace/chroot/mount tools, and command-launching multiplexers are rejected even if proposed for the allowlist. Unsupported executables fail before host execution.

`cwd` is `.` or one canonical relative POSIX directory beneath the configured working root. Absolute paths, parent traversal, aliases, missing directories, and symlink traversal fail closed. The workspace is the only host project mount exposed to the command and is mounted at `/workspace`.

The sandbox environment is constructed deterministically. Bubblewrap clears the inherited process environment. H003 then supplies fixed non-secret runtime values (`HOME=/nonexistent`, `LC_ALL=C`, `PATH=/usr/bin`) plus only request environment names explicitly allowlisted by the adapter. Reserved runtime names and credential-shaped names are not request-settable. Shell receipts record environment key names but do not echo request environment values.

Execution uses the H001-selected qualified `SandboxBackend`, a minimal per-effect runtime containing only the exact executable and its required dynamic libraries, `network=none`, isolated process/network namespaces, dropped capabilities, and bounded execution time. The command cannot obtain ambient host filesystem, process, network, or credential authority from the adapter.

A generic shell effect can mutate workspace state. Therefore an ambiguous `PREPARED` shell execution is not automatically re-run or guessed during reconciliation; it remains fail-closed for explicit reconciliation rather than risking a duplicated consequential effect.
