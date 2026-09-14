# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 3 P3-B001 REMEDIATION

`SESSION_SEGMENT=LAC-P3-REMEDIATION-P3-B001`
`MODE=IMPLEMENTATION_SEGMENT`

Use the connected Web-File-Tool. Treat durable repository state and Git history as authority. This is a fresh remediation implementation segment for the single Phase 3 blocker `P3-B001`. Do not begin Phase 4, broaden scope, or self-approve the corrected Phase 3 candidate.

## Mandatory first reads — exact order

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then inspect at minimum:

- `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`
- `docs/CONTRACTS.md`
- `docs/THREAT_MODEL.md`
- `docs/MODEL_PROVIDER_CONTRACT.md`
- `docs/PHASE3_A003_QUALIFICATION.md`
- `decisions/ADR-004_SANDBOX_BACKEND.md`
- `packages/sandbox/`
- `packages/adapters/pi/adapter.py`
- `packages/adapters/pi/governed_pi.mjs`
- `packages/adapters/pi/model_stream_bridge.mjs`
- `scripts/a003_qualification.mjs`
- `scripts/a003_model_provider_stream.py`
- `scripts/a003_controller_bridge.py`
- `scripts/a003_verify_evidence.py`
- `scripts/test-a003`
- relevant Phase 2/H001-H004 tests and qualification evidence
- `qualification/evidence/a003_owner_execution.json`
- `qualification/evidence/a003_owner_execution.log`
- `qualification/evidence/a003_runtime.json`
- `qualification/evidence/a003_evidence_summary.json`

## Predecessor/review facts to verify; do not assume

- `PREDECESSOR_ROLE=Fresh Independent Reviewer`
- `PREDECESSOR_RESULT=BLOCKED`
- `BLOCKER_IDS=P3-B001`
- `A003_IMPLEMENTATION_GIT_COMMIT=949ac791c077600b2ab683b63131156439ce181e`
- `REVIEW_LIVE_GIT_COMMIT=3bb011de6a626ff717cfcd04e4a4d1ff95fd0a16`
- `PI_PIN=da840b6216578c2a571d0374ac6a2091a83f9d91`
- `FREETOKEN_PIN=af71ba43206e124f5ff6419b47ee36c6e9981078`
- `MODEL_REPO=openai/gpt-oss-20b`
- `MODEL_REVISION=6cee5e81ee83917806bbde320786a8fb61efebee`
- `EXPECTED_PHASE=PHASE_3_REAL_LOCAL_AGENT_MODEL`
- `EXPECTED_ACTIVE_TASK=LAC-P3-REMEDIATION-P3-B001`

The workflow handoff commit created by the owner's blocked-review handoff package is expected to be newer than `REVIEW_LIVE_GIT_COMMIT`. Inspect the complete delta and require it to be workflow-only (`PROJECT_STATE.json`, `tasks/ACTIVE_TASK.md`, `NEXT_SESSION_PROMPT.md`). Fail closed on unrelated implementation drift.

## Blocking finding — P3-B001

The reviewed A003 candidate does not establish the binding ambient-authority boundary for the Pi agent process itself.

Binding evidence:

- `docs/ARCHITECTURE.md`: governed tools alone are insufficient; the agent process must have bounded ambient filesystem/process/network/environment authority using an established Linux sandbox.
- the controlling specification §17: an agent is not governed merely because its tools are governed; the process itself must have bounded ambient authority.
- `decisions/ADR-004_SANDBOX_BACKEND.md`: tool policy alone is not an ambient-authority boundary; bubblewrap is the selected H001 backend.
- reviewed A003 `scripts/test-a003` invokes `node scripts/a003_qualification.mjs` directly.
- reviewed `scripts/a003_qualification.mjs` constructs and runs the Pi Agent in that host Node process; H001 sandboxing is reached only later inside governed filesystem/shell effect adapters.
- reviewed A003 runtime/evidence proves effect subprocess containment but contains no deterministic proof that the Pi agent process itself lacks ambient host filesystem/process/network/environment/credential authority.

This violates the binding process-sandbox/bypass-resistance requirement and leaves an alternate ambient authority surface even though the exposed Pi tool list is correctly limited to four governed tools.

## Required remediation scope

Remediate only `P3-B001`.

The corrected design must put the Pi agent process itself behind the already qualified H001 ambient-authority boundary while preserving:

1. exactly four governed A001 tools and no stock/unrestricted tool surface;
2. Pi inference through the LAC-owned `ModelProvider` boundary;
3. FreeToken as inference-only, with no policy/approval/lease/dispatch/effect authority;
4. exact Pi, FreeToken, and model revision identity unless a concrete impossibility forces an explicit gate;
5. the existing Dispatcher -> H001/H002/H003 effect path and durable receipts;
6. credential isolation and controller-owned authority identifiers;
7. all Phase 1 and H001-H004 security properties.

Add deterministic negative conformance using only synthetic local fixtures that proves the Pi agent process itself cannot:

- read a host-only sensitive fixture outside its declared visibility;
- inherit a synthetic service credential from the host launcher environment;
- launch an arbitrary host executable/process outside the governed effect path;
- obtain arbitrary host/outbound network access beyond the narrowly declared local runtime path needed for the qualification.

For each negative property, prove the prohibited OS effect did not occur. A model response or policy `DENY` is not proof.

## Required validation

Before handoff, at minimum:

- run the new Pi-process ambient-authority conformance tests;
- rerun the real positive A003 local-model scenario and verify durable successful receipts;
- rerun the synthetic SSH-key `ALLOW` scenario and verify the durable failed `filesystem:v1` receipt and secret absence;
- rerun `scripts/test-a003`, including A002 and A001/Phase1/H001-H004 regressions;
- verify exact Pi/FreeToken/model identities and current source pins;
- verify no Phase 4 implementation was introduced;
- verify Git diff/history contains only the intended P3-B001 remediation plus required evidence/workflow updates.

Correct in-scope failures in this same remediation segment. Do not defer known P3-B001 defects to another implementation session.

## Owner package and stop rule

When the corrected remediation segment is complete, create one owner-executable package and exactly one self-contained Bash command following the project packaging contract. It must fail closed on unexpected Git/state/task input, install the corrected candidate, run the full deterministic verification, record owner execution evidence, update durable state/task, and install a populated root `NEXT_SESSION_PROMPT.md` for a **fresh independent Phase 3 re-review**.

Do not perform that re-review in the remediation session. Do not begin Phase 4.

## Required final status fields

- `WHERE_WE_ARE=`
- `SESSION_SEGMENT=LAC-P3-REMEDIATION-P3-B001`
- `PREDECESSOR_RESULT=BLOCKED`
- `BLOCKER_IDS=P3-B001`
- `WHAT_WAS_VERIFIED=`
- `WHAT_WAS_COMPLETED=`
- `WHAT_REMAINS_IN_CURRENT_PHASE=`
- `TOTAL_PROJECT_POSITION=`
- `BLOCKERS=`
- `STOP_GATE=`
- `EXACT_NEXT_SAFE_ACTION=`
