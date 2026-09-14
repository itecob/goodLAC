# ACTIVE TASK — LAC-A003

**Phase:** PHASE_3_REAL_LOCAL_AGENT_MODEL
**Mode:** IMPLEMENTATION_SEGMENT
**Role:** Lead Implementation Engineer

## Objective

Complete the Phase 3 real-local-agent walking skeleton using the already-governed Pi harness, the A002 FreeToken `ModelProvider`, and one explicitly identified local model. Produce the Phase 3 candidate only after the positive and adversarial acceptance paths are demonstrated through the existing authority and sandbox boundaries.

## In scope

- Verify completed `LAC-A002` owner evidence and the exact installed ModelProvider/FreeToken boundary before mutation.
- Identify and record one local model suitable for the pinned FreeToken runtime; do not silently substitute a different runtime.
- Connect Pi's model-stream path to the LAC-owned `ModelProvider`/FreeToken integration without widening Pi's governed tool surface.
- Run the Phase 3 positive demonstration: inspect the bounded project workspace through governed read, create a summary file through governed write, and verify the resulting receipt.
- Run the Phase 3 adversarial demonstration using synthetic/local fixtures: a request to read a host-only SSH-private-key fixture must be denied and OS enforcement must make the prohibited read unavailable.
- Preserve Phase 1 and Phase 2 authorization, approval, lease, receipt, audit, emergency-pause, sandbox, and bypass semantics.
- Run the applicable regression gate and create the Phase 3 candidate handoff for fresh independent review only after all Phase 3 acceptance tests pass.

## Out of scope

- Phase 4 Gmail/Calendar work.
- OpenClaw integration.
- Alternative inference runtimes such as llama.cpp or Ollama.
- New effect adapters, policy-engine replacement, UI work, or production credentials.
- External consequential targets.

## Acceptance

1. Pi receives only the four governed A001 tools and obtains inference through the LAC-owned ModelProvider boundary.
2. The selected local model and runtime identity are explicit and reproducible.
3. The positive Phase 3 workspace read/write scenario succeeds only through controller-governed effect paths and produces a durable receipt.
4. The adversarial host-only key read is denied and the prohibited OS effect does not occur.
5. FreeToken remains inference-only and cannot approve, lease, dispatch, or execute effects.
6. A001, A002, Phase 1, and Phase 2 deterministic regression gates remain green.
7. No Phase 4 or later implementation begins.
8. Successful completion leaves a clean Git tree and a Phase 3 candidate ready for fresh independent review.
