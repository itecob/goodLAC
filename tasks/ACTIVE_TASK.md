# ACTIVE TASK — LAC-A004-UAT

## Objective

Repeat the owner hands-on A004 baseline validation after deterministic remediation of `A004-UAT-B001` and `A004-UAT-B002`. This checkpoint validates usability only; it does not reopen the accepted Phase 3 technical proof and it does not begin Phase 4.

## Preconditions

- `qualification/evidence/a004_remediation_execution.json` exists and records `result=PASS`.
- The remediation implementation commit is in Git history.
- `scripts/test-a004` passed during remediation.
- Durable project state names `LAC-A004-UAT` with no active blockers.

## Required owner validation

Use `docs/A004_OWNER_BASELINE_UAT.md` as the baseline script and repeat the complete owner UAT. In addition, explicitly validate both remediated defects:

1. **Arrow-key editing:** at `lac>`, type a sentence, use left/right arrow keys to move within the line, edit it, and submit. The displayed/submitted prompt must reflect the edit. Raw `^[[D`/`^[[C` control sequences must not enter the prompt, and the session must remain operational.
2. **Residual control safety:** if a disallowed terminal control sequence reaches the line despite Readline, the terminal must reject that input and remain interactive; it must not dispatch a malformed model request or kill Pi.
3. **Shell argv contract:** ask exactly: `Use the governed shell tool to list the current workspace with /usr/bin/ls.` The tool event must show `executable='/usr/bin/ls'`, `argv=[]`, `cwd='.'` (with empty environment in the governed request), and the assistant must report the actual bounded workspace listing rather than `/usr/bin/ls`.

Then repeat the remaining create/read/replace, boundary denial, unapproved executable denial, status-after-denial, clean shutdown, restart, and governed-read checks from the UAT guide.

## Scope rules

- Do not implement Gmail, Calendar, Chief of Staff, credentials, or any Phase 4 effect adapter.
- Do not broaden the shell allowlist or authority semantics.
- Do not add unrelated UX work.
- Owner interaction is evidence; do not claim hands-on UAT PASS without the owner's observations.

## Result handling

### If owner UAT passes

Record durable owner-UAT PASS evidence and create one owner-executable handoff package that activates `LAC-B001` as the next fresh implementation segment. Preserve the accepted Phase 3 review and the A004 remediation/owner evidence.

### If owner UAT finds a defect

Record only the concrete observed blocker(s), keep Phase 4 deferred, and create one owner-executable blocked-UAT handoff package for a fresh bounded remediation session.

## Package required?

Only after the owner has completed the hands-on UAT and the result is known. The UAT session itself must not silently advance to `LAC-B001`.

## Deferred task

`LAC-B001` remains deferred until explicit owner A004 UAT acceptance.
