# P006 Permission-Management E2E / Security Qualification

**Task:** `LAC-P006`
**Scope:** deterministic local qualification of the accepted P001-P005 permission-management plane. This task adds qualification only; it adds no new permission semantics.

The focused P006 suite establishes the following integrated properties using synthetic local fixtures:

- capability registration is descriptive and grants zero authority before standing policy exists;
- P003 specificity is deterministic and equal-specificity conflict resolves `DENY > REQUIRE_APPROVAL > ALLOW`;
- an unknown P002 request is terminally closed, remains closed after later capability/policy/pending administration, survives restart, and only a fresh request can benefit from the new authority state;
- exact approval through P004/P005 creates no lease or effect by itself, survives restart, is blocked by a later current-policy `DENY`, and remains one-request authority when current policy again requires approval;
- unavailable, malformed, unsupported, and wrong-peer administrator paths cause no canonical mutation;
- the P004 administrator socket is owner-only and remains absent from the selected governed sandbox/runtime mutation surface.

## Deterministic prior-phase regression rule

P006 is required to be deterministic. During the first two owner attempts, every P006/P005/P004/P003/P002/P001/B001 deterministic test passed, but the inherited A003 live-model scenario repeatedly returned no tool call under unseedable local-model `tool_choice=auto`; the strict A003 evidence verifier correctly rejected the missing positive trace. Repeating that stochastic model-choice test cannot make a later security regression gate deterministic.

The corrected regression rule therefore separates **already accepted live behavior** from **current deterministic security conformance**:

- direct `scripts/test-a003` and `scripts/test-a004` continue to default to their original live behavior;
- P006 selects `accepted-evidence` regression mode only for nested A003/A004 regression;
- accepted A003 real-model/Pi/effect evidence is cryptographically checked against `qualification/evidence/a003_owner_execution.json` and its recorded evidence hashes, with accepted commit/pin/model identity verified in live Git ancestry;
- accepted A004 live baseline and owner UAT evidence is checked against its durable accepted records and commits;
- current A003 Pi-process sandbox isolation, exact four-tool surface, model/effect boundary source contract, stream bridge, A002/A001/H001-H004, and current A004 deterministic controller/receipt/sandbox tests are rerun normally;
- P005/P004/P003/P002/P001/B001 focused and negative-security suites are rerun normally.

This correction does not convert a failed A003 live attempt into a pass and does not weaken direct A003/A004 acceptance. It removes an unseedable model-behavior choice from a task whose binding objective is deterministic permission-management/security qualification while preserving the independently accepted live proof as immutable evidence.

`scripts/test-p006` records the full deterministic regression output under `qualification/evidence/p006_test_output.txt` and the owner package records a structured result under `qualification/evidence/p006_owner_execution.json`.
