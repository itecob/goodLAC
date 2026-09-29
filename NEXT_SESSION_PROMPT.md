# NEXT SESSION PROMPT — goodLAC / R5-R003 OWNER UAT

Use the connected Web-File-Tool. Work against the live root labeled `Local Agent Controller`; the
local repository directory remains `local-agent-controller`. Do not assume the local folder is named
goodLAC. Prefer `git rev-parse --show-toplevel`.

R5 remains ACTIVE. R6 remains INACTIVE. `1.0.0-rc.11` remains the last accepted baseline.
`1.0.0-rc.12` is NOT accepted.

The prior owner-permission semantics remediation at
`485c431c52c8cf918423aeac6458dc5870141849` passed retained automated regression and owner UAT.

R5-R003 adds:
1. standing `shell.exec` owner scopes: exact command, executable, or all shell in the governed project;
2. exact-command scope bound to canonical command arguments, not only executable/cwd;
3. native Pi model registration for GPT-OSS 20B and the bounded Qwen3.6 35B A3B NVFP4 comparison route;
4. model routing remains non-authoritative and cannot alter the four governed tools or controller policy.

First verify the live repository is clean, read `PROJECT_STATE.json`, this prompt, and the newest
commit, and verify the installed development snapshot points at that exact commit.

Then run the R5-R003 owner UAT in `tasks/ACTIVE_TASK.md`. Use `/model` in Pi to switch models.
The GPT route is `lac-a003-gpt-oss-20b` at `http://127.0.0.1:19203`. The Qwen comparison route is
`goodlac-exp-qwen36-35b-a3b-nvfp4` at `http://127.0.0.1:19360`; it must already be running to serve
Qwen requests.

If UAT fails, keep R5 active and remediate only the narrow defect. If it passes, preserve evidence
and finish the remaining R5 qualification/model-comparison evidence. Do not activate R6 or accept
rc.12 until R5 is explicitly closed and a fresh R6 review is authorized.
