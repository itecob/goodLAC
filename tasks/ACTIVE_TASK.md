# ACTIVE TASK — LAC-P3-REREVIEW-P3-B001

## Mode

Fresh independent Phase 3 re-review. Review the corrected Phase 3 candidate after remediation of `P3-B001`. Do not remediate and do not begin Phase 4.

## Review objective

Independently determine whether Phase 3 now satisfies the binding Pi-process ambient-authority boundary and all Phase 3 acceptance criteria.

## Original blocker

`P3-B001 — Pi agent process lacked the required ambient-authority sandbox boundary.`

The corrected candidate claims that the actual pinned Pi process now runs through the selected H001 Bubblewrap boundary with `network=none`, a cleared environment, no ambient workspace/controller database/host home/service credentials, and only fixed inherited-stdio broker access to the LAC ModelProvider and governed effects.

## Required review

- Verify the live corrected implementation commit and the permitted workflow/evidence-only handoff delta.
- Inspect the actual sandbox launcher/worker and H001 integration.
- Verify exact Pi/FreeToken/model pins remain unchanged.
- Validate the deterministic Pi-process filesystem/environment/process/network negative conformance using synthetic fixtures and actual OS outcomes.
- Validate the exact four-tool surface and fixed broker capability surface.
- Validate positive A003 governed effects and durable receipts.
- Validate the synthetic SSH-key scenario remains policy `ALLOW` plus OS/effect-boundary failure with a durable failed filesystem receipt and no secret bytes.
- Validate A002, A001, Phase 1, and H001-H004 regressions.
- Confirm no Phase 4 implementation or unrelated architecture change entered the candidate.

## Result

Return exactly `PASS` or `BLOCKED`. Only concrete violated binding invariants/acceptance criteria are blockers. Optional improvements are nonblocking. Do not remediate in the review session.
