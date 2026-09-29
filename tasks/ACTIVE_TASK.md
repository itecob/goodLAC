# ACTIVE TASK — POSTV1 R5-R003 SHELL SCOPE / MODEL SELECTOR OWNER UAT

## Status
`ACTIVE`

The previous R5 owner-permission semantics UAT passed at source commit
`485c431c52c8cf918423aeac6458dc5870141849`.

R5-R003 implements the remaining shell standing-permission scope refinement and removes the
single-model Pi TUI registration assumption.

## Owner UAT

1. Launch ordinary installed governed `pi`.
2. For a harmless `shell.exec` first-use request, verify standing choices offer:
   - Exact command
   - This executable
   - All shell in this project
3. Verify exact command does not authorize a changed argv.
4. Verify executable scope authorizes changed argv for the same executable but not a different executable.
5. Verify all-shell scope retains project-bound shell behavior.
6. Verify Allow once / Deny once remain exact-request-only and do not ask for standing scope.
7. Run `/model` in Pi and verify both registered models appear:
   - `lac-a003-gpt-oss-20b`
   - `goodlac-exp-qwen36-35b-a3b-nvfp4`
8. With the corresponding FreeToken endpoints running, execute a harmless governed request under
   each model and verify the same four-tool / controller authority behavior.
9. Preserve Qwen behavioral differences as model-comparison evidence; do not weaken controller
   validation to accommodate a model.
10. Keep R6 inactive and do not accept `1.0.0-rc.12` from this UAT alone.
