# R5-R003 — Shell Permission Scope and Governed Model Selection

R5 remains active. R6 remains inactive. `1.0.0-rc.11` remains the accepted historical baseline;
`1.0.0-rc.12` remains unaccepted.

## Shell standing-permission scope

One-time decisions remain exact-request-only.

For `shell.exec`, standing owner choices now support:

- `SHELL_COMMAND`: exact canonical command arguments, including executable, argv, cwd, and environment.
- `SHELL_EXECUTABLE`: the same canonical executable within the existing project/action/resource scope.
- `RESOURCE`: all governed shell requests within the existing project shell resource.

Exact-command binding uses a deterministic controller-derived canonical arguments hash plus the
canonical executable. The model cannot supply or mutate the selected permission scope.

Filesystem standing permission behavior is unchanged.

## Governed model selection

The trusted Pi provider registers two owner-host allowlisted model routes:

- `lac-a003-gpt-oss-20b` -> accepted GPT-OSS 20B FreeToken endpoint `http://127.0.0.1:19203`.
- `goodlac-exp-qwen36-35b-a3b-nvfp4` -> experimental Qwen3.6 35B A3B NVFP4 FreeToken endpoint
  `http://127.0.0.1:19360`.

Pi's native `/model` / Ctrl+L model selector switches between registered models. Model selection
changes only the model-provider route. It does not change controller state, policy, approvals,
sandboxing, the four-tool model effect surface, or dispatch authority.

The Qwen endpoint remains experimental model-comparison infrastructure and is not evidence that
`1.0.0-rc.12` is accepted.

## Owner UAT closeout

Owner UAT passed on 2026-09-29 against implementation/runtime commit
`996c1629f9d560c64e04a9102df9cd713aae29f3`.

The installed Pi model selector exposed both governed model routes and harmless governed shell
execution succeeded under both models with separate `Allow Once` owner decisions. GPT-OSS exhibited
a model-side retry/replay interpretation weakness on an ordinary repeated explicit user request;
explicit fresh-request wording corrected it. Qwen did not exhibit that behavior under the
equivalent ordinary prompt. No controller authority failure was observed.

Standing shell-scope semantics are accepted from deterministic R5-R003 qualification rather than
creating persistent live policies solely to duplicate that coverage.

R5-R003 status: `COMPLETE`.

R5 remains active. R6 remains inactive. `1.0.0-rc.12` remains unaccepted.
