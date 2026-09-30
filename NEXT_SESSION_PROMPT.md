# NEXT SESSION PROMPT — goodLAC / R5 CLOSED, R6 AWAITING OWNER AUTHORIZATION

Use the connected Web-File-Tool. Work against the live root labeled `Local Agent Controller`; the local repository directory remains `local-agent-controller` (normally `${HOME}/local-agent-controller`). goodLAC is the product/GitHub brand, not the local folder name.

Read:
- `PROJECT_STATE.json`
- `tasks/ACTIVE_TASK.md`
- `docs/POST_V1_REMEDIATION_ROADMAP.md`
- `docs/R5_INTEGRATED_OWNER_UAT_CLOSEOUT.md`
- `docs/R5_R003_OWNER_UAT_EVIDENCE.md`
- the newest commit

Verify the repository is clean and on `main`.

Current boundary:
- R5 is `COMPLETE`.
- R6 is `INACTIVE`.
- `1.0.0-rc.11` remains the last independently accepted release.
- `1.0.0-rc.12` remains `UNACCEPTED`.
- R5-R003 implementation/runtime commit remains `996c1629f9d560c64e04a9102df9cd713aae29f3`.
- The installed development snapshot intentionally remains `~/.local/share/local-agent-controller/releases/r5-996c1629f9d560c64e04a9102df9cd713aae29f3`.
- The R5 closeout commit is documentation/workflow-state/evidence only. Do not reinstall merely to match it.
- The exact R5 review candidate is the newest R5 closeout commit. Verify its commit message is `r5: close integrated qualification and prepare review candidate`.

Do not activate R6 unless the owner explicitly authorizes the fresh independent R6 review.

If the owner explicitly authorizes R6, the reviewer must be fresh and independent from the implementation agent and must review the exact R5 candidate. The review disposition is PASS or BLOCKED. A PASS is required before `1.0.0-rc.12` can be accepted.

Preserve all prior accepted `1.0.0-rc.11` / Phase 7 evidence.
