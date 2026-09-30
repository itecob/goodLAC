# R5-R003 Owner UAT Evidence — Shell Scope / Governed Model Selection

Date: 2026-09-29

## Boundaries

- R5 remained active throughout this UAT.
- R6 remained inactive.
- `1.0.0-rc.11` remained the accepted historical baseline.
- `1.0.0-rc.12` remained unaccepted.
- R5-R003 implementation/runtime commit:
  `996c1629f9d560c64e04a9102df9cd713aae29f3`.
- Installed development snapshot:
  `${HOME}/.local/share/local-agent-controller/releases/r5-996c1629f9d560c64e04a9102df9cd713aae29f3`.

## Deterministic qualification

The R5-R003 qualification runner passed and retained the prior regression chain.

New R5-R003 acceptance coverage passed for exact shell-command standing scope, executable standing
scope, all-shell/project resource scope, exact-request-only one-time owner choices, bounded
GPT-OSS/Qwen registration, and unknown-model fail-closed behavior.

## Installed model-selection UAT

Ordinary installed governed `pi` reported both configured model routes under `lac-freetoken`, with
Bubblewrap, network none, and the same four model-facing tools:
`lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.

## Live governed execution

Under Qwen, `/usr/bin/ls -la` in cwd `.` completed through `lac_shell_exec` after the owner selected
`Allow Once`, with authority outcome `ALLOW`, execution state `SUCCEEDED`, and a durable receipt.

After switching to GPT-OSS, the ordinary repeated explicit user instruction was incorrectly
interpreted by the model as an automatic retry, so the model declined to issue a tool call. The
controller did not deny this because no tool request reached it. After the user explicitly stated
that this was a new request and not an automatic retry/replay, GPT-OSS issued the same governed
shell request. The owner again selected `Allow Once`; the request completed successfully through a
distinct fresh request/approval/receipt path.

## Finding

`GPT-OSS 20B retry/replay interpretation`: GPT-OSS may conflate an ordinary new user turn that
repeats a previously completed governed operation with an automatic retry. Explicit fresh-request
wording corrected the behavior. Qwen did not exhibit this behavior under the equivalent ordinary
prompt.

This is model-comparison evidence. It is not a goodLAC authority, replay, idempotency, permission
persistence, or model-routing failure. The controller must not be weakened to compensate for this
model behavior.

## Owner-UAT disposition

R5-R003 owner UAT: `PASS`.

Standing-scope semantics are accepted from deterministic qualification rather than creating
unnecessary persistent live policies solely to duplicate already-passed coverage.

R5-R003 is complete. R5 remains active for the remaining qualification/model-comparison closeout.
R6 remains inactive and `1.0.0-rc.12` remains unaccepted.
