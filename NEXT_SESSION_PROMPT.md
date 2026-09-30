# NEXT SESSION PROMPT — goodLAC / R5 QUALIFICATION + MODEL-COMPARISON CLOSEOUT

Use the connected Web-File-Tool. Work against the live root labeled `Local Agent Controller`; the
local repository directory remains `local-agent-controller` (normally `${HOME}/local-agent-controller`).
goodLAC is the product/GitHub brand, not the local folder name. Prefer `git rev-parse --show-toplevel`
for owner-host commands.

R5 remains ACTIVE. R6 remains INACTIVE. `1.0.0-rc.11` remains the last accepted baseline.
`1.0.0-rc.12` is NOT accepted.

Start by reading:
- `PROJECT_STATE.json`
- `tasks/ACTIVE_TASK.md`
- `docs/POST_V1_REMEDIATION_ROADMAP.md`
- `docs/R5_R003_SHELL_SCOPE_MODEL_SELECTOR.md`
- `docs/R5_R003_OWNER_UAT_EVIDENCE.md`
- the newest commit

Verify the live repository is clean and on `main`.

Important runtime boundary:
- R5-R003 implementation/runtime commit is `996c1629f9d560c64e04a9102df9cd713aae29f3`.
- The installed development snapshot intentionally remains
  `~/.local/share/local-agent-controller/releases/r5-996c1629f9d560c64e04a9102df9cd713aae29f3`.
- The newest repository commit after the closeout package is documentation/workflow-state only, so
  do NOT treat the installed runtime pointing at `996c162...` as drift or reinstall it merely to
  match the closeout commit.

R5-R003 is COMPLETE:
- retained qualification passed;
- shell standing-scope semantics are covered deterministically for exact command, executable, and
  all-shell/project resource scope;
- installed Pi `/model` exposed both GPT-OSS and Qwen routes;
- harmless governed shell execution succeeded under both models;
- owner selected `Allow Once` for both live executions, producing fresh authorization paths;
- GPT-OSS 20B showed a model-behavior issue: on an ordinary repeated explicit user instruction it
  incorrectly treated the turn as an automatic retry and declined to issue a tool call; when the
  user explicitly stated that the turn was a new request, GPT-OSS issued the governed tool call and
  completed successfully after a fresh `Allow Once`;
- Qwen did not show that retry/replay misinterpretation under the equivalent ordinary prompt;
- this is model-comparison evidence, not a controller authority defect. Do not weaken goodLAC to
  compensate for model behavior.

The active task is now the remaining R5 qualification/model-comparison closeout. Inspect the live
roadmap/state and existing evidence to determine the smallest remaining R5 sequence. Preserve prior
accepted evidence and do not reopen `1.0.0-rc.11`.

If remaining R5 qualification is fully satisfied, prepare the exact R5 closeout/review-candidate
evidence and owner command/package needed to close R5. Do NOT activate R6 or accept rc.12 merely
because R5 evidence appears complete; R6 starts only after R5 is explicitly closed and the owner
authorizes the fresh independent review.

If a concrete R5 blocker is found, keep R5 active and remediate only that narrow blocker.
