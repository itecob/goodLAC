# ACTIVE TASK — LAC-A004-REMEDIATION

## Objective

Remediate only the two concrete defects observed during hands-on A004 owner UAT, preserve the accepted Phase 3 authority boundary, rerun deterministic A004 regression, and return the project to owner A004 UAT.

## Blocking findings

### A004-UAT-B001 — interactive terminal input robustness

During owner UAT, ordinary terminal left-arrow editing produced raw escape characters (`ESC [ D`) in the submitted prompt. The prompt reached the model path and the Pi session terminated with:

`Bad escaped character in JSON ...`

The interactive owner terminal must not allow ordinary line-editing/control sequences to reach the model in a form that can crash the session. Basic arrow-key editing must be usable, and residual terminal control characters must fail safely without terminating the A004 session.

### A004-UAT-B002 — shell argv model-facing contract ambiguity

The accepted H003 shell adapter defines `argv` as argument strings **excluding argv[0]**. A004's model-facing tool description/system prompt does not make this explicit. During owner UAT the model proposed:

`executable='/usr/bin/ls' argv=['/usr/bin/ls'] cwd='.'`

The governed effect correctly succeeded as the literal command `ls /usr/bin/ls`, so the assistant incorrectly reported `/usr/bin/ls` instead of listing the bounded workspace. The A004 model-facing contract must make the shell argument semantics unambiguous and deterministic enough for the baseline `/usr/bin/ls` UAT request to inspect the workspace correctly.

## In scope

- `scripts/a004_terminal.py` terminal input handling and only the smallest supporting code/tests required for B001.
- A004 model-facing shell tool descriptions/system prompt and only the smallest supporting code/tests required for B002.
- Deterministic regression tests that specifically cover both defects.
- Full applicable A004 regression gate after remediation.
- Owner-executable remediation package that returns durable state to `LAC-A004-UAT` and installs a fresh owner-UAT successor prompt.

## Out of scope

- Gmail, Calendar, Chief of Staff, Phase 4 adapters, credentials, production accounts.
- New authority semantics, new effect types, new shell executables, sandbox redesign, runtime/model replacement, web UI, voice UI, or memory architecture.
- Reopening the accepted Phase 3 independent review absent material regression evidence.
- Adding general host hardware introspection or diagnostics capability.

## Acceptance tests

1. Ordinary left/right arrow line editing no longer injects raw terminal escape sequences that can crash the Pi/model path.
2. Any residual disallowed terminal control characters are handled safely without terminating the A004 interactive session or dispatching a malformed request.
3. The A004 model-facing shell contract explicitly states that `argv` contains only arguments after the executable and excludes `argv[0]`.
4. The baseline `/usr/bin/ls` workspace-inspection request is represented with `executable='/usr/bin/ls'`, `argv=[]`, `cwd='.'`, and produces the actual workspace listing.
5. Existing filesystem create/read/replace, shell allowlist enforcement, boundary denial, receipt behavior, hidden-reasoning suppression, credential isolation, sandbox/network constraints, startup/shutdown, and A003/A002/A001/H001-H004 regression remain PASS.
6. Full `scripts/test-a004` applicable gate passes.
7. Durable state returns to `LAC-A004-UAT`; `LAC-B001` remains deferred until explicit owner acceptance.

## Package required?

Yes. The remediation implementation session must produce one owner-executable package and stop at `OWNER_EXECUTION_REQUIRED`.

## Next task on remediation success

`LAC-A004-UAT` — repeat owner hands-on validation. Do not activate or implement `LAC-B001` until owner UAT explicitly passes.
