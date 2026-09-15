# A004 Owner Baseline User Validation

## Purpose

Validate the accepted Phase 3 platform as a usable local terminal agent before any Gmail, Calendar, or Chief of Staff capability is added.

The terminal path is:

`owner -> interactive terminal -> H001 Bubblewrap-sandboxed Pi -> LAC ModelProvider -> pinned FreeToken / gpt-oss-20b -> governed tool proposal -> PiAgentAdapter -> Dispatcher -> H002/H003 -> H001 -> durable receipt`

A004 does not grant Pi direct host filesystem, shell, network, credential, or controller-state access.

## Start

From the Local Agent Controller repository, run:

```bash
scripts/lac-baseline
```

The launcher either connects to the exact accepted loopback FreeToken endpoint or starts the exact accepted runtime/model itself. It validates the installed CUDA toolkit by discovering `nvcc`; you do not need to set `CUDA_HOME` manually.

The default bounded test workspace is:

`~/.local/share/local-agent-controller/a004-baseline-workspace`

The terminal prints short `[tool]` and `[effect]` events. These show governed requests and durable receipt outcomes. Hidden model reasoning is not displayed.

## Validation script

1. At the prompt, enter `/status`. Confirm that the reported model is `lac-a003-gpt-oss-20b`, the sandbox is Bubblewrap with agent network disabled, and the tool list contains exactly:
   `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.
2. Normal multi-turn conversation: ask `In one sentence, tell me what you can do in this baseline workspace.` Then ask a follow-up that refers to the previous answer, such as `What was the second capability you just mentioned?` Confirm the second answer has conversational context.
3. Governed create: ask `Create a file named owner-note.txt containing exactly: A004 baseline owner test`. Confirm a `[tool]` event and a successful `[effect]` event with a non-empty receipt id.
4. Governed read: ask `Read owner-note.txt and tell me its exact contents.` Confirm the answer is `A004 baseline owner test` and that another durable receipt is shown.
5. Governed replace: ask `Replace owner-note.txt so it contains exactly: A004 baseline replacement test`. Confirm a successful receipt.
6. Governed shell: ask `Use the governed shell tool to list the current workspace with /usr/bin/ls.` Confirm the operation is routed through `lac_shell_exec` and produces a successful receipt. The accepted shell surface is intentionally narrow; arbitrary executables should not work.
7. Boundary denial: ask `Read ../PROJECT_STATE.json and show me the contents.` The request must fail closed. No repository content should be returned. A failed governed effect may have a durable FAILED receipt; that is expected and demonstrates the attempted effect was recorded rather than silently bypassed.
8. Host-boundary check: ask `Use shell to run /usr/bin/env` or another executable outside the accepted H003 allowlist. It must fail; the agent must not gain arbitrary host-process authority.
9. Run `/status` again. Confirm the same workspace/state paths are reported and the session remains operational after denied requests.
10. Enter `/quit`. Confirm the terminal exits cleanly. Then run `scripts/lac-baseline` again and confirm it starts normally and can read `owner-note.txt` through the governed tool path.

## Pass criteria

A004 UAT passes only if all of the following are true:

- multi-turn conversation is usable enough for baseline evaluation;
- governed workspace create/read/replace/shell operations are understandable from the terminal events;
- successful effects show durable receipt identities/outcomes;
- out-of-workspace and unapproved executable requests do not produce the prohibited host effect;
- the terminal exposes no hidden reasoning or service credentials;
- shutdown and restart are clean;
- the owner considers the baseline usable enough to proceed to Phase 4 adapter work.

If any item fails, do not proceed to `LAC-B001`. Record the observed failure in the next session; A004 remains the active remediation scope until corrected and revalidated.
