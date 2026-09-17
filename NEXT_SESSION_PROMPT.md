# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / PHASE 4 INDEPENDENT RE-REVIEW AFTER P4-B001

## 1. Role and controlling rule

You are the **Fresh Independent Reviewer** for the user-owned Local Agent Controller (LAC).

> **AI proposes. Deterministic software determines authorization and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Project root label: `Local Agent Controller`.

This session owns exactly one fresh **Phase 4 independent re-review** of the corrected candidate after blocker `P4-B001` remediation. Do not remediate, do not implement Chief of Staff, and do not begin Phase 5 OpenClaw integration in this review session.

## 2. Mandatory durable reads — in order

Read these first, in exactly this order:

1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read:

- the Phase 4 requirements in `docs/TECHNICAL_DESIGN_AND_IMPLEMENTATION_SPECIFICATION_v0.1.md`;
- `docs/CONTRACTS.md`;
- `docs/PERMISSION_MANAGEMENT.md`;
- `decisions/ADR-007_PERMISSION_ADMINISTRATION_AND_CAPABILITY_GOVERNANCE.md`;
- `docs/B003_EXTERNAL_CONSUMER_INTEGRATION.md`;
- `packages/runtime/external_consumer.py`;
- `tests/acceptance/test_b003_external_consumer.py`;
- `tests/fixtures/b003_external_consumer_app.py`;
- `qualification/evidence/p4_b001_owner_execution.json`;
- `qualification/evidence/p4_b001_test_output.txt`;
- the prior B003 evidence as needed;
- and only additional implementation/evidence files needed to review the corrected candidate.

## 3. Handoff facts

- `MODE=PHASE_BOUNDARY_INDEPENDENT_REVIEW`
- `SESSION_SEGMENT=LAC-P4-REVIEW`
- `PREDECESSOR_ROLE=Lead Implementation Engineer + owner package execution`
- `PREDECESSOR_RESULT=P4-B001_REMEDIATION_OWNER_EXECUTION_PASS`
- `PREDECESSOR_GIT_COMMIT=d86a5adf2da490e797b84cb7fd9b8f7165b839b0`
- `HANDOFF_BASE_GIT_COMMIT=d86a5adf2da490e797b84cb7fd9b8f7165b839b0`
- `REVIEWED_GIT_COMMIT=NONE`
- `PRIOR_BLOCKED_REVIEWED_GIT_COMMIT=5f6e8811bd5e8d180d7d9c712ca90115a4437f18`
- `PREVIOUS_BLOCKER_IDS=P4-B001`
- `BLOCKER_IDS=NONE_CLAIMED_PENDING_REVIEW`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/p4_b001_owner_execution.json`
- `EXPECTED_NEXT_TASK=LAC-P4-REVIEW`
- `REMEDIATION_BASE_GIT_COMMIT=984a47a7b117154fb39e1d08e28285d703a15978`

The corrected implementation commit is `d86a5adf2da490e797b84cb7fd9b8f7165b839b0`. Live HEAD is expected to be one later handoff-only commit containing remediation evidence, state/task transition, and this re-review prompt. Inspect the complete material delta from the previously blocked implementation commit `5f6e8811bd5e8d180d7d9c712ca90115a4437f18` through `d86a5adf2da490e797b84cb7fd9b8f7165b839b0`, then inspect the complete `d86a5adf2da490e797b84cb7fd9b8f7165b839b0` to live-HEAD delta. Do not treat a demonstrably handoff-only successor commit as a reason to review the wrong candidate.

## 4. Binding blocker to re-review

### P4-B001 — external-consumer application/skill identity must be controller-bound

Verify that the corrected runtime receives controller-owned authoritative identity for all four dimensions:

- principal;
- agent;
- application;
- skill.

The consumer capability declaration may still contain `application_id` and `skill_id`, but those values must be treated only as declaration claims and must exactly match the controller-owned application/skill binding before capability lookup or standing-policy evaluation.

Verify specifically that a consumer bound to application/skill A cannot obtain authority scoped to registered application/skill B merely by presenting B's valid canonical declaration. A mismatch must fail closed before policy can grant authority, before an execution lease is created, and before adapter invocation.

The manifest must remain descriptive metadata, not a credential or authentication token. Do not require or reward a new general authentication/RBAC architecture.

## 5. Full Phase 4 re-review requirements

Confirm the remediation did not regress the accepted Phase 4 contract:

- registration/declaration grants zero authority;
- unknown or unconfigured requests fail closed and terminally closed effects never revive;
- explicit configured DENY creates no recurring discovery noise;
- standing-policy specificity, conditional rules, defaults, and equal-specificity deny precedence remain deterministic;
- exact approval remains owner-created, exact, one-use, expiry-bound, and subject to immediate pre-dispatch policy re-evaluation;
- runtime consumers cannot supply/override principal, agent, application, skill, capability revision, authority decision, approval, lease/executor, admin operation, or credential material;
- runtime consumers cannot mutate registry/policy/approvals or reach the owner admin surface;
- duplicate successful requests cannot execute twice;
- credentials remain outside consumer/model/public durable surfaces;
- B003 -> accepted B002 -> P006-UAT/P006 -> prior deterministic regression remains PASS;
- all consequential test effects remain synthetic/local and use no production credentials/accounts;
- Chief of Staff remains separate software.

Use deterministic adversarial conformance evidence of actual controller behavior, including DENY and conditional-policy enforcement. Do not count a model refusal as a security pass. Do not weaken any existing security gate to obtain PASS.

## 6. Reviewer behavior

Return exactly one result: `PASS` or `BLOCKED`.

- If `PASS`: do not remediate. Prepare the complete fresh successor implementation prompt for Phase 5 `LAC-O001` OpenClaw integration, but do not begin that implementation in this review session.
- If `BLOCKED`: identify only concrete blocker IDs tied to binding requirements and prepare a complete fresh remediation prompt. Do not remediate in the review session.

Nonblocking cleanup remains nonblocking.

## 7. Required final fields

Before stopping, report:

- `WHERE_WE_ARE`
- `SESSION_SEGMENT`
- `REVIEW_RESULT`
- `REVIEWED_GIT_COMMIT`
- `WHAT_WAS_VERIFIED`
- `BLOCKERS`
- `NONBLOCKING_FINDINGS`
- `TOTAL_PROJECT_POSITION`
- `STOP_GATE`
- `EXACT_NEXT_SAFE_ACTION`
