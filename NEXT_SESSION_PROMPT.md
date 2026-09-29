# NEXT SESSION PROMPT — goodLAC / R5 OWNER PERMISSION SEMANTICS UAT

Use the connected Web-File-Tool. Work against the live root labeled `Local Agent Controller`; the local repository directory remains `local-agent-controller` (normally `${HOME}/local-agent-controller`). Do not assume the local folder is named goodLAC. Prefer `git rev-parse --show-toplevel`.

This handoff follows the bounded R5 owner-permission semantics remediation. R5 remains ACTIVE. R6 remains INACTIVE. `1.0.0-rc.11` remains the last accepted baseline. `1.0.0-rc.12` is NOT accepted. Do not reopen accepted historical work absent current evidence.

First verify the live repository is clean and read `PROJECT_STATE.json`, this prompt, and the newest commit. Confirm the development snapshot installed by the owner points at that exact commit.

The remediation intent is:
1. `ALLOW_ONCE` is exact-request-only in observable standing policy semantics: after normal completion no standing rule remains and the next matching request returns to the five-choice first-use gate. Internally its temporary REQUIRE_APPROVAL rule is conditioned on the deterministic fresh request_id, so a crash cannot broaden authority to another request.
2. `DENY_ONCE` remains exact-only and non-standing.
3. An explicit `ASK_EVERY_TIME` standing rule produces an exact-approval gate with three choices: allow this request once, deny this request once, or `Change default permission…`. Choosing change default opens the five standard choices and permits reassignment, including Always allow / Ask every time / Always deny and returning to no standing default through Allow once / Deny once after the current decision.
4. Escape cancellation remains non-authorizing; owner previously confirmed Escape dismisses the menu. Ctrl+C may still be independently tested; Ctrl+D is not the advertised cancel mechanism.
5. `lac_shell_exec` model-facing contract explicitly requires a canonical absolute reviewed `/usr/bin/...` executable, workspace-relative cwd (`.` for root), argv excluding argv[0], and `{}` environment in the current profile.
6. Model-facing behavior says controller/tool/approval/continuation results are not user turns and terminal DENIED/REJECTED/FAILED effects are not automatically retried unless the original user turn explicitly requested multiple attempts.

Owner UAT to verify or continue:
- Reset only the standard testing standing policy if needed.
- Launch plain `pi` and verify it reports the development snapshot/current governed runtime.
- First-use harmless shell request should show the five-choice gate.
- Choose Allow once: the exact current request may run, then `lacctl permissions list` should show no standing rule for that action; a later explicit user turn requesting the same class must show the five-choice gate again.
- Choose Ask every time on a fresh first-use request: the current/future exact approval gate must show Allow once / Deny once / Change default permission. Select Change default permission and verify the five choices appear. Exercise at least one reassignment to Always deny or Always allow and verify subsequent behavior matches.
- Verify a directory listing request causes the model to propose `/usr/bin/ls` with cwd `.` rather than bare `ls` and `/workspace`; if the model still violates the published tool contract, preserve it as model-behavior evidence rather than weakening controller validation.
- Verify Escape cancels without authorization or standing-policy mutation.

If deterministic tests or owner UAT fail, keep R5 active and remediate the narrow defect only. Do not activate R6 or accept rc.12. If they pass, preserve evidence and continue the remaining R5 work, including the separately identified permission-scope refinement (exact shell command vs executable vs all shell) and model-comparison evidence.
