# ACTIVE TASK — LAC-P3-REMEDIATION-P3-B001

## Mode

Fresh implementation/remediation segment. Remediate only blocker `P3-B001`; do not begin Phase 4.

## Blocker

`P3-B001 — Pi agent process lacks the required ambient-authority sandbox boundary.`

The binding architecture requires the agent process itself—not merely individual effect subprocesses—to have bounded ambient filesystem, process, network, environment, and credential authority. The reviewed A003 path executes Pi in the host Node process while H001 sandboxing is applied only inside governed effect adapters. This leaves the agent process with an alternate ambient host-authority surface and violates the process-sandbox/bypass-resistance requirement.

## Objective

Contain the Phase 3 Pi agent process with the already qualified H001 sandbox boundary (or the existing selected implementation of that boundary) while preserving the current A001-A003 authority architecture and exact pinned runtime/model identities.

## In scope

- Put the Pi agent process itself behind the qualified ambient-authority sandbox boundary.
- Preserve exactly the four A001 governed tools: `lac_fs_read`, `lac_fs_create`, `lac_fs_replace`, `lac_shell_exec`.
- Preserve Pi -> LAC `ModelProvider` -> FreeToken inference and keep FreeToken inference-only.
- Preserve the exact Pi, FreeToken, and model revision pins from the blocked candidate unless a concrete technical impossibility is demonstrated.
- Add deterministic negative conformance proving the Pi process itself cannot use ambient host filesystem/process/network/environment/credential authority outside its declared runtime needs.
- Keep the positive A003 local-model workflow functional through Dispatcher, H001/H002/H003, and durable receipts.
- Keep the synthetic SSH-key scenario blocked at the effect/OS boundary under policy `ALLOW`, with a durable failed filesystem receipt and no secret bytes entering model-visible evidence/workspace.
- Rerun A003, A002, A001, Phase 1, and H001-H004 regressions.
- Produce a corrected Phase 3 candidate and hand it to one fresh independent Phase 3 re-review.

## Required negative conformance

At minimum establish with synthetic fixtures and real OS effects that the Pi agent process cannot:

1. read a host-only sensitive fixture outside its declared sandbox visibility;
2. inherit a synthetic service credential from the launching host environment;
3. launch an arbitrary host executable/process outside the governed tool/effect path;
4. make an arbitrary outbound or host-loopback network connection except the narrowly required local inference/controller path explicitly provided by the architecture.

A policy `DENY` result is not sufficient evidence. The prohibited ambient effect must be technically unavailable.

## Out of scope

- Phase 4 Gmail/Calendar work.
- OpenClaw or Omarchy integration.
- Broadening Pi's tool surface.
- New authority edges from model output or FreeToken.
- Replacing the authority core or redesigning H001-H004.
- Unrelated refactors or optional hardening.

## Completion

The remediation segment is complete only when the blocker is corrected, the full deterministic gate is green, owner-executable evidence is recorded, and durable state points to a fresh Phase 3 re-review. Do not self-approve the corrected candidate.
