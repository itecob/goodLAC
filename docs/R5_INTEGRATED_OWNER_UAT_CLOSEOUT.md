# R5 Integrated Owner UAT / Release-Qualification Closeout

Date: 2026-09-30

## Disposition

R5: `PASS` / `COMPLETE`.

This closes R5 only. It does **not** activate R6 and does **not** accept `1.0.0-rc.12`.

Historical accepted baseline remains `1.0.0-rc.11`.

## Technical boundary

- Pre-closeout repository HEAD: `16989dbeba72b9c03da21a3d2db2496633321c23`
- R5-R003 implementation/runtime commit: `996c1629f9d560c64e04a9102df9cd713aae29f3`
- Installed development runtime intentionally remains:
  `~/.local/share/local-agent-controller/releases/r5-996c1629f9d560c64e04a9102df9cd713aae29f3`
- The closeout commit is documentation/workflow-state/evidence only.

## Acceptance matrix

- Allow once: PASS.
- Always allow: PASS.
- Ask every time: PASS.
- Deny once: PASS.
- Always deny: PASS.
- Overwrite/replace: PASS.
- Restart/recovery: PASS.
- Scope display: PASS.
- Exact project isolation: PASS.
- At least two ordinary project directories: PASS.

The final bounded UAT additionally proved that Project A standing `filesystem.create` DENY did not cross into Project B, Project B could not see Project A recovery state, abrupt Project A termination left the replace effect absent, restart did not auto-dispatch, and explicit `/lac-resume` completed the fresh replace request with exact approval and a durable receipt.

## Harness correction

The initial bounded final UAT unnecessarily asked Project B to repeat `filesystem.create` after the file already existed. That was not required to prove isolation and made the checkpoint depend on model/tool behavior for an already-existing file. The binding isolation evidence is the first Project B request: Project A already had standing DENY, yet Project B received its own first-use gate and completed an independently authorized create.

No controller/security failure is attributed to that harness assertion.

## Final bounded evidence

Repository copy:
`docs/evidence/R5_INTEGRATED_OWNER_UAT_FINAL_20260930.json`

Original owner-host artifacts:

- log SHA-256: `e68185790e4b77d711c887cff4f29f43e78912e9e8011c1e99cb3a87e280656b`
- JSON SHA-256: `4b5fc3c792cbf924ae48937937cbc2b06454eae06ad528eb95b0d38e9968316d`

## Model-comparison finding

GPT-OSS 20B may misclassify an ordinary repeated explicit user request as an automatic retry/replay. Explicit fresh-request wording corrected the behavior. Qwen did not show the same behavior in the equivalent comparison.

This remains model-comparison evidence, not a goodLAC authority defect.

## Post-closeout boundary

- R5: `COMPLETE`
- R6: `INACTIVE`
- last accepted release: `1.0.0-rc.11`
- target release: `1.0.0-rc.12`
- rc.12: `UNACCEPTED`

The next action is explicit owner authorization of a fresh independent R6 review of the exact R5 closeout candidate.
