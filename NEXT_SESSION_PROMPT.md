# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / FRESH PHASE 3 P3-B001 RE-REVIEW

`SESSION_SEGMENT=LAC-P3-REREVIEW-P3-B001`
`MODE=PHASE_BOUNDARY_INDEPENDENT_REVIEW`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. Act only as a **fresh independent Phase 3 reviewer** of the corrected candidate. Do not remediate findings, do not begin Phase 4, and do not trust the predecessor's PASS claims without verifying them.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then inspect at minimum:

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`, especially §§17, 19, 33, and permanent sandbox/credential acceptance tests;
- `docs/CONTRACTS.md`;
- `docs/THREAT_MODEL.md`;
- `docs/MODEL_PROVIDER_CONTRACT.md`;
- `docs/PHASE3_A003_QUALIFICATION.md`;
- `decisions/ADR-004_SANDBOX_BACKEND.md`;
- `packages/sandbox/`;
- `packages/adapters/pi/adapter.py`;
- `packages/adapters/pi/governed_pi.mjs`;
- `scripts/a003_agent_sandbox.py`;
- `scripts/a003_agent_worker.mjs`;
- `scripts/a003_qualification.mjs`;
- `scripts/a003_model_provider_stream.py`;
- `scripts/a003_controller_bridge.py`;
- `scripts/a003_verify_agent_sandbox.py`;
- `scripts/a003_verify_evidence.py`;
- `scripts/test-a003`;
- `tests/integration/test_a003_agent_process_sandbox.py`;
- relevant A001/A002 and Phase 1/H001-H004 tests/evidence;
- `qualification/evidence/a003_agent_sandbox_evidence.json`;
- `qualification/evidence/a003_owner_execution.json`;
- `qualification/evidence/a003_owner_execution.log`;
- `qualification/evidence/a003_runtime.json`;
- `qualification/evidence/a003_evidence_summary.json`;
- `qualification/evidence/a003_qualification.json`.

## Handoff facts to verify; do not assume

- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=REMEDIATION_OWNER_GATE_PASS`
- `ORIGINAL_BLOCKER_IDS=P3-B001`
- `ORIGINAL_A003_IMPLEMENTATION_GIT_COMMIT=949ac791c077600b2ab683b63131156439ce181e`
- `ORIGINAL_REVIEW_LIVE_GIT_COMMIT=3bb011de6a626ff717cfcd04e4a4d1ff95fd0a16`
- `REMEDIATION_START_GIT_COMMIT=71b6d26ba648444859721daace6775467af789cf`
- `CORRECTED_IMPLEMENTATION_GIT_COMMIT=809bb01ec52e6f04d96f22c0195c47961b3efd7a`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/a003_owner_execution.json`
- `PI_PIN=da840b6216578c2a571d0374ac6a2091a83f9d91`
- `FREETOKEN_PIN=af71ba43206e124f5ff6419b47ee36c6e9981078`
- `MODEL_REPO=openai/gpt-oss-20b`
- `MODEL_REVISION=6cee5e81ee83917806bbde320786a8fb61efebee`
- `EXPECTED_PHASE=PHASE_3_REAL_LOCAL_AGENT_MODEL`
- `EXPECTED_ACTIVE_TASK=LAC-P3-REREVIEW-P3-B001`

The owner package creates one workflow/evidence handoff commit newer than `CORRECTED_IMPLEMENTATION_GIT_COMMIT`. Inspect the complete corrected-implementation-to-live-HEAD delta and require it to contain only:

- `PROJECT_STATE.json`;
- `tasks/ACTIVE_TASK.md`;
- `NEXT_SESSION_PROMPT.md`;
- `qualification/evidence/a003_owner_execution.json`.

Fail closed on unrelated implementation drift. The corrected candidate substance is the corrected implementation commit; the later delta is permitted only for owner-evidence finalization and review workflow handoff.

## Review question — original blocker P3-B001

Determine independently whether the corrected candidate now satisfies the binding ambient-authority boundary for the **Pi agent process itself**, not merely its governed effect subprocesses.

At minimum verify deterministically that:

1. the actual pinned Pi Agent process is launched through the selected, qualified H001 Bubblewrap `SandboxBackend` rather than in the host Node process;
2. the Pi process has exactly four governed A001 tools and no stock/unrestricted tool surface;
3. the Pi process has no ambient workspace/controller-database/host-home/service-credential visibility;
4. inherited host service credentials are cleared at the OS process boundary;
5. an arbitrary host executable/process cannot produce the synthetic prohibited host effect;
6. host loopback and arbitrary network access are unavailable to the Pi process itself;
7. the declared model/effect path uses only fixed inherited-stdio IPC to a host broker, with no generic command/executable/network capability;
8. Pi inference still crosses the LAC-owned `ModelProvider` boundary to the exact pinned FreeToken runtime/model, and FreeToken remains inference-only;
9. all consequential filesystem/shell effects still cross `PiAgentAdapter -> Dispatcher -> H002/H003 -> H001` and produce durable receipts;
10. the synthetic SSH-key request is evaluated under policy `ALLOW`, fails at the filesystem/OS boundary, records a durable failed `filesystem:v1` receipt, and exposes no secret bytes;
11. A002, A001, Phase 1, and H001-H004 regressions remain green;
12. no Phase 4 implementation or unrelated architecture change was introduced.

A policy `DENY`, model refusal, prompt instruction, or source-level claim is not sufficient evidence for an operating-system containment property. Confirm the prohibited effect did not occur using the deterministic synthetic evidence/tests.

## Review result discipline

Return exactly one phase-boundary result:

- `PASS` — only if Phase 3 and the remediated P3-B001 boundary satisfy all binding acceptance criteria; or
- `BLOCKED` — identify concrete blocker IDs tied to violated binding invariants/acceptance criteria.

Optional improvements are `NONBLOCKING` and may not prevent progression.

Do not remediate in this review session.

If `PASS`, prepare the required owner workflow handoff for the first Phase 4 implementation segment (`LAC-B001`, Gmail adapter) without implementing Phase 4 in the review session. If `BLOCKED`, prepare a fresh remediation handoff containing only the concrete blocker IDs. In either case preserve the project's one-package/one-command and fresh-session workflow.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P3-REREVIEW-P3-B001`
- `PREDECESSOR_RESULT=REMEDIATION_OWNER_GATE_PASS`
- `ORIGINAL_BLOCKER_IDS=P3-B001`
- `REVIEW_RESULT=PASS|BLOCKED`
- `WHAT_WAS_VERIFIED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=PHASE_BOUNDARY_REVIEW_REQUIRED`
- `EXACT_NEXT_SAFE_ACTION=`
