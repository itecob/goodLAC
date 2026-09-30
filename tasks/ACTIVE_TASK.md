# ACTIVE TASK — POSTV1 R5 QUALIFICATION / MODEL-COMPARISON CLOSEOUT

## Status
`ACTIVE`

R5-R003 owner UAT is complete. R5 itself remains active.

## Completed evidence carried forward

- Accepted historical baseline remains `1.0.0-rc.11`.
- R5-R001 shared administrator control-plane remediation passed deterministic qualification.
- Owner-permission semantics remediation passed retained regression and live UAT.
- R5-R003 implementation commit:
  `996c1629f9d560c64e04a9102df9cd713aae29f3`.
- R5-R003 retained qualification passed for exact shell-command scope, executable scope,
  all-shell/project resource scope, one-time exact-request behavior, and bounded GPT-OSS/Qwen
  registration with unknown-model fail-closed behavior.
- Installed Pi `/model` exposed both configured governed model routes.
- Harmless governed `/usr/bin/ls -la` completed successfully under Qwen and GPT-OSS.
- The owner selected `Allow Once` for both live executions, demonstrating fresh one-shot
  authorization rather than inherited standing permission.
- GPT-OSS 20B exhibited a retry/replay interpretation weakness on an ordinary repeated explicit
  user instruction; explicit fresh-request wording corrected the behavior. Qwen did not exhibit
  that behavior under the equivalent ordinary prompt. This is model behavior, not controller
  authority failure.

## Current task

Determine and execute the smallest remaining R5 qualification/model-comparison closeout sequence.

1. Inspect current roadmap/state/evidence for any still-unsatisfied R5 acceptance requirement.
2. Do not duplicate already-passed live or automated evidence without a concrete gap.
3. Preserve model-behavior findings separately from controller/security findings.
4. If R5 is fully satisfied, prepare bounded R5 closeout/review-candidate evidence for owner
   execution/commit.
5. Keep `1.0.0-rc.12` unaccepted and R6 inactive until R5 is explicitly closed and the owner
   authorizes the fresh independent R6 review.
