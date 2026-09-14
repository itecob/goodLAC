# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 3 FRESH INDEPENDENT REVIEW

`SESSION_SEGMENT=LAC-P3-REVIEW`
`MODE=FRESH_INDEPENDENT_REVIEW`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This is a fresh independent Phase 3 review; do not implement, remediate, redesign, or begin Phase 4.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then inspect at minimum:

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`
- `docs/CONTRACTS.md`
- `docs/MODEL_PROVIDER_CONTRACT.md`
- `docs/PHASE3_A003_QUALIFICATION.md`
- `packages/adapters/pi/adapter.py`
- `packages/adapters/pi/governed_pi.mjs`
- `packages/adapters/pi/model_stream_bridge.mjs`
- `packages/model_provider/contract.py`
- `packages/adapters/freetoken/provider.py`
- `scripts/a003_model_provider_stream.py`
- `scripts/a003_controller_bridge.py`
- `scripts/a003_qualification.mjs`
- `scripts/a003_verify_evidence.py`
- `scripts/test-a003`
- `tests/integration/test_a003_model_boundary.py`
- `tests/integration/test_a003_stream_bridge.mjs`
- `qualification/evidence/a003_owner_execution.json`
- `qualification/evidence/a003_owner_execution.log`
- `qualification/evidence/a003_runtime.json`
- `qualification/evidence/a003_evidence_summary.json`
- A001/A002 owner evidence and the exact pinned Pi/FreeToken source needed to verify the relevant interfaces.

## Predecessor facts to verify; do not assume

- `PREDECESSOR_SEGMENT=LAC-A003`
- `PREDECESSOR_RESULT=PASS`
- `A003_IMPLEMENTATION_GIT_COMMIT=949ac791c077600b2ab683b63131156439ce181e`
- `A002_IMPLEMENTATION_GIT_COMMIT=1c07f57ef846895aed638c411c0c26b8fdcbf841`
- `A001_IMPLEMENTATION_GIT_COMMIT=93f72ded7b96801d0e619a5aa702f9ce0f87b522`
- `PI_PIN=da840b6216578c2a571d0374ac6a2091a83f9d91`
- `FREETOKEN_PIN=af71ba43206e124f5ff6419b47ee36c6e9981078`
- `MODEL_REPO=openai/gpt-oss-20b`
- `MODEL_REVISION=6cee5e81ee83917806bbde320786a8fb61efebee`
- `EXPECTED_PHASE=PHASE_3_REAL_LOCAL_AGENT_MODEL`
- `EXPECTED_ACTIVE_TASK=LAC-P3-REVIEW`

Fail closed if these facts disagree with durable state, evidence, or live Git history.

## Review objective

Independently determine whether Phase 3 candidate satisfies the binding architecture and A001-A003 requirements. At minimum verify:

1. no model output can authorize an effect;
2. Pi receives exactly the four governed A001 tools and no stock/unrestricted tool surface;
3. Pi inference crosses the LAC-owned ModelProvider boundary;
4. FreeToken remains inference-only and cannot approve, lease, dispatch, or invoke effects directly;
5. selected model and runtime identity are exact/reproducible;
6. positive local-model scenario reaches Dispatcher, H001/H002/H003 as applicable, and durable successful receipts;
7. adversarial synthetic SSH-key scenario is blocked at the effect/OS boundary under policy `ALLOW`, with a failed filesystem receipt and no secret bytes entering model-visible evidence/workspace;
8. no service credential is inserted into model-visible context;
9. A001 and A002 regressions, Phase 1 regressions, and H001-H004 remain green in owner evidence;
10. Git history contains the claimed A003 implementation commit and current workflow handoff without unrelated implementation drift;
11. Phase 4 or later scope was not implemented early.

The review is evidence-based. Do not treat the owner script's `PASS` label as proof by itself.

## Review disposition

Return exactly one:

- `PASS` — no blocking Phase 3 finding;
- `BLOCKED` — one or more concrete blocking findings, each with stable finding id, evidence, violated requirement/invariant, and required remediation scope.

Do not remediate in this session. If PASS, prepare the normal owner-executable workflow handoff package for the next planned task only if the live project specification unambiguously identifies that task. If the next phase/task requires an architectural, authority, or licensing decision, stop at the corresponding gate instead of inventing scope.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P3-REVIEW`
- `A003_IMPLEMENTATION_GIT_COMMIT=949ac791c077600b2ab683b63131156439ce181e`
- `WHAT_WAS_VERIFIED=`
- `REVIEW_DISPOSITION=`
- `BLOCKING_FINDINGS=`
- `NONBLOCKING_FINDINGS=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
