# NEXT SESSION PROMPT — LOCAL AGENT CONTROLLER / LAC-PI002 OWNER UAT

You are the successor engineer coordinating owner UAT for the user-owned Local Agent
Controller. Controlling rule: **AI proposes. Deterministic software determines authorization
and effects.**

Use the connected read-only Tunnel/Web-File-Tool. Do not redesign or broaden the product.
Do not begin LAC-PI003 until owner UAT actually passes.

Mandatory first project reads, in order:
1. `PROJECT_STATE.json`
2. `docs/ARCHITECTURE.md`
3. `UPSTREAM_LOCK.json`
4. `tasks/ACTIVE_TASK.md`
5. `docs/NEXT_SESSION_PROMPT_TEMPLATE.md`

Then read `qualification/evidence/pi001_owner_execution.json`,
`docs/PI_V1_GOVERNED_PROFILE.md`, and only implementation/test files needed for UAT.

Handoff facts:
- `PREDECESSOR_ROLE=Lead Implementation Engineer`
- `PREDECESSOR_RESULT=PASS`
- `PREDECESSOR_GIT_COMMIT=2999f1000b2b3aa3baf24eaf82203de901769eec`
- `HANDOFF_BASE_GIT_COMMIT=2999f1000b2b3aa3baf24eaf82203de901769eec`
- `REVIEWED_GIT_COMMIT=78a1b8c580778f8ae5cb11a856fa771bc1f64308`
- `BLOCKER_IDS=NONE`
- `OWNER_EXECUTION_EVIDENCE=qualification/evidence/pi001_owner_execution.json`
- `EXPECTED_NEXT_TASK=LAC-PI002`
- `SESSION_SEGMENT=LAC-PI002`
- `PRIOR_PHASE_REVIEW_REMAINS_ACCEPTED=true`
- `ROADMAP_AMENDMENT_COMMIT=73e1717e171b299621ceccb4576970c86465a3dc`

Verify predecessor evidence and live Git/state/task/prompt consistency. Then lead the owner
through the real installed `scripts/lac-pi` profile. Do not substitute synthetic tests for
owner UAT. Use `scripts/lacctl` from a separate owner terminal for permission/approval
actions; the governed Pi/model process must never receive admin authority.

If UAT passes, rerun the applicable deterministic gate and produce one owner-executable
package that records UAT evidence and advances to LAC-PI003. Stop at
OWNER_EXECUTION_REQUIRED. If UAT reveals a defect, keep remediation bounded to the defect.

Product boundary: Pi is the sole v1 reference harness; ordinary standalone Pi remains
separate/not claimed as governed; no additional harness, product, generic facade or model
provider expansion; Phase 4 authority semantics remain canonical.

Before stopping report: WHERE_WE_ARE, SESSION_SEGMENT, WHAT_WAS_VERIFIED,
WHAT_WAS_COMPLETED, WHAT_REMAINS_IN_CURRENT_PHASE, TOTAL_PROJECT_POSITION, BLOCKERS,
STOP_GATE, EXACT_NEXT_SAFE_ACTION.
