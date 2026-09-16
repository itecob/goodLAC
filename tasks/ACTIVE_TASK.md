# ACTIVE TASK — LAC-P006

## Task ID

`LAC-P006`

## Objective

Perform the deterministic local end-to-end and negative-security qualification of the completed Phase 4 permission-management plane through P005. Prove that capability registration remains zero-authority, unknown/new requests remain terminally non-resumable, standing policy is deterministic, exact approvals remain one-request authority, and owner administration through `lacctl`/P004 is isolated from governed runtime consumers.

## In scope

- Exercise P001–P005 together using deterministic local/synthetic fixtures only.
- Qualify `lacctl` against the real P004 Unix-domain administrator server across skills inspection, standing-policy administration, pending-permission administration, and exact approvals.
- Verify administrator endpoint ownership/mode and peer-UID enforcement, plus fail-closed unavailable/malformed/unsupported protocol behavior.
- Verify the administration socket is not visible inside the selected governed agent sandbox and runtime namespaces expose no administration mutation surface.
- Verify P001 registration alone grants no authority.
- Verify P002 unknown/new material terminates the original effect and later registry/policy/pending administration cannot revive it.
- Verify P003 deterministic rule specificity and `DENY > REQUIRE_APPROVAL > ALLOW` precedence over trusted P002-validated metadata only.
- Verify exact approval still requires dispatch-time policy re-evaluation and does not itself dispatch/execute an effect.
- Verify restart durability of the canonical registry, pending administration disposition, standing policy, and exact approval state used by the qualification scenarios.
- Run the accepted regression gate through P005/P004/P003/P002/P001/B001 and all prior accepted phases.

## Out of scope

- Calendar adapter implementation (`LAC-B002`).
- Generic external-consumer proof (`LAC-B003`).
- Chief of Staff, OpenClaw, Omarchy Agent OS, web UI/TUI, remote administration, enterprise RBAC, or multi-user policy.
- Production credentials, production accounts, or external consequential effects.
- New administration features beyond correcting a concrete P001–P005 defect required to satisfy existing binding contracts.

## Required outputs

- Deterministic P006 qualification tests and evidence covering the integrated permission-management path and negative-security boundaries above.
- Evidence that denied/closed P002 effects remain non-resumable after administrative changes.
- Evidence that governed sandboxes/runtime consumers cannot reach or invoke the P004 administration surface.
- Applicable accepted regression evidence.
- One owner-executable package completing P006 and activating fresh `LAC-B002` on success.

## Next task on success

`LAC-B002` in a fresh implementation session.
