# ACTIVE TASK — LAC-A002

**Phase:** PHASE_3_REAL_LOCAL_AGENT_MODEL
**Mode:** IMPLEMENTATION_SEGMENT
**Role:** Lead Implementation Engineer

## Objective

Integrate the pinned FreeToken revision as the first local model-runtime endpoint behind LAC's `ModelProvider` boundary, while keeping the model runtime completely outside authorization and effect execution.

## In scope

- Verify the completed `LAC-A001` Pi adapter/harness and its owner execution evidence before mutation.
- Inspect the pinned FreeToken revision `af71ba43206e124f5ff6419b47ee36c6e9981078` and the qualified local checkout.
- Implement the minimum FreeToken `ModelProvider`/configuration integration required for Phase 3.
- Keep Pi and FreeToken independently replaceable behind the documented internal interfaces.
- Add deterministic tests for request/response translation, runtime unavailability, malformed output, timeout/cancellation where applicable, and proof that FreeToken has no authority path.
- Preserve all Phase 1 and Phase 2 authorization, approval, lease, receipt, audit, emergency-pause, sandbox, and bypass semantics unchanged.
- Build one fail-closed owner package that verifies, installs, tests, records evidence, and advances durable state only after success.

## Out of scope

- Full Pi + FreeToken + LAC end-to-end agent qualification.
- New effect adapters or broader host capabilities.
- OpenClaw integration.
- Alternative model runtimes such as llama.cpp or Ollama except as documented future compatibility targets.
- Policy-engine replacement or UI work.
- Production credentials or external consequential effects.

## Acceptance

1. FreeToken is used only as a local inference endpoint and cannot approve, lease, dispatch, or directly execute governed effects.
2. The runtime integration is pinned to `af71ba43206e124f5ff6419b47ee36c6e9981078` and fails closed on pin/interface drift.
3. Model/runtime request and response translation is deterministic and tested.
4. Runtime failure, malformed responses, timeout/cancellation, and unavailable endpoint conditions fail closed without granting authority.
5. No service credential is introduced into model-visible context by the integration.
6. `LAC-A001` Pi governed-tool tests remain green.
7. Phase 1 regression remains green.
8. `scripts/test-h001`, `scripts/test-h002`, `scripts/test-h003`, and `scripts/test-h004` remain green.
9. No full Phase 3 end-to-end qualification is started in this segment.
10. Repository is clean after the successful owner workflow.
